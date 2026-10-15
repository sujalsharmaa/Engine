"""
engine/renderer_engine.py
-------------------------------------------------------------------------
Master Manim Rendering Engine supporting 8 ByteMonk-style components,
responsive 16:9 & 9:16 layouts, camera choreography, and auto SFX logging.
"""

import json
import os
import urllib.request
from pathlib import Path
from manim import *
import numpy as np

# =====================================================================
# 1. COLOR PALETTES & STUDIO THEMES
# =====================================================================
BG_DARK = "#05070D"
CARD_FILL = "#0B1120"
CARD_FILL_ALT = "#131C31"
CARD_STROKE = "#1E293B"
TEXT_WHITE = "#F8FAFC"
TEXT_DIM = "#94A3B8"

COLOR_MAP = {
    "cyan": "#00E5FF",
    "blue": "#3B82F6",
    "green": "#10B981",
    "red": "#F43F5E",
    "amber": "#F59E0B",
    "purple": "#A855F7",
    "coral": "#E07A5F",
}

THEME_SPOTLIGHTS = {
    "cyber_cyan": "#00E5FF",
    "monk_purple": "#9333EA",
    "emerald_matrix": "#10B981",
    "crimson_alert": "#F43F5E",
    "solar_gold": "#F59E0B",
}

ICON_DIR = Path("assets/icons")
ICON_URLS = {
    "database": "https://unpkg.com/lucide-static@latest/icons/database.svg",
    "server": "https://unpkg.com/lucide-static@latest/icons/server.svg",
    "bot": "https://unpkg.com/lucide-static@latest/icons/bot.svg",
    "zap": "https://unpkg.com/lucide-static@latest/icons/zap.svg",
    "shield": "https://unpkg.com/lucide-static@latest/icons/shield-check.svg",
    "cpu": "https://unpkg.com/lucide-static@latest/icons/cpu.svg",
    "globe": "https://unpkg.com/lucide-static@latest/icons/globe.svg",
    "lock": "https://unpkg.com/lucide-static@latest/icons/lock.svg",
    "file": "https://unpkg.com/lucide-static@latest/icons/file-code.svg",
    "alert": "https://unpkg.com/lucide-static@latest/icons/alert-triangle.svg",
    "flame": "https://unpkg.com/lucide-static@latest/icons/flame.svg",
    "git": "https://cdn.simpleicons.org/git/F05032",
    "prometheus": "https://cdn.simpleicons.org/prometheus/E6522C",
    "sqlite": "https://cdn.simpleicons.org/sqlite/003B57",
}


# =====================================================================
# 2. SAFE LAYOUT HELPERS, GLOW CARDS & VECTOR ICONS
# =====================================================================

def fit_inside(mob: Mobject, max_w: float, max_h: float, pad: float = 0.22) -> Mobject:
    """Guarantees `mob` never overflows (max_w, max_h) — zero text overlap."""
    avail_w = max(0.1, max_w - 2 * pad)
    avail_h = max(0.1, max_h - 2 * pad)
    if mob.width > avail_w:
        mob.scale_to_fit_width(avail_w)
    if mob.height > avail_h:
        mob.scale_to_fit_height(avail_h)
    return mob


def build_vector_icon(name: str, color=WHITE) -> VMobject:
    """High-precision geometric fallback icon so offline builds never fail."""
    g = VGroup()
    if name in ("database", "server"):
        for i in range(3):
            r = RoundedRectangle(width=1.1, height=0.26, corner_radius=0.06, color=color, fill_color=color, fill_opacity=0.2, stroke_width=2.5)
            d = Dot(r.get_left() + RIGHT * 0.2, radius=0.04, color=WHITE)
            g.add(VGroup(r, d).shift(UP * (0.34 - i * 0.34)))
    elif name == "shield":
        poly = Polygon(UP * 0.6, UR * 0.45 + UP * 0.2, DR * 0.35 + DOWN * 0.2, DOWN * 0.6, DL * 0.35 + DOWN * 0.2, UL * 0.45 + UP * 0.2, color=color, fill_color=color, fill_opacity=0.2, stroke_width=3)
        chk = VMobject(color=WHITE, stroke_width=3.5).set_points_as_corners([LEFT * 0.18, DOWN * 0.12, RIGHT * 0.22 + UP * 0.2])
        g.add(poly, chk)
    elif name in ("zap", "flame"):
        bolt = Polygon(UP * 0.6 + RIGHT * 0.1, LEFT * 0.25 + UP * 0.05, RIGHT * 0.05 + UP * 0.05, DOWN * 0.6 + LEFT * 0.1, RIGHT * 0.25 + DOWN * 0.05, LEFT * 0.05 + DOWN * 0.05, color=color, fill_color=color, fill_opacity=0.35, stroke_width=2.5)
        g.add(bolt)
    elif name == "alert":
        tri = RegularPolygon(n=3, color=color, fill_color=color, fill_opacity=0.2, stroke_width=3)
        bang = Line(UP * 0.15, DOWN * 0.1, color=WHITE, stroke_width=3.5)
        dot = Dot(DOWN * 0.24, radius=0.04, color=WHITE)
        g.add(tri, bang, dot)
    else:
        box = RoundedRectangle(width=1.0, height=1.0, corner_radius=0.2, color=color, fill_color=color, fill_opacity=0.18, stroke_width=2.5)
        core = Circle(radius=0.26, color=WHITE, stroke_width=2.5)
        g.add(box, core)
    return g


def get_icon(name: str, height: float = 0.6, color=WHITE) -> VMobject:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    key = name.lower().strip()
    svg_path = ICON_DIR / f"{key}.svg"
    if not svg_path.exists() and key in ICON_URLS:
        try:
            req = urllib.request.Request(ICON_URLS[key], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                raw = resp.read().decode("utf-8")
            raw = raw.replace('stroke="currentColor"', 'stroke="#FFFFFF"').replace('fill="currentColor"', 'fill="#FFFFFF"')
            svg_path.write_text(raw, encoding="utf-8")
        except Exception:
            pass
    if svg_path.exists():
        try:
            svg = SVGMobject(str(svg_path))
            svg.set_color(color)
            svg.set(height=height)
            return svg
        except Exception:
            pass
    vec = build_vector_icon(key, color=color)
    vec.set(height=height)
    return vec


def create_radial_spotlight(color_hex: str, radius: float = 5.5, max_opacity: float = 0.16) -> VGroup:
    rings = VGroup()
    steps = 20
    for i in range(steps):
        r = radius * (1 - i / steps)
        alpha = max_opacity * ((i / steps) ** 1.5)
        rings.add(Circle(radius=r, fill_color=color_hex, fill_opacity=alpha, stroke_width=0))
    return rings


def create_glass_card(width: float, height: float, color=COLOR_MAP["cyan"], fill_color=CARD_FILL, corner_radius=0.2, tilt_y=0.0, glow=True) -> VGroup:
    g = VGroup()
    if glow:
        for sw, op in [(14, 0.05), (7, 0.12), (3, 0.25)]:
            g.add(RoundedRectangle(width=width, height=height, corner_radius=corner_radius, fill_opacity=0, stroke_color=color, stroke_width=sw, stroke_opacity=op))
    body = RoundedRectangle(width=width, height=height, corner_radius=corner_radius, fill_color=fill_color, fill_opacity=0.93, stroke_color=color, stroke_width=2.0)
    g.add(body)
    if tilt_y != 0:
        g.rotate(tilt_y, axis=UP)
    return g


def pack_glass_card(width: float, height: float, content: Mobject, color=COLOR_MAP["cyan"], fill_color=CARD_FILL, pad=0.25, tilt_y=0.0, glow=True) -> VGroup:
    card = create_glass_card(width, height, color=color, fill_color=fill_color, glow=glow)
    fit_inside(content, width, height, pad=pad)
    content.move_to(card.get_center())
    full = VGroup(card, content)
    if tilt_y != 0:
        full.rotate(tilt_y, axis=UP)
    return full


# =====================================================================
# 3. INSTRUMENTED SCENE WITH AUTO-SFX LOGGING & CAMERA ENGINE
# =====================================================================

class InstrumentedScene(MovingCameraScene):
    def setup(self):
        super().setup()
        self.sfx_cue_sheet = []

    def play_with_sfx(self, *animations, sfx_name: str = None, volume_db: float = -10.0, **kwargs):
        if sfx_name:
            self.sfx_cue_sheet.append({
                "time_sec": round(float(self.renderer.time), 3),
                "sfx": sfx_name,
                "volume_db": volume_db
            })
        self.play(*animations, **kwargs)

    def export_sfx_cues(self, filepath="sfx_cues.json"):
        Path(filepath).write_text(json.dumps(self.sfx_cue_sheet, indent=2), encoding="utf-8")


class StoryboardRenderer(InstrumentedScene):
    def construct(self):
        sb_path = Path("compiled_storyboard.json")
        if not sb_path.exists():
            raise FileNotFoundError("compiled_storyboard.json missing. Run Step 2 first!")

        sb = json.loads(sb_path.read_text(encoding="utf-8"))
        self.is_portrait = sb.get("aspect_ratio", "16:9") == "9:16"

        # Dynamically configure camera frame for 9:16 Shorts vs 16:9 Full Video
        if self.is_portrait:
            self.camera.frame.set(width=9.0, height=16.0)
            self.stage_w = 8.2
            self.header_y = 6.5
        else:
            self.camera.frame.set(width=14.22, height=8.0)
            self.stage_w = 12.6
            self.header_y = 3.1

        config.background_color = BG_DARK

        # Persistent ambient spotlight
        spot_col = THEME_SPOTLIGHTS.get(sb.get("studio_theme", "cyber_cyan"), "#00E5FF")
        self.spotlight = create_radial_spotlight(spot_col, radius=6.2 if not self.is_portrait else 5.0)
        self.add(self.spotlight)

        for scene_data in sb.get("scenes", []):
            self.render_scene_block(scene_data)
            self.clear_stage()

        self.export_sfx_cues()

    def clear_stage(self):
        # Reset camera position and scale smoothly before wiping
        self.camera.frame.move_to(ORIGIN)
        if self.is_portrait:
            self.camera.frame.set(width=9.0, height=16.0)
        else:
            self.camera.frame.set(width=14.22, height=8.0)

        to_remove = [m for m in self.mobjects if m is not self.spotlight]
        if to_remove:
            self.play(*[FadeOut(m, shift=DOWN * 0.2) for m in to_remove], run_time=0.5)

    def make_header(self, heading: str, subheading: str = "", color=COLOR_MAP["cyan"]) -> VGroup:
        if not heading:
            return VGroup()
        bar = RoundedRectangle(width=0.12, height=0.65, corner_radius=0.05, fill_color=color, fill_opacity=1, stroke_width=0)
        h_txt = Text(heading, font_size=32, weight=BOLD, color=TEXT_WHITE)
        if subheading:
            s_txt = Text(subheading, font_size=18, color=TEXT_DIM)
            stack = VGroup(h_txt, s_txt).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        else:
            stack = h_txt
        grp = VGroup(bar, stack).arrange(RIGHT, buff=0.2)
        fit_inside(grp, self.stage_w, 1.1, pad=0.05)
        grp.move_to(UP * self.header_y)
        return grp

    def render_scene_block(self, scene: dict):
        visual = scene.get("visual", {})
        c_type = visual.get("component_type", "")

        dispatch = {
            "HeroQuoteHook": self.render_hero_quote_hook,
            "TiltedCardComparison": self.render_tilted_cards,
            "ArchitectureFlowCanvas": self.render_architecture_flow,
            "MacOSCodeWindow": self.render_macos_code_window,
            "RetroCrashDialog": self.render_retro_crash_dialog,
            "HexMemoryInspector": self.render_hex_memory_inspector,
            "BTreeCameraZoom": self.render_btree_camera_zoom,
            "FeatureCarouselCards": self.render_feature_carousel,
        }
        handler = dispatch.get(c_type)
        if handler:
            handler(visual)

    # -----------------------------------------------------------------
    # COMPONENT 1: HERO QUOTE HOOK (Like 00:01 Linus Torvalds in SQLite)
    # -----------------------------------------------------------------
    def render_hero_quote_hook(self, v: dict):
        col = COLOR_MAP.get(v.get("theme_color", "purple"), "#A855F7")

        # Glowing Avatar Badge
        aura = Circle(radius=1.55, fill_color=col, fill_opacity=0.28, stroke_color=col, stroke_width=3)
        inner_circle = Circle(radius=1.25, fill_color=CARD_FILL_ALT, fill_opacity=0.95, stroke_color=TEXT_WHITE, stroke_width=1.5)
        initials = "".join([part[0] for part in v.get("speaker_name", "AI").split()[:2]]).upper()
        monogram = Text(initials, font_size=52, weight=BOLD, color=TEXT_WHITE)
        name_tag = Text(v.get("speaker_name", ""), font_size=22, weight=BOLD, color=TEXT_WHITE)
        role_tag = Text(v.get("speaker_role", ""), font_size=15, color=col)
        avatar_block = VGroup(VGroup(aura, inner_circle, monogram), name_tag, role_tag).arrange(DOWN, buff=0.14)

        # Quote + Highlighter Bar
        q_text = Text(f"“{v.get('quote_text', '')}”", font_size=34, weight=BOLD, color=TEXT_WHITE)
        fit_inside(q_text, 6.8 if not self.is_portrait else 7.6, 2.2)

        hl_bar = RoundedRectangle(
            width=q_text.width + 0.3,
            height=0.52,
            corner_radius=0.08,
            fill_color=col,
            fill_opacity=0.45,
            stroke_width=0,
        ).move_to(q_text.get_bottom() + UP * 0.22)

        quote_group = VGroup(hl_bar, q_text)

        if v.get("year_badge"):
            yr_txt = Text(str(v["year_badge"]), font_size=56, weight=BOLD, color=col)
            quote_group = VGroup(yr_txt, quote_group).arrange(DOWN, aligned_edge=LEFT, buff=0.35)

        if self.is_portrait:
            layout = VGroup(avatar_block, quote_group).arrange(DOWN, buff=0.75).move_to(ORIGIN)
        else:
            layout = VGroup(avatar_block, quote_group).arrange(RIGHT, buff=1.1).move_to(ORIGIN)

        self.play_with_sfx(FadeIn(avatar_block, scale=0.9), sfx_name="whoosh_soft.wav", run_time=0.8)
        self.play_with_sfx(Write(q_text), GrowFromEdge(hl_bar, LEFT), sfx_name="card_pop.wav", run_time=1.1)
        if v.get("year_badge"):
            self.play(FadeIn(quote_group[0], shift=UP * 0.2), run_time=0.6)
        self.wait(1.8)

    # -----------------------------------------------------------------
    # COMPONENT 2: 2.5D TILTED CARD COMPARISON (Like 00:28 5M vs 1M vs 1T)
    # -----------------------------------------------------------------
    def render_tilted_cards(self, v: dict):
        header = self.make_header(v.get("heading", ""), v.get("subheading", ""))
        self.play_with_sfx(FadeIn(header, shift=DOWN * 0.2), sfx_name="whoosh_soft.wav", run_time=0.6)

        cards_data = v.get("cards", [])
        n = len(cards_data)
        built_cards = VGroup()

        for i, c_info in enumerate(cards_data):
            col = COLOR_MAP.get(c_info.get("color_theme", "cyan"), COLOR_MAP["cyan"])
            is_hero = c_info.get("is_hero", False)
            c_w = (3.6 if is_hero else 3.1) if not self.is_portrait else 7.6
            c_h = (4.3 if is_hero else 3.7) if not self.is_portrait else (2.6 if is_hero else 2.2)

            ic = get_icon(c_info.get("icon", "database"), height=0.65 if not self.is_portrait else 0.55, color=col)
            title = Text(c_info["title"], font_size=26 if is_hero else 22, weight=BOLD, color=TEXT_WHITE)
            val = Text(c_info["value"], font_size=68 if is_hero else 54, weight=BOLD, color=col if is_hero else TEXT_WHITE)

            if self.is_portrait:
                left_col = VGroup(ic, title).arrange(RIGHT, buff=0.22)
                right_col = VGroup(val)
                if c_info.get("subtext"):
                    right_col.add(Text(c_info["subtext"], font_size=15, color=TEXT_DIM))
                    right_col.arrange(DOWN, buff=0.08)
                inner = VGroup(left_col, right_col).arrange(RIGHT, buff=0.65)
                tilt = 0.0
            else:
                inner_items = [ic, title, val]
                if c_info.get("subtext"):
                    inner_items.append(Text(c_info["subtext"], font_size=15, color=TEXT_DIM))
                inner = VGroup(*inner_items).arrange(DOWN, buff=0.18)
                tilt = (12 if i == 0 else (-12 if i == n - 1 else 6)) * DEGREES

            card_mob = pack_glass_card(c_w, c_h, inner, color=col, tilt_y=tilt, glow=True)
            built_cards.add(card_mob)

        if self.is_portrait:
            built_cards.arrange(DOWN, buff=0.35).move_to(DOWN * 0.4)
        else:
            built_cards.arrange(RIGHT, buff=0.45).move_to(DOWN * 0.4)

        for idx, card_mob in enumerate(built_cards):
            self.play_with_sfx(
                FadeIn(card_mob, shift=UP * 0.35, scale=0.9),
                sfx_name="card_pop.wav",
                run_time=0.75
            )
            self.wait(0.35)

        self.wait(1.8)

    # -----------------------------------------------------------------
    # COMPONENT 3: ARCHITECTURE FLOW CANVAS (Like 02:47 & 06:46 in SQLite)
    # -----------------------------------------------------------------
    def render_architecture_flow(self, v: dict):
        header = self.make_header(v.get("heading", ""), v.get("subheading", ""))
        self.play_with_sfx(FadeIn(header, shift=DOWN * 0.2), sfx_name="whoosh_soft.wav", run_time=0.6)

        nodes_spec = v.get("nodes", [])
        edges_spec = v.get("edges", [])
        node_map = {}
        node_group = VGroup()

        for n_spec in nodes_spec:
            col = COLOR_MAP.get(n_spec.get("color_theme", "cyan"), COLOR_MAP["cyan"])
            ic = get_icon(n_spec.get("icon", "server"), height=0.52, color=col)
            lbl = Text(n_spec["label"], font_size=20, weight=BOLD, color=TEXT_WHITE)
            items = [ic, lbl]
            if n_spec.get("sublabel"):
                items.append(Text(n_spec["sublabel"], font_size=14, color=TEXT_DIM))
            inner = VGroup(*items).arrange(DOWN if not self.is_portrait else RIGHT, buff=0.14)
            card = pack_glass_card(
                2.55 if not self.is_portrait else 7.4,
                2.1 if not self.is_portrait else 1.55,
                inner,
                color=col,
                glow=True
            )
            node_map[n_spec["node_id"]] = card
            node_group.add(card)

        if self.is_portrait:
            node_group.arrange(DOWN, buff=0.65).move_to(DOWN * 0.5)
        else:
            node_group.arrange(RIGHT, buff=0.65).move_to(DOWN * 0.4)

        self.play(LaggedStart(*[FadeIn(nd, scale=0.9) for nd in node_group], lag_ratio=0.15), run_time=1.2)

        edge_mobs = VGroup()
        packet_anims = []
        for e_spec in edges_spec:
            src = node_map.get(e_spec["source"])
            dst = node_map.get(e_spec["target"])
            if src and dst:
                col = COLOR_MAP.get(e_spec.get("color_theme", "cyan"), COLOR_MAP["cyan"])
                start_pt = src.get_bottom() if self.is_portrait else src.get_right()
                end_pt = dst.get_top() if self.is_portrait else dst.get_left()
                arr = Arrow(start_pt, end_pt, buff=0.1, color=col, stroke_width=3.5)
                edge_mobs.add(arr)
                if e_spec.get("label"):
                    e_lbl = Text(e_spec["label"], font_size=13, color=col)
                    e_lbl.next_to(arr, RIGHT if self.is_portrait else UP, buff=0.06)
                    edge_mobs.add(e_lbl)

                pkt = Dot(radius=0.08, color=col)
                packet_anims.append((pkt, Line(start_pt, end_pt)))

        if edge_mobs:
            self.play_with_sfx(Create(edge_mobs), sfx_name="card_pop.wav", run_time=0.9)
        if packet_anims:
            self.play(*[MoveAlongPath(p, path, rate_func=smooth) for p, path in packet_anims], run_time=1.1)
            for p, _ in packet_anims:
                self.remove(p)

        self.wait(1.6)

    # -----------------------------------------------------------------
    # COMPONENT 4: MACOS CODE WINDOW (Like 02:20 ~/sqlite/main.c)
    # -----------------------------------------------------------------
    def render_macos_code_window(self, v: dict):
        header = self.make_header(v.get("heading", ""))
        if len(header) > 0:
            self.play(FadeIn(header), run_time=0.5)

        win_w = 11.4 if not self.is_portrait else 8.2
        win_h = 5.4 if not self.is_portrait else 7.2
        win = create_glass_card(win_w, win_h, color="#334155", fill_color="#090D16", glow=True)
        win.move_to(DOWN * 0.35 if len(header) > 0 else ORIGIN)

        # Traffic light buttons
        dots = VGroup(
            Dot(radius=0.08, color="#FF5F56"),
            Dot(radius=0.08, color="#FFBD2E"),
            Dot(radius=0.08, color="#27C93F"),
        ).arrange(RIGHT, buff=0.14).move_to(win.get_corner(UL) + RIGHT * 0.65 + DOWN * 0.35)

        fp_txt = Text(v.get("filepath", "~/src/main.c"), font_size=16, color=TEXT_DIM).move_to(win.get_top() + DOWN * 0.35)
        top_sep = Line(win.get_left() + UP * (win_h / 2 - 0.68), win.get_right() + UP * (win_h / 2 - 0.68), color="#1E293B", stroke_width=2)

        hl_set = set(v.get("highlight_lines", []))
        rendered_lines = VGroup()
        for idx, line_str in enumerate(v.get("code_lines", []), start=1):
            num_t = Text(f"{idx:2d}", font_size=16, color="#475569")
            is_hl = idx in hl_set
            line_col = COLOR_MAP["cyan"] if is_hl else (COLOR_MAP["amber"] if line_str.strip().startswith("#") else TEXT_WHITE)
            code_t = Text(line_str if line_str.strip() else " ", font_size=17, color=line_col)
            row = VGroup(num_t, code_t).arrange(RIGHT, buff=0.35)
            rendered_lines.add(row)

        rendered_lines.arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        fit_inside(rendered_lines, win_w - 0.6, win_h - 1.3, pad=0.2)
        rendered_lines.move_to(win.get_center() + DOWN * 0.25)

        self.play_with_sfx(FadeIn(win), FadeIn(dots), FadeIn(fp_txt), Create(top_sep), sfx_name="whoosh_soft.wav", run_time=0.7)
        self.play(LaggedStart(*[FadeIn(ln, shift=RIGHT * 0.1) for ln in rendered_lines], lag_ratio=0.12), run_time=1.5)

        if v.get("badge_text"):
            badge = pack_glass_card(3.4, 0.85, Text(v["badge_text"], font_size=24, weight=BOLD, color=COLOR_MAP["cyan"]), color=COLOR_MAP["cyan"], glow=True)
            badge.move_to(win.get_corner(DR) + UL * 1.1)
            self.play_with_sfx(FadeIn(badge, scale=0.85), sfx_name="card_pop.wav", run_time=0.6)

        self.wait(1.8)

    # -----------------------------------------------------------------
    # COMPONENT 5: RETRO OS CRASH DIALOG (Like 01:45 Cannot Connect Error)
    # -----------------------------------------------------------------
    def render_retro_crash_dialog(self, v: dict):
        header = self.make_header(v.get("heading", "Single Point of Failure"), color=COLOR_MAP["red"])
        self.play(FadeIn(header), run_time=0.5)

        term_w = 10.6 if not self.is_portrait else 8.0
        term_h = 4.8 if not self.is_portrait else 6.0
        term = create_glass_card(term_w, term_h, color="#334155", fill_color="#070A12", glow=False).move_to(DOWN * 0.45)

        logs = VGroup(*[
            Text(log_line, font_size=15, color="#475569")
            for log_line in (v.get("terminal_logs") or [
                "[04:21:18] INFO  Connecting to primary server 10.0.4.21:9088...",
                "[04:21:21] WARN  Connection timeout after 3000ms. Retrying...",
                "[04:21:24] FATAL Socket closed unexpectedly by remote host.",
            ])
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        fit_inside(logs, term_w - 0.6, 1.8)
        logs.move_to(term.get_top() + DOWN * 1.1)

        # Classic System Error Modal
        modal_w = 6.8 if not self.is_portrait else 7.2
        modal_h = 2.65
        modal_bg = RoundedRectangle(width=modal_w, height=modal_h, corner_radius=0.08, fill_color="#D4D0C8", fill_opacity=1, stroke_color=WHITE, stroke_width=2.5)
        title_bar = Rectangle(width=modal_w - 0.1, height=0.45, fill_color="#0A246A", fill_opacity=1, stroke_width=0).move_to(modal_bg.get_top() + DOWN * 0.25)
        title_txt = Text(v.get("error_title", "System Error"), font_size=16, weight=BOLD, color=WHITE).move_to(title_bar.get_left() + RIGHT * 1.2)

        err_circle = Circle(radius=0.28, fill_color=COLOR_MAP["red"], fill_opacity=1, stroke_color=WHITE, stroke_width=2)
        err_x = Text("X", font_size=22, weight=BOLD, color=WHITE).move_to(err_circle)
        err_icon = VGroup(err_circle, err_x)

        msg_txt = Text(v.get("error_message", "Cannot connect to database server."), font_size=17, weight=BOLD, color="#111827")
        body_row = VGroup(err_icon, msg_txt).arrange(RIGHT, buff=0.28)
        fit_inside(body_row, modal_w - 0.6, 1.1)
        body_row.move_to(modal_bg.get_center() + UP * 0.1)

        ok_btn = VGroup(
            Rectangle(width=1.3, height=0.42, fill_color="#D4D0C8", fill_opacity=1, stroke_color="#111827", stroke_width=1.5),
            Text("Retry", font_size=14, color="#111827")
        ).move_to(modal_bg.get_bottom() + UP * 0.42)

        modal = VGroup(modal_bg, title_bar, title_txt, body_row, ok_btn).move_to(term.get_center() + DOWN * 0.2)

        self.play(FadeIn(term), FadeIn(logs), run_time=0.7)
        self.play_with_sfx(FadeIn(modal, scale=0.85), sfx_name="card_pop.wav", run_time=0.45)
        self.play(Wiggle(modal, scale_value=1.03, rotation_angle=0.015 * TAU), run_time=0.5)
        self.wait(1.6)

    # -----------------------------------------------------------------
    # COMPONENT 6: HEX MEMORY INSPECTOR (Like 04:19 100-Byte Header)
    # -----------------------------------------------------------------
    def render_hex_memory_inspector(self, v: dict):
        header = self.make_header(v.get("heading", "Binary Header Layout"), v.get("subheading", ""))
        self.play(FadeIn(header), run_time=0.5)

        grid_w = 11.4 if not self.is_portrait else 8.2
        grid_h = 3.4 if not self.is_portrait else 4.2
        board = create_glass_card(grid_w, grid_h, color=COLOR_MAP["green"], fill_color="#060B11", glow=True).move_to(UP * 0.35)

        sample_rows = [
            ("0000:", ["53", "51", "4C", "69", "74", "65", "20", "66"], v.get("ascii_preview", "SQLite format 3")),
            ("0010:", ["10", "00", "01", "01", "00", "40", "20", "20"], "Page Size: 4096B"),
            ("0020:", ["00", "00", "00", "05", "00", "00", "00", "02"], "Pages: 5 | Ver: 2"),
        ]

        rows_vgroup = VGroup()
        cell_lookup = {}
        for r_idx, (offset_str, hex_list, ascii_str) in enumerate(sample_rows):
            off_t = Text(offset_str, font_size=18, weight=BOLD, color=COLOR_MAP["amber"])
            cells = VGroup()
            for c_idx, hx in enumerate(hex_list):
                box = RoundedRectangle(width=0.58, height=0.48, corner_radius=0.06, fill_color="#0F172A", fill_opacity=0.9, stroke_color="#334155", stroke_width=1.2)
                txt = Text(hx, font_size=16, color=TEXT_WHITE).move_to(box)
                c_grp = VGroup(box, txt)
                cells.add(c_grp)
                cell_lookup[(r_idx, c_idx)] = c_grp
            cells.arrange(RIGHT, buff=0.08)
            asc_t = Text(ascii_str, font_size=16, color=COLOR_MAP["green"])
            row_grp = VGroup(off_t, cells, asc_t).arrange(RIGHT, buff=0.35)
            rows_vgroup.add(row_grp)

        rows_vgroup.arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        fit_inside(rows_vgroup, grid_w - 0.5, grid_h - 0.5)
        rows_vgroup.move_to(board.get_center())

        self.play_with_sfx(FadeIn(board), FadeIn(rows_vgroup), sfx_name="whoosh_soft.wav", run_time=0.9)

        # Highlight Callout Cards below the Hex Table
        callouts = VGroup()
        for hl in v.get("highlights", [])[:3]:
            col = COLOR_MAP.get(hl.get("color_theme", "cyan"), COLOR_MAP["cyan"])
            c_inner = VGroup(
                Text(hl["label"], font_size=17, weight=BOLD, color=col),
                Text(hl["value_desc"], font_size=14, color=TEXT_WHITE),
            ).arrange(DOWN, buff=0.08)
            c_card = pack_glass_card(3.5 if not self.is_portrait else 7.6, 1.25, c_inner, color=col, glow=True)
            callouts.add(c_card)

        if callouts:
            if self.is_portrait:
                callouts.arrange(DOWN, buff=0.22).move_to(DOWN * 3.8)
            else:
                callouts.arrange(RIGHT, buff=0.35).move_to(DOWN * 2.35)
            self.play_with_sfx(LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in callouts], lag_ratio=0.18), sfx_name="card_pop.wav", run_time=1.1)

        self.wait(1.8)

    # -----------------------------------------------------------------
    # COMPONENT 7: B-TREE CAMERA ZOOM (Like 04:40 - 05:12 in SQLite)
    # -----------------------------------------------------------------
    def render_btree_camera_zoom(self, v: dict):
        q_banner = Text(v.get("query_text", "SELECT * FROM users WHERE id = 42"), font_size=24, weight=BOLD, color=COLOR_MAP["green"])
        fit_inside(q_banner, self.stage_w, 0.7).move_to(UP * self.header_y)

        root_box = pack_glass_card(
            3.6, 1.15,
            VGroup(Text("Page 1 (Root)", font_size=18, weight=BOLD, color=COLOR_MAP["cyan"]), Text("10  |  50  |  90", font_size=15, color=TEXT_WHITE)).arrange(DOWN, buff=0.08),
            color=COLOR_MAP["cyan"], glow=True
        ).move_to(UP * 1.45)

        mid_left = pack_glass_card(2.8, 1.05, VGroup(Text("Page 20", font_size=16, color=TEXT_DIM), Text("10 | 30 | 40", font_size=14, color=TEXT_DIM)).arrange(DOWN, buff=0.06), color="#334155", glow=False).move_to(LEFT * 3.3 + DOWN * 0.35)
        mid_target = pack_glass_card(2.9, 1.05, VGroup(Text("Page 30 (Internal)", font_size=16, weight=BOLD, color=TEXT_WHITE), Text("60 | 70 | 80", font_size=14, color=COLOR_MAP["cyan"])).arrange(DOWN, buff=0.06), color=COLOR_MAP["cyan"], glow=True).move_to(ORIGIN + DOWN * 0.35)
        mid_right = pack_glass_card(2.8, 1.05, VGroup(Text("Page 70", font_size=16, color=TEXT_DIM), Text("90 | 100 | 110", font_size=14, color=TEXT_DIM)).arrange(DOWN, buff=0.06), color="#334155", glow=False).move_to(RIGHT * 3.3 + DOWN * 0.35)

        leaf_target = pack_glass_card(
            3.2, 1.2,
            VGroup(Text("Leaf Page 42", font_size=17, weight=BOLD, color=COLOR_MAP["green"]), Text("Row Match Found (O(log N))", font_size=13, color=TEXT_WHITE)).arrange(DOWN, buff=0.08),
            color=COLOR_MAP["green"], glow=True
        ).move_to(DOWN * 2.25)

        a_root_mid = Arrow(root_box.get_bottom(), mid_target.get_top(), buff=0.1, color=COLOR_MAP["cyan"], stroke_width=4)
        a_mid_leaf = Arrow(mid_target.get_bottom(), leaf_target.get_top(), buff=0.1, color=COLOR)


# -----------------------------------------------------------------
    # COMPONENT 8: FEATURE CAROUSEL CARDS (Like 06:56 4 ACID Cards)
    # -----------------------------------------------------------------
    def render_feature_carousel(self, v: dict):
        header = self.make_header(v.get("heading", ""), v.get("subheading", ""))
        self.play(FadeIn(header), run_time=0.5)

        cards_spec = v.get("cards", [])
        cards_vgroup = VGroup()

        for c_spec in cards_spec:
            col = COLOR_MAP.get(c_spec.get("color_theme", "cyan"), COLOR_MAP["cyan"])
            ic = get_icon(c_spec.get("icon", "shield"), height=0.7, color=col)
            t1 = Text(c_spec["title"], font_size=22, weight=BOLD, color=TEXT_WHITE)
            t2 = Text(c_spec["subtitle"], font_size=15, color=TEXT_DIM)
            inner = VGroup(ic, t1, t2).arrange(DOWN if not self.is_portrait else RIGHT, buff=0.22)
            card = pack_glass_card(
                2.85 if not self.is_portrait else 7.6,
                3.6 if not self.is_portrait else 1.85,
                inner,
                color=col,
                glow=True
            )
            cards_vgroup.add(card)

        if self.is_portrait:
            cards_vgroup.arrange(DOWN, buff=0.3).move_to(DOWN * 0.5)
        else:
            cards_vgroup.arrange(RIGHT, buff=0.32).move_to(DOWN * 0.4)

        self.play(FadeIn(cards_vgroup), run_time=0.7)

        for idx, active_card in enumerate(cards_vgroup):
            anims = [active_card.animate.scale(1.08)]
            for j, other_card in enumerate(cards_vgroup):
                if j != idx:
                    anims.append(other_card.animate.set_opacity(0.45))
            self.play_with_sfx(*anims, sfx_name="card_pop.wav", run_time=0.55)
            self.wait(0.35)
            self.play(active_card.animate.scale(1 / 1.08), *[c.animate.set_opacity(1.0) for c in cards_vgroup], run_time=0.35)

        self.wait(1.4)        
