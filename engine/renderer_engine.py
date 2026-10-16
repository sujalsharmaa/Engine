"""
engine/renderer_engine.py
-------------------------------------------------------------------------
Manim scene that plays a compiled storyboard. All visuals live in
engine/components/*; this file only does stage management:

  * persistent background (plain / grid / spotlight),
  * scene scheduling locked to the voiceover timeline,
  * scene exit transitions,
  * SFX cue logging.

Camera push-ins/drifts and the progress bar are applied in post
(engine/post_processor.py) so Manim can keep its fast static-frame path.
"""

import json
import os
from pathlib import Path

from manim import *  # noqa: F401,F403

from engine.context import GEOMETRY, Ctx
from engine.registry import REGISTRY, load_components
from engine.theme import get_theme
from engine.ui import spotlight


class InstrumentedScene(MovingCameraScene):
    def setup(self):
        super().setup()
        self.sfx_cue_sheet = []
        self.drift_report = []

    def play_with_sfx(self, *animations, sfx_name: str = None, volume_db: float = -10.0, **kwargs):
        if sfx_name:
            self.sfx_cue_sheet.append({
                "time_sec": round(float(self.renderer.time), 3),
                "sfx": sfx_name,
                "volume_db": volume_db,
            })
        self.play(*animations, **kwargs)


class StoryboardRenderer(InstrumentedScene):
    def construct(self):
        load_components()
        sb_path = Path(os.environ.get("STUDIO_STORYBOARD", "compiled_storyboard.json"))
        if not sb_path.exists():
            raise FileNotFoundError(f"{sb_path} missing. Compile the storyboard first (run_studio.py does this).")
        self.out_dir = Path(os.environ.get("STUDIO_BUILD_DIR", "."))
        sb = json.loads(sb_path.read_text(encoding="utf-8"))
        self.sb = sb
        self.theme = get_theme(sb.get("studio_theme", "cyber_cyan"))
        geo = GEOMETRY[sb.get("aspect_ratio", "16:9")]
        self.W, self.H = geo["W"], geo["H"]
        self.base_height = self.H

        self.camera.frame.set(height=self.H).move_to(ORIGIN)
        self._build_persistent_layers(sb.get("background", "grid"))

        for scene_data in sb["scenes"]:
            self.run_scene(scene_data)

        end = float(sb["duration"])
        if end - self.renderer.time > 0.05:
            self.wait(end - self.renderer.time)

        (self.out_dir / "sfx_cues.json").write_text(json.dumps(self.sfx_cue_sheet, indent=2), encoding="utf-8")
        (self.out_dir / "render_report.json").write_text(json.dumps(self.drift_report, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    def _build_persistent_layers(self, bg_mode: str):
        th = self.theme
        layers = []
        bg = Rectangle(width=self.W * 1.7, height=self.H * 1.7, fill_color=th.bg, fill_opacity=1, stroke_width=0)
        bg.set_z_index(-100)
        layers.append(bg)
        if bg_mode == "grid":
            grid = VGroup()
            step = 1.0
            nx, ny = int(self.W / step) + 2, int(self.H / step) + 2
            for i in range(-nx // 2, nx // 2 + 1):
                grid.add(Line(UP * self.H, DOWN * self.H, stroke_width=0.8, stroke_color=th.grid, stroke_opacity=0.55).shift(RIGHT * i * step))
            for j in range(-ny // 2, ny // 2 + 1):
                grid.add(Line(LEFT * self.W, RIGHT * self.W, stroke_width=0.8, stroke_color=th.grid, stroke_opacity=0.55).shift(UP * j * step))
            grid.set_z_index(-90)
            layers.append(grid)
        if bg_mode in ("grid", "spotlight_only"):
            r = 6.2 if self.W > self.H else 5.2
            spot = spotlight(th.accent, radius=r, max_opacity=th.spot_opacity)
            spot.set_z_index(-80)
            layers.append(spot)
        for m in layers:
            self.add(m)
        self._persistent_ids = {id(m) for m in layers}

    def clear_stage(self):
        to_remove = [m for m in self.mobjects if id(m) not in self._persistent_ids]
        for m in to_remove:
            self.remove(m)

    # ------------------------------------------------------------------
    def run_scene(self, sc: dict):
        spec_dict = sc["visual"]
        comp_cls = REGISTRY.get(spec_dict["component_type"])
        if comp_cls is None:
            raise ValueError(f"Unknown component {spec_dict['component_type']}")
        spec = comp_cls.Spec.model_validate(spec_dict)
        self.camera.frame.set(height=self.base_height).move_to(ORIGIN)
        ctx = Ctx(self, self.sb, sc, self.theme)

        # lock to the voiceover timeline
        lag = self.renderer.time - ctx.t0
        if lag > 0.15:
            self.drift_report.append({"scene": sc["scene_id"], "late_by_sec": round(lag, 3),
                                      "hint": "previous scene's animations ran longer than its narration; shorten its text or items"})
        ctx.wait_until(ctx.t0)

        comp_cls(ctx, spec).render()
        ctx.hold()
        self.exit_transition(ctx, sc.get("transition", "fade"))

    def exit_transition(self, ctx: Ctx, kind: str):
        mobs = [m for m in self.mobjects if id(m) not in self._persistent_ids]
        if not mobs or kind == "cut":
            self.clear_stage()
            return
        rt = max(0.1, ctx.exit_time)
        if kind == "slide":
            anims = [FadeOut(m, shift=LEFT * 2.2) for m in mobs]
        elif kind == "zoom":
            anims = [FadeOut(m, scale=1.25) for m in mobs]
        elif kind == "wipe":
            anims = [LaggedStart(*[FadeOut(m, shift=RIGHT * 1.4) for m in mobs], lag_ratio=0.12)]
        else:
            anims = [FadeOut(m, shift=DOWN * 0.2) for m in mobs]
        self.play(*anims, run_time=rt)
        self.clear_stage()
