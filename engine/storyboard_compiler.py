"""
engine/storyboard_compiler.py
-------------------------------------------------------------------------
JSON blueprint + word timestamps  ->  validated, time-bound storyboard.

The LLM only writes: scene_id, narration_text, visual{...}. Everything about
time (scene boundaries, per-item reveal moments, caption words) is computed
here from the real voiceover.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from engine.schema import VideoStoryboard, collect_extras, format_validation_error
from engine.timing import (
    align_script_to_transcript,
    bind_cues,
    estimate_word_times,
    scene_windows,
)


class StoryboardCompiler:
    def __init__(self, timestamps_json_path: Optional[str] = None):
        self.transcript: List[Dict[str, Any]] = []
        self.audio_duration: Optional[float] = None
        if timestamps_json_path and Path(timestamps_json_path).exists():
            data = json.loads(Path(timestamps_json_path).read_text(encoding="utf-8"))
            self.transcript = data.get("words", [])
            self.audio_duration = data.get("duration")
        self.warnings: List[str] = []

    def compile_storyboard(self, raw_llm_spec_path: str, output_path: str = "compiled_storyboard.json") -> Dict[str, Any]:
        spec_path = Path(raw_llm_spec_path)
        if not spec_path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {spec_path}")
        try:
            raw = json.loads(spec_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"{spec_path} is not valid JSON: {e}") from e

        try:
            sb = VideoStoryboard.model_validate(raw)
        except ValidationError as e:
            raise ValueError(format_validation_error(e)) from None
        if not sb.scenes:
            raise ValueError("Storyboard has no scenes.")

        for path, key in collect_extras(sb):
            self.warnings.append(f"unknown field '{key}' at {path or 'root'} (ignored)")

        narrations = [s.narration_text for s in sb.scenes]
        if self.transcript and self.audio_duration:
            scenes_words = align_script_to_transcript(narrations, self.transcript, self.audio_duration)
            total = self.audio_duration
            mode = "voiceover"
        else:
            scenes_words, total = estimate_word_times(narrations)
            mode = "estimated (no audio)"

        manual = None
        if sb.timing_mode == "manual":
            manual = [(s.start_time, s.end_time) for s in sb.scenes]
        windows = scene_windows(scenes_words, total, manual)

        compiled: Dict[str, Any] = sb.model_dump(mode="json")
        compiled["duration"] = windows[-1][1]
        compiled["timing_source"] = mode
        for scene, (t0, t1), words in zip(compiled["scenes"], windows, scenes_words):
            scene["t0"], scene["t1"], scene["words"] = t0, t1, words
            bind_cues(scene["visual"], words, self.warnings, f"scene '{scene['scene_id']}'")
            if t1 - t0 < 2.0:
                self.warnings.append(f"scene '{scene['scene_id']}' is only {t1 - t0:.1f}s long; animations will be compressed")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(compiled, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"[+] Compiled {len(sb.scenes)} scenes | {sb.aspect_ratio} | timing: {mode} | {compiled['duration']:.1f}s")
        for s in compiled["scenes"]:
            print(f"    {s['t0']:6.2f} -> {s['t1']:6.2f}  {s['scene_id']:<22} {s['visual']['component_type']}")
        for w in self.warnings:
            print(f"[!] {w}")
        return compiled
