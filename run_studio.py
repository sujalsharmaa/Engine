#!/usr/bin/env python3
"""
Python Video Studio  --  JSON + voiceover  ->  finished video.

  python run_studio.py --script my_video.json --audio voiceover.mp3
  python run_studio.py --script my_video.json                 # silent preview, estimated timing
  python run_studio.py --script my_video.json --audio vo.mp3 --quality final --music assets/music/bg.mp3
  python run_studio.py --script my_video.json --check         # validate only

Quality: preview (fast, half-res, 24fps) | draft (720p) | final (1080p, fps from JSON)
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine.captions import build_ass                                  # noqa: E402
from engine.post_processor import (build_sfx_track, ensure_default_sfx, ffprobe_duration,  # noqa: E402
                                   finish_video, mix_audio)
from engine.storyboard_compiler import StoryboardCompiler               # noqa: E402
from engine.theme import get_theme                                       # noqa: E402

BASE_RES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def resolution(aspect: str, quality: str):
    w, h = BASE_RES[aspect]
    f = {"preview": 0.5, "draft": 0.67, "final": 1.0}[quality]
    return int(w * f) // 2 * 2, int(h * f) // 2 * 2


def engine_hash(extra: str) -> str:
    h = hashlib.sha1(extra.encode())
    for p in sorted((ROOT / "engine").rglob("*.py")):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True, help="storyboard JSON written by the LLM")
    ap.add_argument("--audio", help="voiceover (mp3/wav/m4a). Omit for a silent preview with estimated timing")
    ap.add_argument("--out", help="output mp4 (default: output/<script-name>.mp4)")
    ap.add_argument("--music", help="optional background music (auto-ducked under the voice)")
    ap.add_argument("--music-volume", type=float, default=0.16)
    ap.add_argument("--quality", choices=["preview", "draft", "final"], default="final")
    ap.add_argument("--whisper", default="base", help="faster-whisper model: tiny|base|small|medium|large-v3")
    ap.add_argument("--language", default=None, help="voiceover language code, e.g. en, hi (default: auto)")
    ap.add_argument("--no-grade", action="store_true", help="skip camera motion / bloom / vignette / grain")
    ap.add_argument("--no-sfx", action="store_true")
    ap.add_argument("--workdir", default=str(ROOT / "build"))
    ap.add_argument("--check", action="store_true", help="validate + print timing table, do not render")
    ap.add_argument("--force", action="store_true", help="ignore render cache")
    a = ap.parse_args()

    t_start = time.time()
    script = Path(a.script).resolve()
    work = Path(a.workdir) / script.stem
    work.mkdir(parents=True, exist_ok=True)
    os.environ["STUDIO_SCRIPT_DIR"] = str(script.parent)

    # 1) timing source ---------------------------------------------------------
    ts_path = None
    if a.audio:
        from engine.audio_aligner import AudioAlignerPipeline
        raw = json.loads(script.read_text(encoding="utf-8"))
        hint = " ".join(s.get("narration_text", "") for s in raw.get("scenes", []))
        ts_path = str(work / "word_timestamps.json")
        AudioAlignerPipeline(model_size=a.whisper).process_audio(a.audio, ts_path, script_hint=hint, language=a.language)

    # 2) compile + validate ------------------------------------------------------
    compiled_path = work / "compiled_storyboard.json"
    try:
        compiled = StoryboardCompiler(ts_path).compile_storyboard(str(script), str(compiled_path))
    except ValueError as e:
        print(f"\n[x] {e}")
        sys.exit(2)
    if a.check:
        print("\n[+] Storyboard is valid.")
        return

    aspect = compiled["aspect_ratio"]
    W, H = resolution(aspect, a.quality)
    fps = 24 if a.quality == "preview" else (30 if a.quality == "draft" else int(compiled.get("fps", 30)))
    theme = get_theme(compiled["studio_theme"])

    # 3) Manim render (cached on storyboard + engine source) -----------------------
    key = engine_hash(compiled_path.read_text(encoding="utf-8") + f"{W}x{H}@{fps}")
    media = work / f"media_{key}"
    existing = list(media.rglob("StoryboardRenderer.mp4")) if media.exists() else []
    if existing and not a.force:
        print(f"[*] Reusing cached Manim render ({key})")
        raw_video = existing[0]
    else:
        print(f"[*] Rendering scenes with Manim at {W}x{H} @ {fps}fps ...")
        env = dict(os.environ, STUDIO_STORYBOARD=str(compiled_path), STUDIO_BUILD_DIR=str(work))
        cmd = [sys.executable, "-m", "manim", "render", "-r", f"{W},{H}", "--fps", str(fps), "--media_dir", str(media),
               "--disable_caching", str(ROOT / "engine" / "renderer_engine.py"), "StoryboardRenderer"]
        r = subprocess.run(cmd, env=env, cwd=str(ROOT))
        if r.returncode != 0:
            print("[x] Manim render failed (see log above).")
            sys.exit(3)
        raw_video = next(media.rglob("StoryboardRenderer.mp4"))
        for f in ("sfx_cues.json", "render_report.json"):
            pass
    report = work / "render_report.json"
    if report.exists():
        drift = json.loads(report.read_text() or "[]")
        for d in drift:
            print(f"[!] timing drift in scene '{d['scene']}': {d['late_by_sec']}s late - {d['hint']}")

    # 4) audio -------------------------------------------------------------------
    total = float(compiled["duration"])
    ensure_default_sfx(ROOT / "assets" / "sfx")
    cues = []
    if not a.no_sfx and (work / "sfx_cues.json").exists():
        cues = json.loads((work / "sfx_cues.json").read_text())
    sfx_wav = work / "sfx_track.wav"
    have_sfx = build_sfx_track(cues, ROOT / "assets" / "sfx", total, sfx_wav) if cues else False
    mixed = work / "final_mix.wav"
    mix_audio(a.audio, str(sfx_wav) if have_sfx else None, a.music, total, str(mixed), a.music_volume)

    # 5) captions + finishing --------------------------------------------------------
    ass = work / "captions.ass"
    has_caps = build_ass(compiled, W, H, theme.accent, str(ass))
    out = Path(a.out) if a.out else ROOT / "output" / f"{script.stem}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    print("[*] Finishing (camera, grade, captions, audio) ...")
    finish_video(str(raw_video), str(mixed), str(out), compiled, theme.accent, theme.glow,
                 str(ass) if has_caps else None, grade=not a.no_grade,
                 crf=23 if a.quality == "preview" else 17, preset="veryfast" if a.quality == "preview" else "medium")
    print(f"\n[+] DONE  {out}  ({ffprobe_duration(str(out)):.1f}s, {time.time() - t_start:.0f}s of work)")


if __name__ == "__main__":
    main()
