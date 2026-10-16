"""
engine/context.py
-------------------------------------------------------------------------
Ctx = everything a component needs: geometry for the current aspect ratio,
theme colours, text/icon/card factories, and the TIME API that keeps every
animation locked to the voiceover.

Time API (all times are absolute seconds on the video timeline):
    ctx.t0 / ctx.t1            scene window
    ctx.cue_times(exacts)      reveal moments for n items (spoken keyword or auto-spaced)
    ctx.at(t, *anims, ...)     wait until t, then play
    ctx.play(*anims, ...)      play now (run_time auto-clamped to the scene window)
    ctx.hold()                 wait until the scene's exit transition should start
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from manim import *  # noqa: F401,F403

from engine.theme import Theme, resolve_color
from engine.ui import fit_inside, get_icon, glass_card, pack_card, wrap_text

EXIT_TIME = {"fade": 0.45, "slide": 0.5, "zoom": 0.5, "wipe": 0.6, "cut": 0.0}

GEOMETRY = {
    #            W        H     header_y body_top  body_bottom(captions on/off)   font scale
    "16:9": dict(W=14.222, H=8.0, header_y=3.1, top=2.35, bot=(-2.95, -3.45), fs=1.0, tall=False),
    "9:16": dict(W=9.0, H=16.0, header_y=6.4, top=5.4, bot=(-4.0, -6.2), fs=1.5, tall=True),
    "1:1": dict(W=10.0, H=10.0, header_y=3.9, top=3.15, bot=(-3.3, -4.2), fs=1.22, tall=True),
}


@dataclass
class Region:
    cx: float
    cy: float
    w: float
    h: float

    @property
    def top(self): return self.cy + self.h / 2
    @property
    def bottom(self): return self.cy - self.h / 2
    @property
    def left(self): return self.cx - self.w / 2
    @property
    def right(self): return self.cx + self.w / 2
    @property
    def center(self): return np.array([self.cx, self.cy, 0.0])


def pick_mono_font() -> Optional[str]:
    try:
        import manimpango
        have = set(manimpango.list_fonts())
    except Exception:
        return None
    for f in ("JetBrains Mono", "Fira Code", "DejaVu Sans Mono", "Liberation Mono", "Ubuntu Mono", "Courier New"):
        if f in have:
            return f
    return "Monospace"


def pick_ui_font() -> Optional[str]:
    try:
        import manimpango
        have = set(manimpango.list_fonts())
    except Exception:
        return None
    for f in ("Inter", "Roboto", "Noto Sans", "Open Sans", "DejaVu Sans", "Liberation Sans", "Arial"):
        if f in have:
            return f
    return None


class Ctx:
    def __init__(self, scene, sb: dict, sc: dict, theme: Theme):
        self.scene = scene
        self.sb = sb
        self.sc = sc
        self.theme = theme
        self.aspect = sb.get("aspect_ratio", "16:9")
        g = GEOMETRY[self.aspect]
        self.W, self.H = g["W"], g["H"]
        self.portrait = g["tall"]
        self.font_scale = g["fs"]
        self.captions_on = sb.get("captions", "pop") != "off"
        cap_idx = 0 if self.captions_on else 1
        self.header_y = g["header_y"]
        self.top = g["top"]
        self.bot = g["bot"][cap_idx]
        self.margin = 0.6
        self.t0, self.t1 = float(sc["t0"]), float(sc["t1"])
        self.dur = self.t1 - self.t0
        self.words = sc.get("words", [])
        self.exit_time = EXIT_TIME.get(sc.get("transition", "fade"), 0.45)
        self.mono = pick_mono_font()
        self.ui_font = pick_ui_font()
        self.accent = theme.accent

    # ---------------------------------------------------------- geometry --
    @property
    def body(self) -> Region:
        return Region(0, (self.top + self.bot) / 2, self.W - 2 * self.margin, self.top - self.bot)

    @property
    def full(self) -> Region:
        """Whole safe area (use when a scene has no header)."""
        top = self.H / 2 - (0.9 if not self.portrait else 1.4)
        return Region(0, (top + self.bot) / 2, self.W - 2 * self.margin, top - self.bot)

    def region(self, has_header: bool) -> Region:
        return self.body if has_header else self.full

    # ------------------------------------------------------------ colours --
    def color(self, name: Optional[str]) -> str:
        return resolve_color(name or "accent", self.theme)

    # -------------------------------------------------------------- mobs --
    def fs(self, size: float) -> float:
        return size * self.font_scale

    def T(self, s: str, size: float = 24, color: Optional[str] = None, bold: bool = False, mono: bool = False, **kw):
        kw.setdefault("color", color or self.theme.text)
        if bold:
            kw["weight"] = BOLD
        if mono and self.mono:
            kw["font"] = self.mono
        elif self.ui_font:
            kw.setdefault("font", self.ui_font)
        return Text(s, font_size=self.fs(size), **kw)

    def wrap(self, s: str, size: float, max_w: float, align=LEFT, color: Optional[str] = None, bold=False, **kw):
        kw.setdefault("color", color or self.theme.text)
        if bold:
            kw["weight"] = BOLD
        if self.ui_font:
            kw.setdefault("font", self.ui_font)
        kw.setdefault("line_buff", 0.1 + 0.0016 * self.fs(size))
        return wrap_text(s, self.fs(size), max_w, align=align, **kw)

    def icon(self, name: str, height: float = 0.6, color: Optional[str] = None, brand: bool = False):
        return get_icon(name, height=height, color=color or self.theme.text, use_brand_color=brand)

    def card(self, w, h, color, fill=None, glow=True, **kw):
        return glass_card(self.theme, w, h, color, fill=fill, glow=glow, **kw)

    def pack(self, w, h, content, color, fill=None, glow=True, **kw):
        return pack_card(self.theme, w, h, content, color, fill=fill, glow=glow, **kw)

    def fit(self, mob, w, h, pad=0.1):
        return fit_inside(mob, w, h, pad=pad)

    def make_header(self, heading: str, subheading: str = "", color: Optional[str] = None):
        if not heading:
            return VGroup()
        col = color or self.accent
        bar = RoundedRectangle(width=0.12, height=0.65 * (1.2 if self.portrait else 1), corner_radius=0.05,
                               fill_color=col, fill_opacity=1, stroke_width=0)
        h_txt = self.T(heading, 32, bold=True)
        stack = h_txt
        if subheading:
            stack = VGroup(h_txt, self.T(subheading, 18, color=self.theme.dim)).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        grp = VGroup(bar, stack).arrange(RIGHT, buff=0.22)
        bar.stretch_to_fit_height(stack.height + 0.05)
        fit_inside(grp, self.W - 2 * self.margin, 1.3, pad=0.02)
        grp.move_to(UP * self.header_y)
        return grp

    def show_header(self, v, color: Optional[str] = None):
        h = self.make_header(getattr(v, "heading", ""), getattr(v, "subheading", ""), color)
        if len(h) > 0:
            self.play(FadeIn(h, shift=DOWN * 0.2), sfx="whoosh_soft.wav", rt=0.5)
        return h

    # -------------------------------------------------------------- time --
    @property
    def now(self) -> float:
        return float(self.scene.renderer.time)

    @property
    def end(self) -> float:
        """Latest moment content animations may run until."""
        return self.t1 - self.exit_time

    def wait_until(self, t: float):
        dt = t - self.now
        if dt > 0.03:
            self.scene.wait(dt)

    def play(self, *anims, sfx: Optional[str] = None, rt: float = 0.6, db: float = -10.0, **kw):
        room = self.end - self.now
        rt = max(0.06, min(rt, room if room > 0.06 else 0.06))
        self.scene.play_with_sfx(*anims, sfx_name=sfx, volume_db=db, run_time=rt, **kw)

    def at(self, t: float, *anims, **kw):
        self.wait_until(t)
        self.play(*anims, **kw)

    def hold(self):
        self.wait_until(self.end)

    def mark_sfx(self, name: str, t: Optional[float] = None, db: float = -14.0):
        self.scene.sfx_cue_sheet.append({"time_sec": round(float(self.now if t is None else t), 3), "sfx": name, "volume_db": db})

    def cue_times(self, exacts: List[Optional[float]], start_offset: float = 0.7, end_pad: float = 1.1) -> List[float]:
        """Reveal moment for each of n items. Spoken keywords win; gaps are interpolated."""
        n = len(exacts)
        if n == 0:
            return []
        lo = self.t0 + start_offset
        hi = max(lo + 0.3 * n, self.end - end_pad)
        ks = [-1]
        ts = [lo - (hi - lo) / (n + 1)]
        for i, e in enumerate(exacts):
            if e is not None:
                ks.append(i)
                ts.append(max(float(e) - 0.08, self.t0 + 0.15))
        ks.append(n)
        ts.append(hi)
        order = np.argsort(ks)
        ks = [ks[i] for i in order]
        ts = list(np.maximum.accumulate([ts[i] for i in order]))
        times = np.interp(np.arange(n), ks, ts)
        out = []
        for i, t in enumerate(times):
            t = float(t)
            if out:
                t = max(t, out[-1] + 0.2)
            out.append(min(t, self.end - 0.3))
        return out

    def scene_words(self):
        return self.words
