"""
engine/timing.py
-------------------------------------------------------------------------
Audio-driven timing, with NO manual timestamps in the JSON.

1. Scenes are located in the voiceover by aligning each scene's
   `narration_text` against the Whisper transcript (difflib sequence
   alignment), so Whisper mishearing a word ("PromQL" -> "prom QL") does not
   break anything.
2. Every word of the *script* (not the transcript) gets a time, so captions
   and kinetic text show the exact words you wrote.
3. `trigger_keyword`s are bound to the moment that word is spoken.
4. With no audio at all, timing is estimated so you can preview silently.
"""

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

LEAD_IN = 0.15       # visuals appear slightly before the first word is spoken
TAIL = 0.6           # hold after the last word
MIN_SCENE = 1.2


def _tok(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", s.lower().replace("’", "").replace("'", ""))


def _tok_match(a: str, b: str) -> bool:
    if a == b:
        return True
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True
    return False


def expand_transcript(words: List[Dict[str, Any]]) -> List[Tuple[str, float, float]]:
    out = []
    for w in words:
        toks = _tok(w.get("word", ""))
        if not toks:
            continue
        s, e = float(w["start"]), float(w["end"])
        step = (e - s) / len(toks)
        for i, t in enumerate(toks):
            out.append((t, s + i * step, s + (i + 1) * step))
    return out


def estimate_word_times(narrations: List[str]) -> Tuple[List[List[Dict[str, Any]]], float]:
    """Silent-preview timing: ~2.6 words/sec with punctuation pauses."""
    t = 0.0
    scenes_words = []
    for text in narrations:
        sw = []
        for w in text.split():
            d = 0.36 + 0.012 * len(w)
            sw.append({"word": w, "start": round(t, 3), "end": round(t + d, 3)})
            t += d
            if w.endswith((".", "!", "?")):
                t += 0.35
            elif w.endswith((",", ";", ":")):
                t += 0.18
        t += 0.25
        scenes_words.append(sw)
    return scenes_words, t


def align_script_to_transcript(
    narrations: List[str],
    transcript_words: List[Dict[str, Any]],
    audio_duration: float,
) -> List[List[Dict[str, Any]]]:
    """Returns, per scene, the list of SCRIPT words with start/end seconds."""
    exp: List[Tuple[str, int, int]] = []          # (token, scene, surface_idx)
    surfaces: List[List[str]] = []
    for si, text in enumerate(narrations):
        sw = text.split()
        surfaces.append(sw)
        for wi, w in enumerate(sw):
            for t in _tok(w):
                exp.append((t, si, wi))

    trans = expand_transcript(transcript_words)
    exp_tokens = [e[0] for e in exp]
    tr_tokens = [t[0] for t in trans]

    matched: Dict[int, float] = {}
    if exp_tokens and tr_tokens:
        sm = difflib.SequenceMatcher(None, exp_tokens, tr_tokens, autojunk=False)
        for a, b, size in sm.get_matching_blocks():
            for k in range(size):
                matched[a + k] = trans[b + k][1]

    n = len(exp)
    ks = [-1] + sorted(matched) + [n]
    ts = [0.0] + [matched[k] for k in sorted(matched)] + [audio_duration]
    exp_times = np.interp(np.arange(n), ks, ts) if n else np.array([])

    # first token time per (scene, surface word)
    first_time: Dict[Tuple[int, int], float] = {}
    for k, (_, si, wi) in enumerate(exp):
        first_time.setdefault((si, wi), float(exp_times[k]))

    scenes_words: List[List[Dict[str, Any]]] = []
    flat: List[Dict[str, Any]] = []
    for si, sw in enumerate(surfaces):
        row = []
        for wi, w in enumerate(sw):
            if (si, wi) in first_time:
                st = first_time[(si, wi)]
            else:  # pure punctuation word: inherit previous time
                st = row[-1]["start"] if row else (flat[-1]["start"] if flat else 0.0)
            row.append({"word": w, "start": round(st, 3), "end": 0.0})
        flat.extend(row)
        scenes_words.append(row)

    for i, w in enumerate(flat):
        nxt = flat[i + 1]["start"] if i + 1 < len(flat) else audio_duration
        w["end"] = round(max(w["start"] + 0.08, min(nxt, w["start"] + 0.9)), 3)
    return scenes_words


def scene_windows(
    scenes_words: List[List[Dict[str, Any]]],
    total_duration: float,
    manual: Optional[List[Tuple[Optional[float], Optional[float]]]] = None,
) -> List[Tuple[float, float]]:
    n = len(scenes_words)
    starts: List[float] = []
    for i, sw in enumerate(scenes_words):
        if i == 0:
            starts.append(0.0)
            continue
        first = sw[0]["start"] if sw else starts[-1] + MIN_SCENE
        starts.append(max(starts[-1] + 0.5, first - LEAD_IN))
    ends = starts[1:] + [total_duration + TAIL]

    if manual:
        for i, (ms, me) in enumerate(manual):
            if ms is not None:
                starts[i] = ms
            if me is not None:
                ends[i] = me
        ends = [ends[i] if manual[i][1] is not None else (starts[i + 1] if i + 1 < n else ends[i]) for i in range(n)]

    return [(round(s, 3), round(max(e, s + 0.5), 3)) for s, e in zip(starts, ends)]


def find_keyword(words: List[Dict[str, Any]], keyword: str) -> Optional[float]:
    kt = _tok(keyword)
    if not kt:
        return None
    flat = [(t, w["start"]) for w in words for t in _tok(w["word"])]
    for i in range(len(flat) - len(kt) + 1):
        if all(_tok_match(flat[i + j][0], kt[j]) for j in range(len(kt))):
            return round(flat[i][1], 3)
    return None


def bind_cues(node: Any, scene_words: List[Dict[str, Any]], warnings: List[str], where: str) -> None:
    """Recursively turn every `trigger_keyword` into an absolute `exact_time`."""
    if isinstance(node, dict):
        kw = node.get("trigger_keyword")
        if kw:
            t = find_keyword(scene_words, kw)
            if t is None:
                warnings.append(f"{where}: trigger_keyword {kw!r} not found in this scene's narration (will be auto-spaced)")
            node["exact_time"] = t
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                bind_cues(v, scene_words, warnings, where)
    elif isinstance(node, list):
        for item in node:
            bind_cues(item, scene_words, warnings, where)
