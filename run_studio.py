"""
Master Studio Orchestrator (`run_studio.py`) — Cached Version
-------------------------------------------------------------------------
Chains the 4-layer pipeline with built-in caching so you don't waste 
time re-rendering completed steps.
"""

import argparse
import sys
from pathlib import Path
import subprocess

from engine.audio_aligner import AudioAlignerPipeline
from engine.storyboard_compiler import StoryboardCompiler
from engine.post_processor import CinematicPostProcessor, AutomatedAudioMixer


def main():
    parser = argparse.ArgumentParser(description="Proprietary Python Video Studio CLI")
    parser.add_argument("--script", required=True, help="Path to raw LLM blueprint JSON file")
    parser.add_argument("--audio", required=True, help="Path to voiceover MP3/WAV file")
    parser.add_argument("--music", default=None, help="Optional path to background music track")
    parser.add_argument("--output", default="final_master_video.mp4", help="Final output video filename")
    parser.add_argument("--force", action="store_true", help="Force re-render all steps from scratch")
    
    args = parser.parse_args()

    script_path = Path(args.script)
    audio_path = Path(args.audio)
    output_path = Path(args.output)

    if not script_path.exists():
        print(f"[-] Error: Blueprint script not found at {script_path}")
        sys.exit(1)
    if not audio_path.exists():
        print(f"[-] Error: Voiceover audio not found at {audio_path}")
        sys.exit(1)

    print("==================================================")
    print(" [🎬] PROPRIETARY VIDEO STUDIO PIPELINE (CACHED)")
    print("==================================================")

    timestamps_file = Path("word_timestamps.json")
    compiled_json = Path("compiled_storyboard.json")
    sfx_cues_json = Path("sfx_cues.json")
    graded_video_temp = Path("temp_graded_video.mp4")
    master_audio_path = Path("temp_master_audio.wav")

    # --------------------------------------------------------------
    # STEP 1: Audio-Driven Timing Engine (Cached if exists)
    # --------------------------------------------------------------
    if not timestamps_file.exists() or args.force:
        print("\n[Step 1/4] Running Faster-Whisper Forced Aligner...")
        aligner = AudioAlignerPipeline(model_size="base")
        aligner.process_audio(str(audio_path), output_json_path=str(timestamps_file))
    else:
        print("\n[Step 1/4] Skipping Whisper Alignment (Found cached word_timestamps.json)")

    # --------------------------------------------------------------
    # STEP 2: Storyboard Compiler (Cached if exists)
    # --------------------------------------------------------------
    if not compiled_json.exists() or args.force:
        print("\n[Step 2/4] Compiling and validating storyboard specifications...")
        compiler = StoryboardCompiler(timestamps_json_path=str(timestamps_file))
        compiler.compile_storyboard(str(script_path), output_path=str(compiled_json))
    else:
        print("\n[Step 2/4] Skipping Compilation (Found cached compiled_storyboard.json)")

    # Locate potential Manim raw video output
    raw_video_path = Path("media/videos/renderer_engine/1080p60/StoryboardRenderer.mp4")
    possible_files = list(Path("media/videos").rglob("StoryboardRenderer.mp4"))
    if possible_files:
        raw_video_path = possible_files[0]

    # --------------------------------------------------------------
    # STEP 3: Manim Renderer Engine (Cached if raw video exists)
    # --------------------------------------------------------------
    if not raw_video_path.exists() or not sfx_cues_json.exists() or args.force:
        print("\n[Step 3/4] Executing Manim component renderer & logging SFX cues...")
        manim_cmd = ["manim", "-pqh", "engine/renderer_engine.py", "StoryboardRenderer"]
        result = subprocess.run(manim_cmd)
        if result.returncode != 0:
            print("[-] Error during Manim rendering phase.")
            sys.exit(1)
        
        possible_files = list(Path("media/videos").rglob("StoryboardRenderer.mp4"))
        if possible_files:
            raw_video_path = possible_files.pop()
    else:
        print(f"\n[Step 3/4] Skipping Manim Render (Found cached video at {raw_video_path})")

    # --------------------------------------------------------------
    # STEP 4A: OpenCV Cinematic Bloom Shader (Cached if temp graded video exists)
    # --------------------------------------------------------------
    if not graded_video_temp.exists() or args.force:
        print("\n[Step 4a/4] Applying OpenCV Cinematic Bloom & Film Grain Shader...")
        post_processor = CinematicPostProcessor(fps=60.0)
        post_processor.apply_optical_bloom_shader(str(raw_video_path), str(graded_video_temp))
    else:
        print("\n[Step 4a/4] Skipping OpenCV Shader (Found cached temp_graded_video.mp4)")

    # --------------------------------------------------------------
    # STEP 4B: Automated Foley & Audio Mixing (Cached if master audio exists)
    # --------------------------------------------------------------
    if not master_audio_path.exists() or args.force:
        print("\n[Step 4b/4] Mixing Master Audio (Voiceover + Ducked Music + SFX Cues)...")
        audio_mixer = AutomatedAudioMixer(sfx_library_dir="assets/sfx/")
        audio_mixer.mix_audio_track(
            voiceover_path=str(audio_path),
            sfx_cues_json=str(sfx_cues_json),
            bg_music_path=args.music,
            output_audio_path=str(master_audio_path)
        )
    else:
        print("\n[Step 4b/4] Skipping Audio Mix (Found cached temp_master_audio.wav)")

    # --------------------------------------------------------------
    # FINAL MUX: Combine Graded Video + Master Audio via FFmpeg
    # --------------------------------------------------------------
    print(f"\n[MUX] Multiplexing final master video -> {output_path}")
    mux_cmd = [
        "ffmpeg", "-y",
        "-i", str(graded_video_temp),
        "-i", str(master_audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path)
    ]
    mux_result = subprocess.run(mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if mux_result.returncode != 0:
        print(f"[-] Error during final FFmpeg audio/video muxing:\n{mux_result.stderr.decode('utf-8', errors='ignore')}")
        sys.exit(1)

    print("==================================================")
    print(f" [✨] SUCCESS! MASTER VIDEO READY: {output_path}")
    print("==================================================")


if __name__ == "__main__":
    main()