"""
engine/captions.py
-------------------------------------------------------------------------
Burned-in captions from the SCRIPT words (so spelling is always right),
timed by the voiceover alignment. Output is an ASS file rendered by ffmpeg.

  pop  : short chunks, the spoken word is highlighted in the accent colour
  line : short chunks, no per-word highlight
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

CHUNK_WORDS = {"9:16": 3, "1:1": 4, "16:9": 6}
CHUNK_CHARS = {"9:16": 20, "1:1": 26, "16:9": 44}


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _bgr(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}&".upper()


def pick_caption_font() -> str:
    try:
        out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, timeout=10).stdout
        fams = {f.strip() for line in out.splitlines() for f in line.split(",")}
        for f in ("Inter", "Roboto", "Noto Sans", "DejaVu Sans", "Liberation Sans"):
            if f in fams:
                return f
    except Exception:
        pass
    return "Arial"


def _clean(w: str) -> str:
    return re.sub(r"[{}\\]", "", w).replace("\n", " ")


def chunk_words(words: List[Dict[str, Any]], aspect: str) -> List[List[Dict[str, Any]]]:
    max_w, max_c = CHUNK_WORDS.get(aspect, 5), CHUNK_CHARS.get(aspect, 30)
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_w or sum(len(x["word"]) + 1 for x in cur) + len(w["word"]) > max_c or w["start"] - cur[-1]["end"] > 0.7):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w["word"].endswith((".", "?", "!")) or (w["word"].endswith((",", ";", ":")) and len(cur) >= 2):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(compiled: Dict[str, Any], width: int, height: int, accent: str, out_path: str) -> bool:
    style = compiled.get("captions", "pop")
    if style == "off":
        return False
    aspect = compiled.get("aspect_ratio", "16:9")
    words = [w for sc in compiled["scenes"] for w in sc.get("words", [])]
    if not words:
        return False
    font = pick_caption_font()
    size = int({"9:16": 0.036, "1:1": 0.052, "16:9": 0.056}.get(aspect, 0.05) * height)
    y = int({"9:16": 0.80, "1:1": 0.86, "16:9": 0.88}.get(aspect, 0.85) * height)
    base = _bgr(compiled.get("caption_color", "#FFFFFF"))
    hi = _bgr(accent)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},{base},{base},&H00000000&,&H96000000&,-1,0,0,0,100,100,0,0,1,{max(3, size // 9)},2,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    chunks = chunk_words(words, aspect)
    pos = f"{{\\an5\\pos({width // 2},{y})}}"
    for ci, chunk in enumerate(chunks):
        c_start = chunk[0]["start"]
        nxt = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else chunk[-1]["end"] + 0.4
        c_end = min(nxt, chunk[-1]["end"] + 0.5) if nxt - chunk[-1]["end"] > 0.5 else nxt
        if style == "line":
            text = " ".join(_clean(w["word"]) for w in chunk)
            lines.append(f"Dialogue: 0,{_ass_time(c_start)},{_ass_time(c_end)},Cap,,0,0,0,,{pos}{text}")
            continue
        for k, w in enumerate(chunk):
            s = w["start"] if k else c_start
            e = chunk[k + 1]["start"] if k + 1 < len(chunk) else c_end
            parts = []
            for j, ww in enumerate(chunk):
                col = hi if j == k else base
                parts.append(f"{{\\c{col}}}{_clean(ww['word'])}")
            lines.append(f"Dialogue: 0,{_ass_time(s)},{_ass_time(e)},Cap,,0,0,0,,{pos}{' '.join(parts)}")
    Path(out_path).write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
    return True
