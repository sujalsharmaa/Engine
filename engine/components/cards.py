"""Card-based components: tilted comparison cards and feature carousel."""

import math
from typing import List, Literal

from manim import *  # noqa: F401,F403

from engine.components._common import dim_cover
from engine.registry import Component, Cue, VisualSpec, register
from engine.theme import ThemeColor


class TiltedCardItem(Cue):
    title: str
    value: str
    subtext: str = ""
    icon: str = "database"
    color_theme: ThemeColor = "cyan"
    is_hero: bool = False


@register
class TiltedCardComparison(Component):
    name = "TiltedCardComparison"
    description = "2-4 glowing 2.5D cards with big values side by side; one can be the 'hero'. Tilted on 16:9, stacked on phones."
    best_for = "A vs B, before/after, old vs new, tier comparison, key numbers"

    class Spec(VisualSpec):
        component_type: Literal["TiltedCardComparison"] = "TiltedCardComparison"
        cards: List[TiltedCardItem]

    example = {"component_type": "TiltedCardComparison", "heading": "Push vs. Pull", "subheading": "Two telemetry models",
               "cards": [{"title": "Legacy Push", "value": "Flood", "subtext": "Spikes overwhelm the server", "icon": "alert", "color_theme": "red", "trigger_keyword": "push"},
                         {"title": "Prometheus", "value": "Pull", "subtext": "Scrapes /metrics on its own schedule", "icon": "prometheus", "color_theme": "cyan", "is_hero": True, "trigger_keyword": "pull"}]}
    example_narration = "Push monitoring floods the server, while Prometheus pulls metrics on its own schedule."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        n = len(v.cards)
        gap = 0.4
        built = []
        for i, ci in enumerate(v.cards):
            col = c.color(ci.color_theme)
            hero = ci.is_hero
            if c.portrait:
                cw = body.w
                ch = min(3.6 if hero else 3.1, (body.h - gap * (n - 1)) / n)
            else:
                cw = min(4.2, (body.w - gap * (n - 1)) / n) * (1.06 if hero else 1.0)
                ch = min(5.0 if hero else 4.4, body.h)
            ic = c.icon(ci.icon, 0.7, col, brand=False)
            title = c.wrap(ci.title, 26 if hero else 22, cw - 0.6, align=ORIGIN, bold=True)
            val = c.T(ci.value, 64 if hero else 50, bold=True, color=col if hero else c.theme.text)
            parts = [ic, title, val]
            if ci.subtext:
                parts.append(c.wrap(ci.subtext, 16, cw - 0.7, align=ORIGIN, color=c.theme.dim))
            tilt = 0.0
            if not c.portrait and n > 1:
                tilt = (12 if i == 0 else (-12 if i == n - 1 else 6)) * DEGREES
            card = c.pack(cw, ch, VGroup(*parts).arrange(DOWN, buff=0.18), col, pad=0.2, tilt_y=tilt)
            built.append(card)
        grp = VGroup(*built).arrange(DOWN if c.portrait else RIGHT, buff=gap).move_to(body.center)
        times = c.cue_times([ci.exact_time for ci in v.cards], start_offset=0.7)
        for card, ci, t in zip(built, v.cards, times):
            c.at(t, FadeIn(card, shift=UP * 0.4, scale=0.9), sfx="card_pop.wav", rt=0.7)
            if ci.is_hero:
                c.play(card.animate.scale(1.04), rt=0.3)
        c.hold()


class CarouselCardItem(Cue):
    title: str
    subtitle: str = ""
    icon: str = "zap"
    color_theme: ThemeColor = "cyan"


@register
class FeatureCarouselCards(Component):
    name = "FeatureCarouselCards"
    description = "A set of 3-6 feature/concept cards; the one being discussed lights up while the others dim."
    best_for = "feature lists, pillars (e.g. ACID), principles, tools in a stack, categories"

    class Spec(VisualSpec):
        component_type: Literal["FeatureCarouselCards"] = "FeatureCarouselCards"
        cards: List[CarouselCardItem]

    example = {"component_type": "FeatureCarouselCards", "heading": "ACID Guarantees", "subheading": "What every transaction promises",
               "cards": [{"title": "Atomicity", "subtitle": "All or nothing", "icon": "atom", "color_theme": "cyan", "trigger_keyword": "atomicity"},
                         {"title": "Consistency", "subtitle": "Valid state only", "icon": "shield", "color_theme": "green", "trigger_keyword": "consistency"},
                         {"title": "Isolation", "subtitle": "No interference", "icon": "lock", "color_theme": "purple", "trigger_keyword": "isolation"},
                         {"title": "Durability", "subtitle": "Survives crashes", "icon": "database", "color_theme": "amber", "trigger_keyword": "durability"}]}
    example_narration = "Atomicity means all or nothing. Consistency keeps data valid. Isolation prevents interference. Durability survives crashes."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        n = len(v.cards)
        gap = 0.32
        if c.portrait:
            cols = 1 if n <= 4 else 2
        else:
            cols = n if n <= 4 else math.ceil(n / 2)
        rows = math.ceil(n / cols)
        cw = (body.w - gap * (cols - 1)) / cols
        ch = min(4.2 if not c.portrait else 2.6, (body.h - gap * (rows - 1)) / rows)
        horizontal = c.portrait and cols == 1
        cards = VGroup()
        for ci in v.cards:
            col = c.color(ci.color_theme)
            ic = c.icon(ci.icon, 0.8 if not horizontal else 0.9, col)
            t1 = c.wrap(ci.title, 24, cw - (1.8 if horizontal else 0.4), align=LEFT if horizontal else ORIGIN, bold=True)
            parts = [t1]
            if ci.subtitle:
                parts.append(c.wrap(ci.subtitle, 16, cw - (1.8 if horizontal else 0.4), align=LEFT if horizontal else ORIGIN, color=c.theme.dim))
            txt = VGroup(*parts).arrange(DOWN, aligned_edge=LEFT if horizontal else ORIGIN, buff=0.1)
            inner = VGroup(ic, txt).arrange(RIGHT if horizontal else DOWN, buff=0.4 if horizontal else 0.22)
            cards.add(c.pack(cw, ch, inner, col, pad=0.2))
        cards.arrange_in_grid(rows=rows, cols=cols, buff=gap)
        cards.move_to(body.center)
        c.play(LaggedStart(*[FadeIn(k, shift=UP * 0.25, scale=0.92) for k in cards], lag_ratio=0.15), sfx="whoosh_soft.wav", rt=0.9)

        times = c.cue_times([ci.exact_time for ci in v.cards], start_offset=1.4, end_pad=1.0)
        covers = [dim_cover(c, k, 0.0) for k in cards]
        for cv in covers:
            c.scene.add(cv)
        for idx, t in zip(range(n), times):
            anims = [cards[idx].animate.scale(1.05), covers[idx].animate.scale(1.05).set_fill(c.theme.bg, opacity=0.0)]
            anims += [covers[j].animate.set_fill(c.theme.bg, opacity=0.6) for j in range(n) if j != idx]
            c.at(t, *anims, sfx="card_pop.wav", rt=0.45)
            if idx + 1 < n:
                c.play(cards[idx].animate.scale(1 / 1.05), covers[idx].animate.scale(1 / 1.05), rt=0.2)
        c.play(cards[n - 1].animate.scale(1 / 1.05), covers[n - 1].animate.scale(1 / 1.05),
               *[cv.animate.set_fill(c.theme.bg, opacity=0.0) for cv in covers], rt=0.4)
        c.hold()
