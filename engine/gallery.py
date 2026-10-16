"""
engine/gallery.py
-------------------------------------------------------------------------
Builds a showcase storyboard from every registered component's built-in
example. Used for visual regression checks and as a catalogue you can
render yourself:

    python -m engine.gallery --aspect 9:16 --out examples/gallery_9x16.json
    python run_studio.py --script examples/gallery_9x16.json --preview
"""

import argparse
import json
from pathlib import Path

from engine.registry import load_components


def build_gallery(aspect: str = "16:9", theme: str = "cyber_cyan", only=None) -> dict:
    reg = load_components()
    scenes = []
    for name in sorted(reg):
        if only and name not in only:
            continue
        comp = reg[name]
        if not comp.example:
            continue
        scenes.append({
            "scene_id": name.lower(),
            "narration_text": comp.example_narration or f"This is the {name} component.",
            "visual": comp.example,
        })
    return {"title": "Component Gallery", "aspect_ratio": aspect, "studio_theme": theme, "fps": 30, "scenes": scenes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aspect", default="16:9")
    ap.add_argument("--theme", default="cyber_cyan")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", default="examples/gallery.json")
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(build_gallery(a.aspect, a.theme, a.only), indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
