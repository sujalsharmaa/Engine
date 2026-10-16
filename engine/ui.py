"""
engine/ui.py
-------------------------------------------------------------------------
Shared drawing helpers: safe fitting, glass cards, offline icon library,
text wrapping, syntax-highlighted code lines.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from manim import *  # noqa: F401,F403

ICON_ROOT = Path(__file__).resolve().parent.parent / "assets" / "icons"

ICON_ALIASES = {
    "alert": "triangle-alert", "warning": "triangle-alert", "shield": "shield-check", "file": "file-code",
    "bot": "bot", "ai": "brain-circuit", "brain": "brain", "cloud": "cloud", "aws": "cloud", "azure": "cloud",
    "api": "plug", "web": "globe", "internet": "globe", "network": "network", "money": "banknote",
    "cash": "banknote", "growth": "trending-up", "decline": "trending-down", "idea": "lightbulb",
    "time": "clock", "speed": "gauge", "security": "shield-check", "user": "user", "users": "users",
    "code": "code", "terminal": "terminal", "check": "circle-check", "cross": "circle-x", "star": "star",
    "rocket": "rocket", "target": "target", "key": "key-round", "mail": "mail", "phone": "smartphone",
    "chart": "chart-column", "docs": "file-text", "folder": "folder", "search": "search", "heart": "heart",
    "java": "coffee", "csharp": "hash", "windows": "app-window", "microsoft": "app-window", "amazon": "shopping-cart",
    "openai": "sparkles", "slack": "message-square", "linkedin": "briefcase", "vscode": "code",
    "kafka": "workflow", "cassandra": "database", "aws-s3": "database", "grpc": "plug",
}


# ---------------------------------------------------------------- layout --
def fit_inside(mob, max_w: float, max_h: float, pad: float = 0.22):
    avail_w = max(0.1, max_w - 2 * pad)
    avail_h = max(0.1, max_h - 2 * pad)
    if mob.width > avail_w:
        mob.scale_to_fit_width(avail_w)
    if mob.height > avail_h:
        mob.scale_to_fit_height(avail_h)
    return mob


def wrap_text(s: str, size: float, max_w: float, align=LEFT, line_buff=0.14, **kw):
    """Word-wrap using measured width of the full string; returns a VGroup of lines."""
    probe = Text(s, font_size=size, **kw)
    if probe.width <= max_w or " " not in s:
        return VGroup(probe)
    per_char = probe.width / max(1, len(s))
    max_chars = max(6, int(max_w / per_char))
    lines, cur = [], ""
    for word in s.split():
        if cur and len(cur) + 1 + len(word) > max_chars:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    g = VGroup(*[Text(l, font_size=size, **kw) for l in lines]).arrange(DOWN, aligned_edge=align, buff=line_buff)
    return g


# ----------------------------------------------------------------- cards --
def glass_card(theme, width, height, color, fill=None, corner_radius=0.2, glow=True, stroke_width=2.0):
    g = VGroup()
    if glow and theme.glow:
        for sw, op in [(14, 0.05), (7, 0.12), (3, 0.25)]:
            g.add(RoundedRectangle(width=width, height=height, corner_radius=corner_radius, fill_opacity=0,
                                   stroke_color=color, stroke_width=sw, stroke_opacity=op))
    g.add(RoundedRectangle(width=width, height=height, corner_radius=corner_radius,
                           fill_color=fill or theme.card, fill_opacity=0.94 if theme.glow else 1.0,
                           stroke_color=color, stroke_width=stroke_width))
    return g


def pack_card(theme, width, height, content, color, fill=None, pad=0.25, tilt_y=0.0, glow=True):
    card = glass_card(theme, width, height, color, fill=fill, glow=glow)
    fit_inside(content, width, height, pad=pad)
    content.move_to(card.get_center())
    full = VGroup(card, content)
    if tilt_y:
        full.rotate(tilt_y, axis=UP)
    return full


def spotlight(color_hex, radius=5.5, max_opacity=0.16, steps=30):
    rings = VGroup()
    for i in range(steps):
        r = radius * (1 - i / steps)
        a = (max_opacity / 1.6) * ((i / steps) ** 1.6) * 0.62 + (max_opacity / steps) * 0.38
        rings.add(Circle(radius=r, fill_color=color_hex, fill_opacity=a, stroke_width=0))
    return rings


# ----------------------------------------------------------------- icons --
@lru_cache(maxsize=1)
def _brand_colors():
    p = ICON_ROOT / "brands" / "_colors.json"
    return json.loads(p.read_text()) if p.exists() else {}


def brand_color(name: str):
    return _brand_colors().get(name.lower().strip())


def _icon_file(name: str):
    key = name.lower().strip().replace(" ", "-").replace("_", "-")
    for cand in (key, ICON_ALIASES.get(key)):
        if not cand:
            continue
        for folder in ("lucide", "brands", ""):
            p = ICON_ROOT / folder / f"{cand}.svg"
            if p.exists():
                return p, folder
    # fuzzy: first lucide icon containing the name
    hits = sorted((ICON_ROOT / "lucide").glob(f"*{key}*.svg"))
    if hits:
        return hits[0], "lucide"
    return None, ""


def list_icons():
    out = []
    for folder in ("lucide", "brands"):
        out += sorted(p.stem for p in (ICON_ROOT / folder).glob("*.svg"))
    return out


def vector_fallback_icon(color):
    box = RoundedRectangle(width=1.0, height=1.0, corner_radius=0.2, color=color, fill_color=color, fill_opacity=0.18, stroke_width=2.5)
    core = Circle(radius=0.26, color=WHITE, stroke_width=2.5)
    return VGroup(box, core)


def get_icon(name: str, height: float = 0.6, color=WHITE, use_brand_color: bool = False):
    path, folder = _icon_file(name or "")
    if path is not None:
        try:
            svg = SVGMobject(str(path))
            stroke_style = folder == "lucide" or (folder == "" and 'fill="none"' in path.read_text(errors="ignore")[:600])
            if stroke_style:
                svg.set_fill(opacity=0)
                svg.set_stroke(color=color, width=3.2)
            else:
                col = brand_color(path.stem) if (folder == "brands" and use_brand_color) else None
                svg.set_fill(color=col or color, opacity=1)
                svg.set_stroke(width=0)
            svg.set(height=height)
            return svg
        except Exception:
            pass
    ic = vector_fallback_icon(color)
    ic.set(height=height)
    return ic


# ------------------------------------------------------------------ code --
def code_lines_markup(lines, language: str, theme_dark=True):
    """Return list of Pango-markup strings, one per line, coloured by Pygments."""
    try:
        from pygments import lex
        from pygments.lexers import get_lexer_by_name, guess_lexer
        from pygments.token import Token
        try:
            lexer = get_lexer_by_name(language or "text")
        except Exception:
            lexer = guess_lexer("\n".join(lines))
    except Exception:
        return [escape(l) or " " for l in lines]

    palette = {
        Token.Keyword: "#C792EA", Token.Keyword.Type: "#FFCB6B", Token.Name.Function: "#82AAFF",
        Token.Name.Class: "#FFCB6B", Token.Name.Builtin: "#82AAFF", Token.String: "#C3E88D",
        Token.Number: "#F78C6C", Token.Comment: "#697098", Token.Operator: "#89DDFF",
        Token.Name.Decorator: "#FFCB6B", Token.Name.Tag: "#F07178", Token.Name.Attribute: "#FFCB6B",
        Token.Literal: "#F78C6C",
    }

    def colour(ttype):
        while ttype is not Token and ttype is not None:
            if ttype in palette:
                return palette[ttype]
            ttype = ttype.parent
        return "#E2E8F0"

    out = []
    for line in lines:
        parts = []
        for ttype, value in lex(line, lexer):
            value = value.rstrip("\n")
            if value == "":
                continue
            parts.append(f'<span foreground="{colour(ttype)}">{escape(value)}</span>')
        out.append("".join(parts) or " ")
    return out
