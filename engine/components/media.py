"""Media components: images / screenshots with frames and Ken-Burns motion."""

import os
from pathlib import Path
from typing import List, Literal

from manim import *  # noqa: F401,F403
from pydantic import Field, model_validator

from engine.registry import Component, Cue, VisualSpec, register
from engine.theme import ThemeColor


class ImageItem(Cue):
    path: str
    caption: str = ""

    @model_validator(mode="before")
    @classmethod
    def _from_str(cls, data):
        return {"path": data} if isinstance(data, str) else data


def resolve_asset(path: str):
    p = Path(path)
    cands = [p]
    for base in (os.environ.get("STUDIO_SCRIPT_DIR"), "assets/images", "assets", "."):
        if base:
            cands.append(Path(base) / path)
    for cand in cands:
        if cand.exists():
            return cand
    return None


@register
class ImageShowcase(Component):
    name = "ImageShowcase"
    description = "One or more local images/screenshots in a browser, phone, polaroid or plain frame with slow zoom; multiple images cross-fade as spoken."
    best_for = "screenshots, product shots, photos, diagrams exported as PNG, logos, thumbnails"

    class Spec(VisualSpec):
        component_type: Literal["ImageShowcase"] = "ImageShowcase"
        images: List[ImageItem]
        style: Literal["plain", "browser", "phone", "polaroid"] = "browser"
        zoom: bool = True
        theme_color: ThemeColor = "accent"

    example = {"component_type": "ImageShowcase", "heading": "The dashboard", "style": "browser",
               "images": [{"path": "demo.png", "caption": "Weekly active users"}]}
    example_narration = "Here is what the dashboard looks like once everything is wired up."

    def _image(self, item, max_w, max_h):
        c = self.ctx
        p = resolve_asset(item.path)
        if p is None or p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"):
            grp = VGroup(c.icon("image", 1.0, c.theme.dim), c.wrap(f"image: {item.path}", 16, max_w - 1, align=ORIGIN, color=c.theme.dim)).arrange(DOWN, buff=0.2)
            box = RoundedRectangle(width=max_w, height=max_h, corner_radius=0.15, stroke_color=c.theme.dim, stroke_width=2, fill_color=c.theme.card, fill_opacity=1)
            grp.move_to(box)
            print(f"[!] ImageShowcase: could not load image '{item.path}' (put PNG/JPG in assets/images or next to the script)")
            return VGroup(box, grp)
        img = ImageMobject(str(p))
        img.scale_to_fit_width(max_w)
        if img.height > max_h:
            img.scale_to_fit_height(max_h)
        return img

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        col = c.color(v.theme_color)
        has_cap = any(i.caption for i in v.images)
        cap_h = 1.1 if has_cap else 0
        area_h = body.h - cap_h
        pad = 0.25
        top_bar = 0.55 if v.style == "browser" else 0
        iw = min(body.w - 2 * pad, area_h * (0.55 if v.style == "phone" else 5)) if v.style != "phone" else min(body.w * 0.55, area_h * 0.5)
        ih = area_h - 2 * pad - top_bar - (0.5 if v.style == "polaroid" else 0)
        if v.style == "phone":
            iw = min(body.w * 0.5, ih * 0.5)
        times = c.cue_times([i.exact_time for i in v.images], start_offset=0.5, end_pad=1.0)
        if len(v.images) > 1:
            times[0] = c.t0 + 0.4
        prev = None
        cy = body.top - area_h / 2
        for i, (item, t) in enumerate(zip(v.images, times)):
            img = self._image(item, iw, ih)
            frame = VGroup()
            if v.style == "browser":
                w, h = img.width + 2 * pad * 0.5, img.height + top_bar + pad
                box = c.card(w, h, col)
                dots = VGroup(*[Dot(radius=0.07, color=k) for k in ("#FF5F56", "#FFBD2E", "#27C93F")]).arrange(RIGHT, buff=0.12)
                dots.move_to(box.get_corner(UL) + RIGHT * 0.5 + DOWN * 0.3)
                img.move_to(box.get_center() + DOWN * (top_bar / 2 - pad / 4))
                frame = VGroup(box, dots)
            elif v.style == "phone":
                w, h = img.width + 0.4, img.height + 0.5
                frame = VGroup(RoundedRectangle(width=w, height=h, corner_radius=0.45, stroke_color=col, stroke_width=5, fill_color="#000000", fill_opacity=1))
                img.move_to(frame.get_center())
            elif v.style == "polaroid":
                w, h = img.width + 0.5, img.height + 1.1
                frame = VGroup(RoundedRectangle(width=w, height=h, corner_radius=0.05, stroke_width=0, fill_color="#F8FAFC", fill_opacity=1))
                img.move_to(frame.get_center() + UP * 0.25)
            elif v.style == "plain":
                frame = VGroup(SurroundingRectangle(img, color=col, buff=0.08, stroke_width=3, corner_radius=0.1))
            group = Group(frame, img)
            group.move_to([0, cy, 0])
            cap = c.wrap(item.caption, 22, body.w - 0.6, align=ORIGIN, bold=True) if item.caption else None
            if cap:
                cap.move_to([0, body.bottom + cap_h / 2, 0])
            anims_in = [FadeIn(group, scale=0.94)] + ([FadeIn(cap, shift=UP * 0.15)] if cap else [])
            outs = [FadeOut(prev)] if prev else []
            c.at(t, *anims_in, *outs, sfx="whoosh_soft.wav", rt=0.6)
            prev = Group(group, cap) if cap else group
            if v.zoom:
                nxt = times[i + 1] if i + 1 < len(times) else c.end
                room = nxt - c.now - 0.5
                if room > 0.6:
                    c.play(group.animate.scale(1.05), rt=room, rate_func=linear)
        c.hold()
