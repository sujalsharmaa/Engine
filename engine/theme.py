"""
engine/theme.py
-------------------------------------------------------------------------
Studio themes (full palettes, not just a spotlight colour) and the shared
named-colour table used by every component.
"""

from dataclasses import dataclass
from typing import Dict, Literal


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    card: str
    card_alt: str
    stroke: str
    text: str
    dim: str
    accent: str
    grid: str
    glow: bool = True
    spot_opacity: float = 0.16
    code_bg: str = "#090D16"


THEMES: Dict[str, Theme] = {
    "cyber_cyan": Theme("cyber_cyan", "#05070D", "#0B1120", "#131C31", "#1E293B", "#F8FAFC", "#94A3B8", "#00E5FF", "#16213A"),
    "monk_purple": Theme("monk_purple", "#07050F", "#120B24", "#1B1236", "#2A1B4D", "#F8FAFC", "#A5A1BD", "#9333EA", "#1E1538"),
    "emerald_matrix": Theme("emerald_matrix", "#030A07", "#07140E", "#0C2016", "#14532D", "#F0FDF4", "#86A897", "#10B981", "#0E2A1C"),
    "crimson_alert": Theme("crimson_alert", "#0B0507", "#190A0F", "#26111A", "#4C1D2B", "#FFF1F2", "#B49AA2", "#F43F5E", "#2A121B"),
    "solar_gold": Theme("solar_gold", "#0A0803", "#17120A", "#241C0E", "#4A3A14", "#FFFBEB", "#B5A98A", "#F59E0B", "#2B2210"),
    "midnight_blue": Theme("midnight_blue", "#030712", "#0A1226", "#111C3A", "#1D2B53", "#F1F5F9", "#8FA0C2", "#3B82F6", "#122044"),
    "sunset_orange": Theme("sunset_orange", "#0D0606", "#1C0F0B", "#2B1812", "#5A2A1B", "#FFF7ED", "#C2A294", "#FB7C3C", "#2D1710"),
    "paper_light": Theme("paper_light", "#F5F7FA", "#FFFFFF", "#EEF2F7", "#CBD5E1", "#0F172A", "#475569", "#2563EB", "#E2E8F0",
                         glow=False, spot_opacity=0.07, code_bg="#0F172A"),
}

DEFAULT_THEME = "cyber_cyan"

COLOR_MAP: Dict[str, str] = {
    "cyan": "#00E5FF",
    "blue": "#3B82F6",
    "green": "#10B981",
    "red": "#F43F5E",
    "amber": "#F59E0B",
    "purple": "#A855F7",
    "coral": "#E07A5F",
    "pink": "#EC4899",
    "teal": "#14B8A6",
    "lime": "#84CC16",
    "gray": "#64748B",
}

COLOR_NAMES = ["accent"] + list(COLOR_MAP.keys())


def get_theme(name: str) -> Theme:
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def resolve_color(name: str, theme: Theme) -> str:
    if name in (None, "", "accent"):
        return theme.accent
    if isinstance(name, str) and name.startswith("#"):
        return name
    return COLOR_MAP.get(name, theme.accent)


ThemeColor = Literal["accent", "cyan", "blue", "green", "red", "amber", "purple", "coral", "pink", "teal", "lime", "gray"]
