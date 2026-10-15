"""
Step 1: Audio-Driven Timing Engine (Forced Alignment)
-----------------------------------------------------
Takes a raw voiceover audio file, runs faster-whisper to extract exact 
word-level start and end times, and structures it into a validated Pydantic model.
"""

import json
from pathlib import Path
from typing import List
from faster_whisper import WhisperModel
from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class TranscriptAlignment(BaseModel):
    audio_path: str
    duration: float
    words: List[WordTimestamp] = Field(default_factory=list)

    def get_timestamp_for_keyword(self, keyword: str) -> float:
        """Finds the exact start time of a specific keyword in the voiceover."""
        kw_lower = keyword.strip().lower()
        for item in self.words:
            if kw_lower in item.word.strip().lower():
                return item.start
        return 0.0  # Fallback if keyword not found


class AudioAlignerPipeline:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        print(f"[*] Loading Whisper model ({model_size}) on {device}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def process_audio(self, audio_filepath: str, output_json_path: str = "word_timestamps.json") -> TranscriptAlignment:
        audio_path = Path(audio_filepath)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_filepath}")

        print(f"[*] Transcribing and extracting word-level timestamps for: {audio_path.name}...")
        segments, info = self.model.transcribe(str(audio_path), word_timestamps=True)

        all_words = []
        for segment in segments:
            if segment.words:
                for w in segment.words:
                    all_words.append(
                        WordTimestamp(
                            word=w.word,
                            start=round(w.start, 3),
                            end=round(w.end, 3)
                        )
                    )

        alignment = TranscriptAlignment(
            audio_path=str(audio_path),
            duration=round(info.duration, 3),
            words=all_words
        )

        # Save to disk for subsequent compiler steps
        out_path = Path(output_json_path)
        out_path.write_text(alignment.model_dump_json(indent=2), encoding="utf-8")
        print(f"[+] Alignment complete! Saved {len(all_words)} word timestamps to {out_path.resolve()}")

        return alignment


# --- Example Execution ---
if __name__ == "__main__":
    # To test locally:
    # 1. Place an audio file named 'voiceover.mp3' in your directory.
    # 2. Run: python engine/audio_aligner.py
    audio_file = "voiceover.mp3"
    if Path(audio_file).exists():
        aligner = AudioAlignerPipeline(model_size="base")
        result = aligner.process_audio(audio_file)
        
        # Example query for keyword synchronization
        target_time = result.get_timestamp_for_keyword("SQLite")
        print(f"[DEBUG] The word 'SQLite' was spoken at: {target_time} seconds.")
    else:
        print(f"[-] Place a sample '{audio_file}' in this folder to run the alignment test.")