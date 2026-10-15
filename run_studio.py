"""
run_studio.py — Master CLI Orchestrator
-------------------------------------------------------------------------
Single command to render 16:9 Deep Dives or 9:16 Shorts into output/:
    python run_studio.py --script prometheus_short.json --audio voiceover.mp3 --output output/prometheus_short.mp4
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from engine.audio_aligner import AudioAlignerPipeline
from engine.storyboard_compiler import StoryboardCompiler
from engine.post_processor import CinematicPostProcessor, AutomatedAudioMixer, resolve_ffmpeg_binary


def main():
    parser = argparse.ArgumentParser(description="Proprietary Python Video Studio CLI")
    parser.add_argument("--script", required=True, help="Path to blueprint JSON file")
    parser.add_argument("--audio", required=True, help="Path to voiceover MP3/WAV file")
    parser.add_argument("--music", default=None, help="Optional background music track")
    parser.add_argument("--output", default="output/final_master.mp4", help="Output video path (inside output/)")
    parser.add_argument("--force", action="store_true", help="Force full re-render ignoring cache")

    args = parser.parse_args()

    script_path = Path(args.script)
    audio_path = Path(args.audio)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not script_path.exists():
        print(f"[-] Blueprint script not found: {script_path}")
        sys.exit(1)
    if not audio_path.exists():
        print(f"[-] Voiceover audio not found: {audio_path}")
        sys.exit(1)

    ffmpeg_bin = resolve_ffmpeg_binary()

    timestamps_file = Path("word_timestamps.json")
    compiled_json = Path("compiled_storyboard.json")
    sfx_cues_json = Path("sfx_cues.json")
    graded_video_temp = Path("temp_graded_video.mp4")
    master_audio_path = Path("temp_master_audio.wav")

    # STEP 1: Forced Alignment
    if not timestamps_file.exists() or args.force:
        print("\n[Step 1/4] Running Faster-Whisper Forced Aligner...")
        aligner = AudioAlignerPipeline(model_size="base")
        aligner.process_audio(str(audio_path), output_json_path=str(timestamps_file))
    else:
        print("\n[Step 1/4] Using cached word_timestamps.json")

    # STEP 2: Storyboard Compilation (Always re-compile JSON as it takes <0.05s)
    print("\n[Step 2/4] Compiling and validating storyboard specifications...")
    compiler = StoryboardCompiler(timestamps_json_path=str(timestamps_file))
    storyboard = compiler.compile_storyboard(str(script_path), output_path=str(compiled_json))

    # Determine resolution based on aspect_ratio ("9:16" vs "16:9")
    res_flag = "1080,1920" if storyboard.aspect_ratio == "9:16" else "1920,1080"

    # STEP 3: Manim Rendering
    possible_files = list(Path("media/videos").rglob("StoryboardRenderer.mp4"))
    raw_video_path = possible_files[0] if possible_files else Path("media/videos/renderer_engine/1080p60/StoryboardRenderer.mp4")

    if not raw_video_path.exists() or not sfx_cues_json.exists() or args.force:
        print(f"\n[Step 3/4] Rendering 8-Component Manim Scene ({storyboard.aspect_ratio} @ {res_flag})...")
        manim_cmd = [
            sys.executable, "-m", "manim", "render",
            "-qh", "-r", res_flag,
            "engine/renderer_engine.py", "StoryboardRenderer"
        ]
        res = subprocess.run(manim_cmd)
        if res.returncode != 0:
            print("[-] Manim render failed.")
            sys.exit(1)
        possible_files = list(Path("media/videos").rglob("StoryboardRenderer.mp4"))
        if possible_files:
            raw_video_path = max(possible_files, key=lambda p: p.stat().st_mtime)
    else:
        print(f"\n[Step 3/4] Using cached Manim video: {raw_video_path}")

    # STEP 4A: OpenCV Bloom Shader
    if not graded_video_temp.exists() or args.force:
        print("\n[Step 4a/4] Applying OpenCV Cinematic Bloom & Film Grain Shader...")
        post = CinematicPostProcessor(fps=float(storyboard.fps))
        post.apply_optical_bloom_shader(str(raw_video_path), str(graded_video_temp))
    else:
        print("\n[Step 4a/4] Using cached temp_graded_video.mp4")

    # STEP 4B: Native FFmpeg Audio & SFX Mixing
    print("\n[Step 4b/4] Mixing Voiceover + Procedural/Custom SFX + Music...")
    mixer = AutomatedAudioMixer(sfx_library_dir="assets/sfx/")
    mixer.mix_audio_track(
        voiceover_path=str(audio_path),
        sfx_cues_json=str(sfx_cues_json),
        bg_music_path=args.music,
        output_audio_path=str(master_audio_path)
    )

    # FINAL MUX
    print(f"\n[MUX] Multiplexing Master Video -> {output_path}")
    mux_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(graded_video_temp),
        "-i", str(master_audio_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path)
    ]
    mux_res = subprocess.run(mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if mux_res.returncode != 0:
        print(f"[-] Mux error:\n{mux_res.stderr.decode('utf-8', errors='ignore')}")
        sys.exit(1)

    print("==================================================")
    print(f" [✨] SUCCESS! MASTER VIDEO READY: {output_path.resolve()}")
    print("==================================================")


if __name__ == "__main__":
    main()