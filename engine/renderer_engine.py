"""
Step 3: The Proprietary Component & Rendering Engine
-------------------------------------------------------------------------
Reads 'compiled_storyboard.json', builds glassmorphic 3D-tilted cards 
programmatically, handles automated sound effect cue logging, and renders 
the master video using Manim.
"""

import json
from pathlib import Path
from manim import *

# --- Studio Styling Constants ---
BG_COLOR = "#05070D"
CARD_FILL = "#0D1322"
NEON_CYAN = "#00E5FF"
NEON_BLUE = "#2979FF"
NEON_GREEN = "#00E676"
TEXT_WHITE = "#F8FAFC"
TEXT_DIM = "#64748B"

config.background_color = BG_COLOR

class InstrumentedScene(MovingCameraScene):
    """Scene class that automatically tracks timing and logs sound effect cues."""
    def setup(self):
        super().setup()
        self.sfx_cue_sheet = []

    def play_with_sfx(self, *animations, sfx_name: str = None, volume_db: float = -10.0, **kwargs):
        if sfx_name:
            self.sfx_cue_sheet.append({
                "time_sec": round(self.renderer.time, 3),
                "sfx": sfx_name,
                "volume_db": volume_db
            })
        self.play(*animations, **kwargs)

    def export_sfx_cues(self, filepath="sfx_cues.json"):
        Path(filepath).write_text(json.dumps(self.sfx_cue_sheet, indent=2), encoding="utf-8")


def create_glass_card(width, height, color=NEON_CYAN, tilt_y=0.0) -> VGroup:
    """Generates a frosted-glass card with multi-layered neon glow and 2.5D tilt."""
    card_group = VGroup()
    for sw, op in [(14, 0.05), (7, 0.12), (3, 0.25)]:
        glow = RoundedRectangle(
            width=width, height=height, corner_radius=0.2,
            fill_opacity=0, stroke_color=color, stroke_width=sw, stroke_opacity=op
        )
        card_group.add(glow)

    body = RoundedRectangle(
        width=width, height=height, corner_radius=0.2,
        fill_color=CARD_FILL, fill_opacity=0.92, stroke_color=color, stroke_width=2.0
    )
    card_group.add(body)
    
    if tilt_y != 0:
        card_group.rotate(tilt_y, axis=UP)
    return card_group


class StoryboardRenderer(InstrumentedScene):
    def construct(self):
        storyboard_path = Path("compiled_storyboard.json")
        if not storyboard_path.exists():
            raise FileNotFoundError("compiled_storyboard.json missing. Run Step 2 first!")

        storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
        
        for scene_data in storyboard.get("scenes", []):
            self.render_scene_block(scene_data)

        # Export tracked SFX cues for Step 4's audio mixer
        self.export_sfx_cues()

    def render_scene_block(self, scene: dict):
        visual = scene.get("visual", {})
        comp_type = visual.get("component_type")

        if comp_type == "TiltedCardComparison":
            self.render_tilted_cards(visual)
        else:
            # Fallback placeholder for other component types
            dummy_text = Text(f"Rendering: {visual.get('heading', 'Scene')}", font_size=32, color=TEXT_WHITE)
            self.play_with_sfx(FadeIn(dummy_text), sfx_name="pop.wav")
            self.wait(1.5)
            self.play(FadeOut(dummy_text))

    def render_tilted_cards(self, visual: dict):
        heading = Text(visual.get("heading", ""), font_size=36, weight=BOLD, color=TEXT_WHITE).to_edge(UP, buff=0.8)
        subheading = Text(visual.get("subheading", ""), font_size=18, color=TEXT_DIM).next_to(heading, DOWN, buff=0.15)
        
        self.play_with_sfx(FadeIn(heading, shift=DOWN * 0.2), FadeIn(subheading), sfx_name="whoosh_soft.wav")

        cards_data = visual.get("cards", [])
        rendered_cards = []
        
        # Position cards dynamically based on quantity
        x_offsets = [-3.8, 0.0, 3.8] if len(cards_data) == 3 else [-2.2, 2.2]

        for i, card_info in enumerate(cards_data):
            theme_color = NEON_GREEN if card_info.get("is_hero") else (NEON_BLUE if i % 2 == 1 else NEON_CYAN)
            tilt_angle = 12 if i == 0 else (-12 if i == len(cards_data) - 1 else 0)

            box = create_glass_card(3.3, 4.2, color=theme_color, tilt_y=tilt_angle * DEGREES)
            t_text = Text(card_info["title"], font_size=24, weight=BOLD, color=TEXT_WHITE).shift(UP * 1.2)
            v_text = Text(card_info["value"], font_size=64, weight=BOLD, color=TEXT_WHITE)
            
            content = VGroup(t_text, v_text).move_to(box)
            if card_info.get("subtext"):
                sub_t = Text(card_info["subtext"], font_size=14, color=TEXT_DIM).shift(DOWN * 1.5)
                content.add(sub_t)

            card_node = VGroup(box, content).move_to(RIGHT * x_offsets[i] + DOWN * 0.5)
            rendered_cards.append(card_node)

        # Staggered appearance triggered around audio timing
        for idx, card_obj in enumerate(rendered_cards):
            self.play_with_sfx(
                FadeIn(card_obj, shift=UP * 0.4, scale=0.92),
                sfx_name="card_pop.wav",
                run_time=0.8
            )
            self.wait(0.4)

        self.wait(2.0)
        self.play(*(FadeOut(c) for c in rendered_cards), FadeOut(heading), FadeOut(subheading))


if __name__ == "__main__":
    # Command to run this engine:
    # manim -pqh engine/renderer_engine.py StoryboardRenderer
    pass