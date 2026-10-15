"""
Cinematic Post-Processor & Native FFmpeg Audio Mixer
-------------------------------------------------------------------------
1. OpenCV Shader: Applies multi-pass optical bloom, chromatic halation, 
   vignette, and organic film grain to turn flat Manim renders into 
   ByteMonk-caliber motion graphics.
2. Native FFmpeg Mixer: Mixes voiceover, optional background music, and 
   automated SFX cue sheets using direct FFmpeg filtergraphs (no pydub/ffprobe required).
"""

import json
from pathlib import Path
import subprocess
import cv2
import numpy as np


class CinematicPostProcessor:
    def __init__(self, fps: float = 60.0):
        self.fps = fps

    def apply_optical_bloom_shader(self, input_video_path: str, output_video_path: str):
        """
        Intercepts raw video frames and applies HDR-style optical halation,
        multi-pass Gaussian blur, radial vignette, and film grain.
        """
        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open input video: {input_video_path}")

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_video_path, fourcc, self.fps, (w, h))

        # Precompute radial vignette mask
        X = np.linspace(-1, 1, w)
        Y = np.linspace(-1, 1, h)
        xx, yy = np.meshgrid(X, Y)
        radius = np.sqrt(xx**2 + yy**2)
        vignette = np.clip(1.0 - 0.25 * (radius**2), 0.7, 1.0)[..., np.newaxis]

        print(f"[*] Processing {total_frames} frames through OpenCV Cinematic Bloom Shader...")
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            img = frame.astype(np.float32) / 255.0
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, bright_mask = cv2.threshold(gray, 0.6, 1.0, cv2.THRESH_BINARY)
            bright_pass = img * bright_mask[..., np.newaxis]

            bloom_tight = cv2.GaussianBlur(bright_pass, (0, 0), sigmaX=7, sigmaY=7)
            bloom_wide = cv2.GaussianBlur(bright_pass, (0, 0), sigmaX=31, sigmaY=31)

            combined = img + (bloom_tight * 0.4) + (bloom_wide * 0.25)
            noise = np.random.normal(0, 0.01, img.shape).astype(np.float32)
            final = np.clip((combined * vignette) + noise, 0.0, 1.0)

            out.write((final * 255).astype(np.uint8))
            frame_idx += 1
            if frame_idx % 100 == 0:
                print(f"    - Rendered frame {frame_idx}/{total_frames}")

        cap.release()
        out.release()
        print(f"[+] Cinematic video grading complete: {output_video_path}")


class AutomatedAudioMixer:
    def __init__(self, sfx_library_dir: str = "assets/sfx/"):
        self.sfx_dir = Path(sfx_library_dir)

    def mix_audio_track(
        self,
        voiceover_path: str,
        sfx_cues_json: str = "sfx_cues.json",
        bg_music_path: str = None,
        output_audio_path: str = "temp_master_audio.wav"
    ):
        """
        Mixes voiceover, optional background music, and automated SFX cues 
        using native FFmpeg filtergraphs. Completely bypasses pydub/ffprobe bugs.
        """
        vo_path = Path(voiceover_path)
        if not vo_path.exists():
            raise FileNotFoundError(f"Voiceover file missing: {vo_path}")

        print("[*] Mixing audio layers via native FFmpeg...")

        # Build complex FFmpeg filtergraph inputs and mix arguments
        inputs = ["-i", str(vo_path)]
        filter_complex_parts = []
        mix_inputs = ["[0:a]"]

        input_idx = 1

        # Optional background music input and ducking filter (-18dB)
        if bg_music_path and Path(bg_music_path).exists():
            inputs.extend(["-i", str(bg_music_path)])
            filter_complex_parts.append(f"[{input_idx}:a]volume=0.12[bg_ducked]")
            mix_inputs.append("[bg_ducked]")
            input_idx += 1

        # Load SFX cue sheet generated during Step 3
        cues_path = Path(sfx_cues_json)
        valid_cues = []
        if cues_path.exists():
            cues = json.loads(cues_path.read_text(encoding="utf-8"))
            for cue in cues:
                sfx_file = self.sfx_dir / cue["sfx"]
                if sfx_file.exists():
                    valid_cues.append((cue, sfx_file))

        # Add each SFX as an input and apply millisecond delay (adelay)
        for idx, (cue, sfx_file) in enumerate(valid_cues):
            inputs.extend(["-i", str(sfx_file)])
            delay_ms = int(cue["time_sec"] * 1000)
            # Convert volume dB to gain multiplier if needed, or use volume filter
            filter_complex_parts.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[sfx{idx}]")
            mix_inputs.append(f"[sfx{idx}]")
            input_idx += 1

        # Combine all audio streams using amix
        total_streams = len(mix_inputs)
        filter_str = ""
        if filter_complex_parts:
            filter_str += ";".join(filter_complex_parts) + ";"
        
        filter_str += f"{''.join(mix_inputs)}amix=inputs={total_streams}:duration=first:dropout_transition=2[outa]"

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[outa]",
            output_audio_path
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"[-] FFmpeg Audio Mixing Error:\n{result.stderr.decode('utf-8', errors='ignore')}")
            raise RuntimeError("FFmpeg audio mixing failed.")

        print(f"[+] Master audio successfully mixed: {output_audio_path}")
        return output_audio_path