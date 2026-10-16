"""Helpers shared by components (module name starts with _ so it registers nothing)."""

from manim import *  # noqa: F401,F403


def left_pack(ctx, w, h, content, color, fill=None, pad_x=0.4, glow=True):
    """Glass card with content left-aligned and vertically centred (list rows, code panels...)."""
    card = ctx.card(w, h, color, fill=fill, glow=glow)
    ctx.fit(content, w - pad_x, h, pad=0.12)
    content.move_to(card.get_center())
    content.align_to(card, LEFT).shift(RIGHT * pad_x)
    return VGroup(card, content)


def number_badge(ctx, n, color, r=0.3):
    circ = Circle(radius=r, fill_color=color, fill_opacity=0.22, stroke_color=color, stroke_width=2.5)
    t = ctx.T(str(n), 22, bold=True, color=color).move_to(circ)
    return VGroup(circ, t)


def stack_center(mobs, buff=0.3, center=ORIGIN):
    return VGroup(*mobs).arrange(DOWN, buff=buff).move_to(center)


def dim_cover(ctx, mob, opacity=0.55, corner=0.2):
    """Translucent overlay in the background colour: dims a card WITHOUT touching its own opacities
    (set_opacity() on a glass card flattens its glow rings / fill to 100%)."""
    cover = RoundedRectangle(width=mob.width + 0.02, height=mob.height + 0.02, corner_radius=corner,
                             fill_color=ctx.theme.bg, fill_opacity=opacity, stroke_width=0)
    cover.move_to(mob.get_center())
    return cover
