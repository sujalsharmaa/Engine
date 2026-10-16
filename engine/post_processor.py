"""
engine/post_processor.py
-------------------------------------------------------------------------
Everything after Manim:

  * synthesised SFX library (no copyright issues, regenerated if missing)
  * audio mix: voiceover + SFX + music with sidechain ducking + loudness norm
  * video finishing in ONE pass: camera push-in/drift, bloom, vignette, grain,
    progress bar -> piped straight into ffmpeg together with audio + captions
    (single lossy encode instead of the old mp4v -> libx264 double encode)
"""

import json
import math
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

SR = 44100


# ------------------------------------------------------------------ ffmpeg --
def resolve_ffmpeg_binary() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise RuntimeError("ffmpeg not found. Install it (apt install ffmpeg / brew install ffmpeg).")


def ffprobe_duration(path: str) -> float:
    ff = resolve_ffmpeg_binary().replace("ffmpeg", "ffprobe") if "ffmpeg" in resolve_ffmpeg_binary() else "ffprobe"
    try:
        out = subprocess.run([ff, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def has_filter(name: str) -> bool:
    out = subprocess.run([resolve_ffmpeg_binary(), "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return f" {name} " in out


# --------------------------------------------------------------------- sfx --
def _save_wav(path: Path, x: np.ndarray):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def ensure_default_sfx(sfx_dir: Path):
    sfx_dir = Path(sfx_dir)
    sfx_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)

    def t(d):
        return np.linspace(0, d, int(SR * d), endpoint=False)

    makers = {}

    def pop():
        x = t(0.14)
        return np.sin(2 * np.pi * (520 + 700 * np.exp(-x * 40)) * x) * np.exp(-x * 28) * 0.8
    makers["pop.wav"] = pop
    makers["card_pop.wav"] = lambda: np.sin(2 * np.pi * (300 + 500 * np.exp(-t(0.2) * 30)) * t(0.2)) * np.exp(-t(0.2) * 20) * 0.8

    def whoosh():
        x = t(0.55)
        n = rng.normal(0, 1, x.size)
        k = np.ones(40) / 40
        n = np.convolve(n, k, mode="same")
        return n * np.sin(np.pi * x / 0.55) ** 2 * 0.9
    makers["whoosh_soft.wav"] = whoosh

    def tick():
        x = t(0.04)
        return rng.normal(0, 1, x.size) * np.exp(-x * 120) * 0.5 + np.sin(2 * np.pi * 1800 * x) * np.exp(-x * 150) * 0.4
    makers["tick.wav"] = tick

    def success():
        a, b = t(0.16), t(0.34)
        return np.concatenate([np.sin(2 * np.pi * 660 * a) * np.exp(-a * 9), np.sin(2 * np.pi * 990 * b) * np.exp(-b * 7)]) * 0.55
    makers["success.wav"] = success

    def error():
        x = t(0.38)
        saw = 2 * ((140 * x) % 1) - 1
        return saw * np.exp(-x * 6) * 0.5 * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 14 * x)))
    makers["error.wav"] = error

    def hit():
        x = t(0.5)
        return (np.sin(2 * np.pi * (45 + 90 * np.exp(-x * 14)) * x) * np.exp(-x * 7) + rng.normal(0, 1, x.size) * np.exp(-x * 40) * 0.3) * 0.95
    makers["hit.wav"] = hit

    for name, fn in makers.items():
        p = sfx_dir / name
        if not p.exists():
            _save_wav(p, fn())


def _load_wav(path: Path) -> Optional[np.ndarray]:
    try:
        with wave.open(str(path), "r") as w:
            if w.getsampwidth() != 2 or w.getframerate() != SR:
                raise ValueError
            raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
            if w.getnchannels() == 2:
                raw = raw.reshape(-1, 2).mean(axis=1)
            return raw
    except Exception:
        tmp = path.with_suffix(".conv.wav")
        r = subprocess.run([resolve_ffmpeg_binary(), "-y", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-sample_fmt", "s16", str(tmp)])
        if r.returncode == 0 and tmp.exists():
            try:
                with wave.open(str(tmp), "r") as w:
                    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
            finally:
                tmp.unlink(missing_ok=True)
    return None


def build_sfx_track(cues: List[Dict[str, Any]], sfx_dir: Path, total_sec: float, out_wav: Path) -> bool:
    if not cues:
        return False
    track = np.zeros(int(SR * (total_sec + 2)), dtype=np.float32)
    cache: Dict[str, Optional[np.ndarray]] = {}
    used = 0
    for cue in cues:
        name = cue["sfx"]
        if name not in cache:
            p = Path(sfx_dir) / name
            cache[name] = _load_wav(p) if p.exists() else None
            if cache[name] is None:
                print(f"[!] SFX '{name}' not found in {sfx_dir}; skipped")
        snd = cache[name]
        if snd is None:
            continue
        gain = 10 ** (cue.get("volume_db", -10) / 20)
        i = int(cue["time_sec"] * SR)
        seg = snd[: max(0, track.size - i)] * gain
        track[i:i + seg.size] += seg
        used += 1
    if not used:
        return False
    _save_wav(out_wav, track)
    return True


# --------------------------------------------------------------------- mix --
def mix_audio(voice: Optional[str], sfx_wav: Optional[str], music: Optional[str], total_sec: float, out_path: str,
              music_volume: float = 0.16) -> str:
    ff = resolve_ffmpeg_binary()
    cmd = [ff, "-y", "-v", "error"]
    idx = {}
    n = 0
    if voice:
        cmd += ["-i", voice]; idx["vo"] = n; n += 1
    else:
        cmd += ["-f", "lavfi", "-t", f"{total_sec:.3f}", "-i", f"anullsrc=r={SR}:cl=stereo"]; idx["vo"] = n; n += 1
    if sfx_wav:
        cmd += ["-i", sfx_wav]; idx["sfx"] = n; n += 1
    if music:
        cmd += ["-stream_loop", "-1", "-i", music]; idx["music"] = n; n += 1

    f = [f"[{idx['vo']}:a]aresample={SR},aformat=channel_layouts=stereo,asplit=2[vo][vosc]"]
    mix_in = ["[vo]"]
    if "sfx" in idx:
        f.append(f"[{idx['sfx']}:a]aresample={SR},aformat=channel_layouts=stereo[sfx]")
        mix_in.append("[sfx]")
    if "music" in idx:
        f.append(f"[{idx['music']}:a]aresample={SR},aformat=channel_layouts=stereo,volume={music_volume},"
                 f"afade=t=in:d=1.5,afade=t=out:st={max(0, total_sec - 2):.2f}:d=2[m0]")
        f.append("[m0][vosc]sidechaincompress=threshold=0.03:ratio=10:attack=15:release=450[mduck]")
        mix_in.append("[mduck]")
    else:
        f[0] = f[0].replace("asplit=2[vo][vosc]", "anull[vo]")
    f.append(f"{''.join(mix_in)}amix=inputs={len(mix_in)}:duration=longest:normalize=0,"
             f"loudnorm=I=-14:TP=-1.5:LRA=11,atrim=0:{total_sec:.3f}[out]")
    cmd += ["-filter_complex", ";".join(f), "-map", "[out]", "-ar", str(SR), "-c:a", "pcm_s16le", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("audio mix failed:\n" + r.stderr[-1500:])
    return out_path


# ------------------------------------------------------------- video finish --
def _hex_to_bgr(h: str):
    h = h.lstrip("#")
    return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))


def finish_video(raw_video: str, audio_wav: str, out_path: str, compiled: Dict[str, Any], accent: str, glow: bool,
                 ass_path: Optional[str], grade: bool = True, crf: int = 17, preset: str = "medium") -> str:
    import cv2

    cap = cv2.VideoCapture(raw_video)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {raw_video}")
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = float(compiled["duration"])
    scenes = compiled["scenes"]
    show_bar = bool(compiled.get("show_progress_bar", True))
    bar_col = _hex_to_bgr(accent)
    bar_h = max(4, int(h * 0.004))

    vig = None
    grain = []
    if grade:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        v = np.clip(1.0 - 0.28 * np.clip(d - 0.55, 0, None) ** 1.4, 0.6, 1.0)
        vig = np.repeat((v * 255).astype(np.uint8)[:, :, None], 3, axis=2)
        rng = np.random.default_rng(3)
        grain = [rng.integers(0, 4, (h, w, 3), dtype=np.uint8) for _ in range(4)]

    cmd = [resolve_ffmpeg_binary(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-",
           "-i", audio_wav]
    vf = []
    wd = None
    if ass_path and Path(ass_path).exists() and has_filter("subtitles"):
        wd = str(Path(ass_path).parent)
        vf.append(f"subtitles={Path(ass_path).name}")
    elif ass_path:
        print("[!] ffmpeg has no 'subtitles' filter (libass); captions skipped")
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total:.3f}", "-movflags", "+faststart", out_path]
    log = open(str(Path(out_path).with_suffix(".ffmpeg.log")), "w")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log, cwd=wd)

    idx = 0
    cur = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = idx / fps
        while cur + 1 < len(scenes) and t >= scenes[cur]["t1"]:
            cur += 1
        sc = scenes[cur]
        if grade:
            p = min(1.0, max(0.0, (t - sc["t0"]) / max(0.1, sc["t1"] - sc["t0"])))
            mode = sc.get("camera", "push_in")
            s, tx, ty = 1.0, 0.0, 0.0
            if mode == "push_in":
                s = 1.0 + 0.06 * p
            elif mode == "pull_out":
                s = 1.06 - 0.06 * p
            elif mode == "drift":
                s, tx, ty = 1.05, (p - 0.5) * 0.02 * w, math.sin(p * math.pi) * 0.006 * h
            if s != 1.0 or tx or ty:
                M = np.array([[s, 0, (1 - s) * w / 2 + tx], [0, s, (1 - s) * h / 2 + ty]], dtype=np.float32)
                frame = cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            if glow:
                small = cv2.resize(frame, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                bright = np.where((gray > 215)[:, :, None], small, 0).astype(np.uint8)
                bloom = cv2.addWeighted(cv2.GaussianBlur(bright, (0, 0), 4), 0.30, cv2.GaussianBlur(bright, (0, 0), 14), 0.22, 0)
                frame = cv2.add(frame, cv2.resize(bloom, (w, h), interpolation=cv2.INTER_LINEAR))
            frame = cv2.multiply(frame, vig, scale=1 / 255.0)
            frame = cv2.add(frame, grain[idx % 4])
        if show_bar:
            frame[h - bar_h:, : max(1, int(w * min(1.0, t / total)))] = bar_col
        proc.stdin.write(frame.tobytes())
        idx += 1
        if idx % 300 == 0:
            print(f"    finishing... {idx} frames ({t:.0f}s / {total:.0f}s)")
    cap.release()
    proc.stdin.close()
    proc.wait()
    log.close()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg encode failed; see " + str(Path(out_path).with_suffix(".ffmpeg.log")))
    return out_path
