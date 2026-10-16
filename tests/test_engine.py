"""pytest -q   (no audio / no rendering needed)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from engine.gallery import build_gallery
from engine.registry import load_components
from engine.schema import VideoStoryboard
from engine.timing import align_script_to_transcript, find_keyword, scene_windows


def test_every_component_has_valid_example():
    reg = load_components()
    assert len(reg) >= 20
    for name, comp in reg.items():
        assert comp.example, f"{name} has no example"
        comp.Spec.model_validate(comp.example)


@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1"])
def test_gallery_validates(aspect):
    VideoStoryboard.model_validate(build_gallery(aspect))


def test_unknown_component_is_reported():
    with pytest.raises(Exception) as e:
        VideoStoryboard.model_validate({"scenes": [{"scene_id": "a", "narration_text": "x", "visual": {"component_type": "Nope"}}]})
    assert "unknown component_type" in str(e.value)


def test_alignment_survives_misheard_words():
    narr = ["Production is down at three AM.", "Push monitoring floods the server."]
    fake, t = [], 0.0
    for w in "Production is down at three AM um Push monitoring floods the server".split():
        fake.append({"word": w, "start": t, "end": t + 0.3})
        t += 0.4
    words = align_script_to_transcript(narr, fake, t)
    wins = scene_windows(words, t)
    assert wins[0][0] == 0.0
    assert abs(wins[1][0] - (6 * 0.4 + 0.4 - 0.15)) < 0.2
    assert find_keyword(words[1], "floods") == pytest.approx(9 * 0.4, abs=0.05)
