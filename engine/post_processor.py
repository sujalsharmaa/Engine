"""
engine/post_processor.py
-------------------------------------------------------------------------
1. OpenCV Cinematic Bloom Shader (optical halation, vignette, film grain).
2. Procedural SFX Synthesizer (generates crisp UI pops & whooshes via NumPy
   if WAV files are missing in assets/sfx/).
3. Cross-Platform FFmpeg Resolver & Native Filtergraph Audio Mixer.
"""

import json
import os
import shutil
import subprocess
import wave
from pathlib import Path
import cv2
import numpy as np


def resolve_ffmpeg_binary() -> str:
    """Finds ffmpeg on Linux/Docker, local folder, PATH, or Windows Winget."""
    local_exe = Path("ffmpeg.exe")
    if local_exe.exists():
        return str(local_exe.resolve())

    which_ff = shutil.which("ffmpeg")
    if which_ff:
        return which_ff

    # Search Windows Winget / common install paths automatically
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    search_roots = [
        Path(local_appdata) / "Microsoft" / "WinGet" / "Packages",
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
    ]
    for root in search_roots:
        if root.exists():
            matches = list(root.rglob("ffmpeg.exe"))
            if matches:
                return str(matches[0])

    raise FileNotFoundError(
        "FFmpeg binary not found! Place ffmpeg.exe in your project folder or install via apt/winget."
    )


def ensure_default_sfx(sfx_dir: Path):
    """Synthesizes clean studio sound effects via NumPy if WAV files don't exist yet."""
    sfx_dir.mkdir(parents=True, exist_ok=True)
    sr = 44100

    def save_wav(filename: str, samples: np.ndarray):
        filepath = sfx_dir / filename
        if filepath.exists():
            return
        pcm = np.int16(np.clip(samples, -1.0, 1.0) * 32767)
        with wave.open(str(filepath), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(np.column_stack((pcm, pcm)).tobytes())

    # 1. Crisp UI Card Pop (exponential pitch-drop sine thud)
    t_pop = np.linspace(0, 0.14, int(sr * 0.14), endpoint=False)
    freq_pop = 260 * np.exp(-t_pop * 22) + 55
    env_pop = np.exp(-t_pop * 28)
    save_wav("card_pop.wav", np.sin(2 * np.pi * freq_pop * t_pop) * env_pop * 0.65)
    save_wav("pop.wav", np.sin(2 * np.pi * freq_pop * t_pop) * env_pop * 0.55)

    # 2. Soft Cinematic Whoosh (envelope-shaped filtered noise)
    t_w = np.linspace(0, 0.32, int(sr * 0.32), endpoint=False)
    np.random.seed(42)
    noise = np.convolve(np.random.normal(0, 1, len(t_w)), np.ones(18) / 18, mode="same")
    env_w = np.sin(np.pi * (t_w / 0.32)) ** 2
    save_wav("whoosh_soft.wav", noise * env_w * 0.35)


class CinematicPostProcessor:
    def __init__(self, fps: float = 60.0):
        self.fps = fps

    def apply_optical_bloom_shader(self, input_video_path: str, output_video_path: str):
        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open input video: {input_video_path}")

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_video_path, fourcc, self.fps, (w, h))

        X = np.linspace(-1, 1, w)
        Y = np.linspace(-1, 1, h)
        xx, yy = np.meshgrid(X, Y)
        radius = np.sqrt(xx**2 + yy**2)
        vignette = np.clip(1.0 - 0.24 * (radius**2), 0.72, 1.0)[..., np.newaxis]

        print(f"[*] Grading {total_frames} frames through OpenCV Optical Bloom Shader...")
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            img = frame.astype(np.float32) / 255.0
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, bright_mask = cv2.threshold(gray, 0.58, 1.0, cv2.THRESH_BINARY)
            bright_pass = img * bright_mask[..., np.newaxis]

            bloom_tight = cv2.GaussianBlur(bright_pass, (0, 0), sigmaX=7, sigmaY=7)
            bloom_wide = cv2.GaussianBlur(bright_pass, (0, 0), sigmaX=29, sigmaY=29)

            combined = img + (bloom_tight * 0.42) + (bloom_wide * 0.26)
            noise = np.random.normal(0, 0.008, img.shape).astype(np.float32)
            final = np.clip((combined * vignette) + noise, 0.0, 1.0)

            out.write((final * 255).astype(np.uint8))
            frame_idx += 1
            if frame_idx % 120 == 0:
                print(f"    - Graded frame {frame_idx}/{total_frames}")

        cap.release()
        out.release()
        print(f"[+] Cinematic grading saved -> {output_video_path}")


class AutomatedAudioMixer:
    def __init__(self, sfx_library_dir: str = "assets/sfx/"):
        self.sfx_dir = Path(sfx_library_dir)
        ensure_default_sfx(self.sfx_dir)
        self.ffmpeg_bin = resolve_ffmpeg_binary()

    def mix_audio_track(
        self,
        voiceover_path: str,
        sfx_cues_json: str = "sfx_cues.json",
        bg_music_path: str = None,
        output_audio_path: str = "temp_master_audio.wav"
    ) -> str:
        vo_path = Path(voiceover_path)
        if not vo_path.exists():
            raise FileNotFoundError(f"Voiceover file missing: {vo_path}")

        print(f"[*] Mixing audio layers via FFmpeg ({self.ffmpeg_bin})...")
        inputs = ["-i", str(vo_path)]
        filter_parts = []
        mix_labels = ["[0:a]"]
        input_idx = 1

        if bg_music_path and Path(bg_music_path).exists():
            inputs.extend(["-i", str(bg_music_path)])
            filter_parts.append(f"[{input_idx}:a]volume=0.12[bg_ducked]")
            mix_labels.append("[bg_ducked]")
            input_idx += 1

        cues_path = Path(sfx_cues_json)
        valid_cues = []
        if cues_path.exists():
            cues = json.loads(cues_path.read_text(encoding="utf-8"))
            for cue in cues:
                sfx_file = self.sfx_dir / cue["sfx"]
                if sfx_file.exists():
                    valid_cues.append((cue, sfx_file))

        for idx, (cue, sfx_file) in enumerate(valid_cues):
            inputs.extend(["-i", str(sfx_file)])
            delay_ms = max(0, int(float(cue["time_sec"]) * 1000))
            filter_parts.append(f"[{input_idx}:a]volume=0.35,adelay={delay_ms}|{delay_ms}[sfx{idx}]")
            mix_labels.append(f"[sfx{idx}]")
            input_idx += 1

        total_streams = len(mix_labels)
        filter_str = (";".join(filter_parts) + ";") if filter_parts else ""
        filter_str += f"{''.join(mix_labels)}amix=inputs={total_streams}:duration=first:dropout_transition=2[outa]"

        cmd = [
            self.ffmpeg_bin, "-y",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[outa]",
            output_audio_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg audio mix failed:\n{res.stderr.decode('utf-8', errors='ignore')}")

        print(f"[+] Master audio mixed -> {output_audio_path}")
        return output_audio_path