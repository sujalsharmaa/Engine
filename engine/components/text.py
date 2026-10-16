"""Text-driven components: titles, quotes, lists, kinetic captions, pros/cons, CTA."""

import re
from typing import List, Literal, Optional

from manim import *  # noqa: F401,F403
from pydantic import Field

from engine.components._common import dim_cover, left_pack, number_badge
from engine.registry import Component, Cue, TextItem, VisualSpec, register
from engine.theme import ThemeColor
from engine.timing import _tok


# ======================================================================
@register
class TitleCard(Component):
    name = "TitleCard"
    description = "Big animated title with optional eyebrow, subtitle and badge. Intros, chapter breaks, outros."
    best_for = "video intro, chapter title, section divider, closing statement"

    class Spec(VisualSpec):
        component_type: Literal["TitleCard"] = "TitleCard"
        eyebrow: str = ""
        title: str
        subtitle: str = ""
        badge: str = ""
        theme_color: ThemeColor = "accent"
        align: Literal["center", "left"] = "center"

    example = {"component_type": "TitleCard", "eyebrow": "DEEP DIVE", "title": "How Kafka Actually Works",
               "subtitle": "Logs, partitions and consumer groups in 60 seconds", "badge": "2025"}
    example_narration = "Kafka looks complicated, but it is really just a distributed commit log."

    def render(self):
        c, v = self.ctx, self.v
        col = c.color(v.theme_color)
        region = c.full
        al = LEFT if v.align == "left" else ORIGIN
        parts = []
        if v.eyebrow:
            eb = c.T(v.eyebrow.upper(), 20, color=col, bold=True)
            line = Line(LEFT * 0.5, RIGHT * 0.5, stroke_width=4, color=col)
            parts.append(VGroup(line, eb).arrange(RIGHT, buff=0.25))
        title = c.wrap(v.title, 56, region.w, align=LEFT if v.align == "left" else ORIGIN, bold=True)
        parts.append(title)
        if v.subtitle:
            parts.append(c.wrap(v.subtitle, 24, region.w * 0.9, align=LEFT if v.align == "left" else ORIGIN, color=c.theme.dim))
        if v.badge:
            b = c.T(v.badge, 20, color=col, bold=True)
            pill = RoundedRectangle(width=b.width + 0.7, height=b.height + 0.4, corner_radius=0.3, stroke_color=col,
                                    stroke_width=2.5, fill_color=col, fill_opacity=0.15)
            parts.append(VGroup(pill, b.move_to(pill)))
        stack = VGroup(*parts).arrange(DOWN, buff=0.45, aligned_edge=LEFT if v.align == "left" else ORIGIN)
        c.fit(stack, region.w, region.h, pad=0.05)
        stack.move_to(region.center)
        if v.align == "left":
            stack.align_to(region.left * RIGHT, LEFT)
        underline = Line(LEFT, RIGHT, stroke_width=6, color=col).set(width=min(3.0, title.width * 0.5))
        underline.next_to(title, DOWN, buff=0.22, aligned_edge=LEFT if v.align == "left" else ORIGIN)

        times = c.cue_times([None] * len(parts), start_offset=0.15, end_pad=max(1.0, c.dur * 0.5))
        for part, t in zip(parts, times):
            sfx = "whoosh_soft.wav" if part is title else None
            c.at(t, FadeIn(part, shift=UP * 0.3), sfx=sfx, rt=0.7)
            if part is title:
                c.play(Create(underline), rt=0.4)
        c.hold()


# ======================================================================
@register
class HeroQuoteHook(Component):
    name = "HeroQuoteHook"
    description = "Speaker avatar badge + highlighted quote. Strong cold-open hooks and testimonials."
    best_for = "opening hook, expert quote, testimonial, famous line"

    class Spec(VisualSpec):
        component_type: Literal["HeroQuoteHook"] = "HeroQuoteHook"
        speaker_name: str
        speaker_role: str = ""
        quote_text: str
        highlight_phrase: str = ""
        year_badge: Optional[str] = None
        theme_color: ThemeColor = "purple"

    example = {"component_type": "HeroQuoteHook", "speaker_name": "Linus Torvalds", "speaker_role": "Creator of Linux",
               "quote_text": "Talk is cheap. Show me the code.", "highlight_phrase": "Show me the code", "year_badge": "2000"}
    example_narration = "Talk is cheap. Show me the code. Those words changed how engineers argue."

    def render(self):
        c, v = self.ctx, self.v
        col = c.color(v.theme_color)
        region = c.full
        th = c.theme

        aura = Circle(radius=1.45, fill_color=col, fill_opacity=0.25, stroke_color=col, stroke_width=3)
        inner = Circle(radius=1.15, fill_color=th.card_alt, fill_opacity=0.95, stroke_color=th.text, stroke_width=1.5)
        initials = "".join(p[0] for p in v.speaker_name.split()[:2]).upper() or "?"
        mono = c.T(initials, 46, bold=True).move_to(inner)
        avatar = VGroup(VGroup(aura, inner, mono), c.T(v.speaker_name, 22, bold=True))
        if v.speaker_role:
            avatar.add(c.T(v.speaker_role, 15, color=col))
        avatar.arrange(DOWN, buff=0.16)

        qmax = region.w if c.portrait else region.w - 4.6
        t2c = {}
        if v.highlight_phrase:
            t2c = {v.highlight_phrase: col}
        lines = c.wrap(f"“{v.quote_text}”", 34, qmax, bold=True, t2c=t2c) if t2c else c.wrap(f"“{v.quote_text}”", 34, qmax, bold=True)
        quote = VGroup(lines)
        if v.year_badge:
            quote = VGroup(c.T(str(v.year_badge), 52, bold=True, color=col), lines).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        layout = VGroup(avatar, quote).arrange(DOWN if c.portrait else RIGHT, buff=0.8 if c.portrait else 1.1)
        c.fit(layout, region.w, region.h, pad=0.05)
        layout.move_to(region.center)

        t_q = c.cue_times([v.exact_time], start_offset=0.9, end_pad=max(1.0, c.dur * 0.5))[0]
        c.play(FadeIn(avatar, scale=0.9), sfx="whoosh_soft.wav", rt=0.8)
        c.at(t_q, Write(lines, run_time=1.1), sfx="card_pop.wav", rt=1.1)
        if v.year_badge:
            c.play(FadeIn(quote[0], shift=UP * 0.2), rt=0.5)
        c.hold()


# ======================================================================
class ListItem(Cue):
    text: str
    detail: str = ""
    icon: str = ""
    color_theme: ThemeColor = "accent"


@register
class KeyPointsList(Component):
    name = "KeyPointsList"
    description = "Items reveal one by one as they are spoken. Numbered, bullets, checklist or icon rows; supports Top-N countdowns."
    best_for = "listicles, summaries, takeaways, Top-N rankings, checklists, agendas"

    class Spec(VisualSpec):
        component_type: Literal["KeyPointsList"] = "KeyPointsList"
        items: List[ListItem]
        style: Literal["numbered", "bullets", "checklist", "icons"] = "numbered"
        countdown: bool = False   # reveal from N down to 1 (Top-N)

    example = {"component_type": "KeyPointsList", "heading": "3 Habits of Fast Learners", "style": "numbered",
               "items": [{"text": "Teach it back", "detail": "Explain it simply", "trigger_keyword": "teach"},
                         {"text": "Space your reviews", "detail": "Day 1, 3, 7, 21", "trigger_keyword": "space"},
                         {"text": "Sleep on it", "detail": "Memory consolidates overnight", "trigger_keyword": "sleep"}]}
    example_narration = "First, teach it back to someone. Second, space your reviews. Third, sleep on it."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        items = v.items
        n = len(items)
        gap = 0.2
        row_h = min(2.2 if c.portrait else 1.4, (body.h - gap * (n - 1)) / max(1, n))
        row_w = body.w
        rows = []
        for i, it in enumerate(items):
            col = c.color(it.color_theme)
            num = (n - i) if v.countdown else (i + 1)
            if v.style == "numbered":
                lead = number_badge(c, num, col)
            elif v.style == "checklist":
                lead = c.icon("circle-check", 0.6, col)
            elif v.style == "icons":
                lead = c.icon(it.icon or "sparkles", 0.6, col)
            else:
                lead = Dot(radius=0.12, color=col)
            txt = VGroup(c.wrap(it.text, 26, row_w - 2.2, bold=True))
            if it.detail:
                txt.add(c.wrap(it.detail, 16, row_w - 2.2, color=c.theme.dim))
            txt.arrange(DOWN, aligned_edge=LEFT, buff=0.08)
            content = VGroup(lead, txt).arrange(RIGHT, buff=0.35)
            rows.append(left_pack(c, row_w, row_h, content, col))
        stack = VGroup(*rows).arrange(DOWN, buff=gap)
        stack.move_to(body.center)

        order = list(range(n))[::-1] if v.countdown else list(range(n))
        exacts = [items[i].exact_time for i in order]
        times = c.cue_times(exacts, start_offset=0.6)
        covers = []
        for idx, t in zip(order, times):
            new_cover = dim_cover(c, rows[idx], 0.0)
            fades = []
            if covers:
                prev_cover = covers[-1]
                fades.append(prev_cover.animate.set_fill(c.theme.bg, opacity=0.5))
            covers.append(new_cover)
            c.at(t, FadeIn(rows[idx], shift=RIGHT * 0.5), *fades, sfx="card_pop.wav", rt=0.55)
            c.scene.add(new_cover)
        if covers:
            c.play(*[cv.animate.set_fill(c.theme.bg, opacity=0.0) for cv in covers], rt=0.4)
        c.hold()


# ======================================================================
@register
class KineticText(Component):
    name = "KineticText"
    description = "Big words pop onto the screen exactly as they are spoken (the narration itself), with emphasis words in colour."
    best_for = "Shorts/Reels hooks, punchy statements, motivational lines, storytelling beats, no-asset scenes"

    class Spec(VisualSpec):
        component_type: Literal["KineticText"] = "KineticText"
        text: str = ""                                  # empty = use this scene's narration
        emphasis_words: List[str] = Field(default_factory=list)
        theme_color: ThemeColor = "accent"
        size: int = 54

    example = {"component_type": "KineticText", "emphasis_words": ["never", "again"], "theme_color": "amber"}
    example_narration = "You will never ship slow code again once you learn this one trick."

    def render(self):
        c, v = self.ctx, self.v
        col = c.color(v.theme_color)
        region = c.full
        if v.text:
            raw = v.text.split()
            lo, hi = c.t0 + 0.4, max(c.t0 + 1.0, c.end - 0.8)
            times = [lo + (hi - lo) * i / max(1, len(raw)) for i in range(len(raw))]
        else:
            raw = [w["word"] for w in c.words]
            times = [w["start"] for w in c.words]
        if not raw:
            return
        emph = {t for e in v.emphasis_words for t in _tok(e)}
        size = v.size if len(raw) <= 14 else (v.size * 0.8 if len(raw) <= 28 else v.size * 0.62)

        mobs = []
        for w in raw:
            is_e = any(t in emph for t in _tok(w))
            m = c.T(w, size, bold=True, color=col if is_e else c.theme.text)
            mobs.append(m)
        space = c.fs(size) * 0.0055
        lines, cur, cur_w = [], [], 0.0
        for m in mobs:
            if cur and cur_w + m.width + space > region.w:
                lines.append(cur)
                cur, cur_w = [], 0.0
            cur.append(m)
            cur_w += m.width + space
        if cur:
            lines.append(cur)
        probe_y, probe_x = c.T("y", size, bold=True), c.T("x", size, bold=True)
        desc = probe_y.height - probe_x.height
        line_groups = []
        for l in lines:
            g = VGroup(*l).arrange(RIGHT, buff=space, aligned_edge=DOWN)
            for m, wtxt in zip(l, [raw[mobs.index(mm)] for mm in l]):
                if any(ch in "gjpqyQ" for ch in wtxt):
                    m.shift(DOWN * desc)
            line_groups.append(g)
        rows = VGroup(*line_groups).arrange(DOWN, buff=0.3)
        c.fit(rows, region.w, region.h, pad=0.05)
        rows.move_to(region.center)

        for m, t in zip(mobs, times):
            c.at(t - 0.05, FadeIn(m, shift=UP * 0.18, scale=0.85), rt=0.18)
        c.hold()


# ======================================================================
class ProsConsItem(TextItem):
    pass


@register
class ProsCons(Component):
    name = "ProsCons"
    description = "Two-column pros vs cons (or before vs after) with check / cross icons revealing as spoken."
    best_for = "reviews, trade-off discussions, decisions, myth vs fact"

    class Spec(VisualSpec):
        component_type: Literal["ProsCons"] = "ProsCons"
        pros_title: str = "Pros"
        cons_title: str = "Cons"
        pros: List[ProsConsItem]
        cons: List[ProsConsItem]
        pros_color: ThemeColor = "green"
        cons_color: ThemeColor = "red"

    example = {"component_type": "ProsCons", "heading": "Microservices", "pros": ["Independent deploys", "Scale per service"],
               "cons": ["Network complexity", "Harder debugging"]}
    example_narration = "Microservices give independent deploys and scaling, but bring network complexity and harder debugging."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        pc, cc = c.color(v.pros_color), c.color(v.cons_color)

        def column(title, items, col, icon, w, h):
            n = max(1, len(items))
            head = c.T(title, 26, bold=True, color=col)
            rows = VGroup()
            avail = h - 1.0
            rh = min(1.4 if c.portrait else 1.0, avail / n - 0.12)
            for it in items:
                ic = c.icon(icon, 0.45, col)
                tx = c.wrap(it.text, 20, w - 1.6)
                row = VGroup(ic, tx).arrange(RIGHT, buff=0.25, aligned_edge=ORIGIN)
                rows.add(left_pack(c, w, max(0.7, rh), row, col, glow=False))
            rows.arrange(DOWN, buff=0.14)
            col_g = VGroup(head, rows).arrange(DOWN, buff=0.3)
            return col_g, rows

        if c.portrait:
            w, h = body.w, body.h / 2 - 0.1
        else:
            w, h = body.w / 2 - 0.2, body.h
        pcol, prows = column(v.pros_title, v.pros, pc, "circle-check", w, h)
        ccol, crows = column(v.cons_title, v.cons, cc, "circle-x", w, h)
        if c.portrait:
            both = VGroup(pcol, ccol).arrange(DOWN, buff=0.5)
        else:
            both = VGroup(pcol, ccol).arrange(RIGHT, buff=0.4, aligned_edge=UP)
        c.fit(both, body.w, body.h, pad=0.0)
        both.move_to(body.center)
        c.play(FadeIn(pcol[0], shift=DOWN * 0.15), FadeIn(ccol[0], shift=DOWN * 0.15), rt=0.5)

        seq = [(r, it) for r, it in zip(prows, v.pros)] + [(r, it) for r, it in zip(crows, v.cons)]
        times = c.cue_times([it.exact_time for _, it in seq], start_offset=0.9)
        for (r, _), t in zip(seq, times):
            c.at(t, FadeIn(r, shift=UP * 0.2), sfx="pop.wav", rt=0.4)
        c.hold()


# ======================================================================
@register
class CallToAction(Component):
    name = "CallToAction"
    description = "Closing card with a pulsing button (Subscribe / Follow / Download) and handle."
    best_for = "video outro, follow/subscribe prompt, link in bio, newsletter"

    class Spec(VisualSpec):
        component_type: Literal["CallToAction"] = "CallToAction"
        title: str = "Enjoyed this?"
        subtitle: str = ""
        button_text: str = "Follow for more"
        handle: str = ""
        icon: str = "bell"
        theme_color: ThemeColor = "accent"

    example = {"component_type": "CallToAction", "title": "Learn one concept a day", "button_text": "Follow", "handle": "@yourchannel"}
    example_narration = "If this helped, follow for one new concept every day."

    def render(self):
        c, v = self.ctx, self.v
        col = c.color(v.theme_color)
        region = c.full
        ic = c.icon(v.icon, 1.0, col)
        title = c.wrap(v.title, 46, region.w, align=ORIGIN, bold=True)
        parts = [ic, title]
        if v.subtitle:
            parts.append(c.wrap(v.subtitle, 22, region.w * 0.9, align=ORIGIN, color=c.theme.dim))
        btn_t = c.T(v.button_text, 28, bold=True, color="#05070D")
        btn = VGroup(RoundedRectangle(width=btn_t.width + 1.2, height=btn_t.height + 0.6, corner_radius=0.5,
                                      fill_color=col, fill_opacity=1, stroke_width=0), btn_t)
        btn_t.move_to(btn[0])
        parts.append(btn)
        if v.handle:
            parts.append(c.T(v.handle, 22, color=c.theme.dim))
        stack = VGroup(*parts).arrange(DOWN, buff=0.45)
        c.fit(stack, region.w, region.h, pad=0.05)
        stack.move_to(region.center)
        c.play(FadeIn(ic, scale=0.6), FadeIn(title, shift=UP * 0.3), sfx="whoosh_soft.wav", rt=0.7)
        rest = [p for p in parts[2:] if p is not btn]
        if v.subtitle:
            c.play(FadeIn(parts[2], shift=UP * 0.2), rt=0.4)
        c.play(GrowFromCenter(btn), sfx="card_pop.wav", rt=0.5)
        if v.handle:
            c.play(FadeIn(parts[-1]), rt=0.4)
        while c.now + 0.9 < c.end:
            c.play(Indicate(btn, scale_factor=1.08, color=col), rt=0.8)
        c.hold()
