"""
engine/audio_aligner.py
-------------------------------------------------------------------------
Voiceover -> word-level timestamps (faster-whisper). The narration script is
passed as `initial_prompt`, which noticeably improves recognition of jargon
(PromQL, Kubernetes, gRPC ...). Results are cached by audio hash + model.
"""

import hashlib
import json
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class TranscriptAlignment(BaseModel):
    audio_path: str
    duration: float
    words: List[WordTimestamp] = Field(default_factory=list)


class AudioAlignerPipeline:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size, self.device, self.compute_type = model_size, device, compute_type
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            print(f"[*] Loading Whisper model ({self.model_size}) on {self.device}...")
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    @staticmethod
    def _key(audio: str, model: str, prompt: str) -> str:
        h = hashlib.sha1()
        with open(audio, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        h.update(model.encode())
        h.update(prompt.encode())
        return h.hexdigest()[:16]

    def process_audio(self, audio_filepath: str, output_json_path: str = "word_timestamps.json",
                      script_hint: str = "", language: str = None) -> TranscriptAlignment:
        audio = Path(audio_filepath)
        if not audio.exists():
            raise FileNotFoundError(f"Audio not found: {audio}")
        key = self._key(str(audio), self.model_size, script_hint[:900])
        out = Path(output_json_path)
        if out.exists():
            try:
                cached = json.loads(out.read_text(encoding="utf-8"))
                if cached.get("cache_key") == key:
                    print("[*] Using cached word timestamps")
                    return TranscriptAlignment(**{k: v for k, v in cached.items() if k != "cache_key"})
            except Exception:
                pass
        model = self._load()
        print(f"[*] Aligning {audio.name} ...")
        segments, info = model.transcribe(str(audio), word_timestamps=True, beam_size=5, language=language,
                                          initial_prompt=script_hint[:900] or None, vad_filter=False)
        words = [WordTimestamp(word=w.word.strip(), start=round(w.start, 3), end=round(w.end, 3))
                 for seg in segments for w in (seg.words or [])]
        result = TranscriptAlignment(audio_path=str(audio), duration=round(float(info.duration), 3), words=words)
        data = result.model_dump()
        data["cache_key"] = key
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[+] {len(words)} words, {result.duration:.1f}s")
        return result
