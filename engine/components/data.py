"""Data components: big stats, bar / line / donut charts, comparison tables."""

import math
from typing import List, Literal, Optional

from manim import *  # noqa: F401,F403
from pydantic import Field, model_validator

from engine.components._common import left_pack
from engine.registry import Component, Cue, VisualSpec, register
from engine.theme import ThemeColor


def fmt_num(v: float, prefix="", suffix="", decimals=0) -> str:
    return f"{prefix}{v:,.{decimals}f}{suffix}"


def nice_ticks(lo: float, hi: float, n: int = 4):
    span = max(hi - lo, 1e-9)
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=raw)
    start = math.floor(lo / step) * step
    ticks, t = [], start
    while t <= hi + step * 0.5:
        ticks.append(round(t, 10))
        t += step
    return ticks


# ======================================================================
class StatItem(Cue):
    value: float
    label: str
    prefix: str = ""
    suffix: str = ""
    decimals: int = 0
    sublabel: str = ""
    delta: str = ""
    delta_positive: bool = True
    icon: str = ""
    color_theme: ThemeColor = "accent"


@register
class BigStat(Component):
    name = "BigStat"
    description = "One to four huge KPI numbers that count up, with label, delta badge and optional icon."
    best_for = "headline numbers, KPIs, milestones, 'X million users', before/after metrics"

    class Spec(VisualSpec):
        component_type: Literal["BigStat"] = "BigStat"
        stats: List[StatItem]
        count_up: bool = True

    example = {"component_type": "BigStat", "heading": "Growth in 2024", "stats": [
        {"value": 2.4, "suffix": "M", "decimals": 1, "label": "Active users", "delta": "+38% YoY", "icon": "users", "trigger_keyword": "users"},
        {"value": 120, "prefix": "$", "suffix": "K", "label": "Monthly revenue", "delta": "+12%", "icon": "banknote", "trigger_keyword": "revenue"}]}
    example_narration = "We reached 2.4 million active users, and monthly revenue climbed to 120 thousand dollars."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        n = len(v.stats)
        single = n == 1
        if single:
            cw, ch = body.w, min(body.h, 5.0)
        elif c.portrait:
            cw, ch = body.w, min(4.4, (body.h - 0.3 * (n - 1)) / n)
        else:
            cw, ch = (body.w - 0.4 * (n - 1)) / n, min(body.h, 4.4)

        cards, holders = [], []
        for st in v.stats:
            col = c.color(st.color_theme)
            big_size = (110 if single else 70)
            holder = c.T(fmt_num(0 if v.count_up else st.value, st.prefix, st.suffix, st.decimals), big_size, bold=True, color=col)
            lab = c.T(st.label, 26 if single else 20, bold=True)
            items = []
            if st.icon:
                items.append(c.icon(st.icon, 0.7, col))
            items += [holder, lab]
            if st.sublabel:
                items.append(c.T(st.sublabel, 16, color=c.theme.dim))
            if st.delta:
                dcol = c.color("green" if st.delta_positive else "red")
                arrow = "▲ " if st.delta_positive else "▼ "
                dt = c.T(arrow + st.delta, 20, bold=True, color=dcol)
                pill = RoundedRectangle(width=dt.width + 0.5, height=dt.height + 0.3, corner_radius=0.25, stroke_color=dcol,
                                        stroke_width=2, fill_color=dcol, fill_opacity=0.14)
                items.append(VGroup(pill, dt.move_to(pill)))
            inner = VGroup(*items).arrange(DOWN, buff=0.22)
            card = c.pack(cw, ch, inner, col, pad=0.3)
            cards.append(card)
            holders.append((holder, st, col, big_size))
        grp = VGroup(*cards)
        if n > 1:
            grp.arrange(DOWN if c.portrait else RIGHT, buff=0.35)
        grp.move_to(body.center)

        times = c.cue_times([s.exact_time for s in v.stats], start_offset=0.6, end_pad=1.8)
        for card, (holder, st, col, size), t in zip(cards, holders, times):
            c.at(t, FadeIn(card, scale=0.92), sfx="card_pop.wav", rt=0.5)
            if v.count_up:
                anchor = holder.get_center()
                top_w = holder.width

                def make(val, st=st, col=col, size=size, anchor=anchor):
                    m = c.T(fmt_num(val, st.prefix, st.suffix, st.decimals), size, bold=True, color=col)
                    return m.move_to(anchor)

                def upd(m, a, st=st, make=make):
                    m.become(make(st.value * a))

                c.play(UpdateFromAlphaFunc(holder, upd, rate_func=rush_from), rt=1.2)
                holder.become(make(st.value))
        c.hold()


# ======================================================================
class BarItem(Cue):
    label: str
    value: float
    color_theme: ThemeColor = "accent"
    highlight: bool = False


@register
class BarChart(Component):
    name = "BarChart"
    description = "Animated bar chart (horizontal or vertical) with value labels and optional highlighted bar."
    best_for = "comparisons, rankings, benchmarks, market share, performance numbers"

    class Spec(VisualSpec):
        component_type: Literal["BarChart"] = "BarChart"
        bars: List[BarItem]
        orientation: Literal["auto", "horizontal", "vertical"] = "auto"
        value_prefix: str = ""
        value_suffix: str = ""
        decimals: int = 0

    example = {"component_type": "BarChart", "heading": "Requests per second", "value_suffix": "k",
               "bars": [{"label": "Node", "value": 42, "trigger_keyword": "node"},
                        {"label": "Go", "value": 118, "highlight": True, "trigger_keyword": "go"},
                        {"label": "Rust", "value": 131, "trigger_keyword": "rust"}]}
    example_narration = "Node handles 42 thousand, Go jumps to 118 thousand, and Rust edges ahead at 131 thousand."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        bars = v.bars
        n = len(bars)
        vmax = max(b.value for b in bars) or 1
        horizontal = v.orientation == "horizontal" or (v.orientation == "auto" and (c.portrait or n > 6))
        any_hl = any(b.highlight for b in bars)

        def bar_color(b):
            col = c.color(b.color_theme)
            if any_hl and not b.highlight:
                return c.theme.dim
            return col

        times = c.cue_times([b.exact_time for b in bars], start_offset=0.6, end_pad=1.4)
        base = None
        if horizontal:
            label_w = min(3.0, body.w * 0.3)
            track_w = body.w - label_w - 1.6
            rh = min(1.7 if c.portrait else 1.1, (body.h - 0.25 * (n - 1)) / n)
            y0 = body.top - rh / 2 - max(0, (body.h - (rh * n + 0.25 * (n - 1))) / 2)
            made = []
            for i, b in enumerate(bars):
                y = y0 - i * (rh + 0.25)
                lab = c.wrap(b.label, 20, label_w, align=RIGHT, bold=True)
                lab.move_to([body.left + label_w - lab.width / 2, y, 0])
                w = max(0.05, track_w * b.value / vmax)
                col = bar_color(b)
                bar = RoundedRectangle(width=w, height=rh * 0.7, corner_radius=0.1, fill_color=col, fill_opacity=0.95,
                                       stroke_width=0)
                bar.move_to([body.left + label_w + 0.3 + w / 2, y, 0])
                val = c.T(fmt_num(b.value, v.value_prefix, v.value_suffix, v.decimals), 20, bold=True, color=col)
                val.next_to(bar, RIGHT, buff=0.2)
                made.append((lab, bar, val))
            for (lab, bar, val), t in zip(made, times):
                c.at(t, FadeIn(lab, shift=RIGHT * 0.2), GrowFromEdge(bar, LEFT), sfx="pop.wav", rt=0.7)
                c.play(FadeIn(val, scale=0.8), rt=0.25)
        else:
            axis_y = body.bottom + 1.0
            plot_h = body.h - 1.6
            slot = body.w / n
            bw = min(1.4, slot * 0.62)
            base = Line([body.left, axis_y, 0], [body.right, axis_y, 0], stroke_width=3, color=c.theme.stroke)
            c.play(Create(base), rt=0.4)
            for b, t, i in zip(bars, times, range(n)):
                x = body.left + slot * (i + 0.5)
                h = max(0.06, plot_h * b.value / vmax)
                col = bar_color(b)
                bar = RoundedRectangle(width=bw, height=h, corner_radius=min(0.12, bw / 4), fill_color=col, fill_opacity=0.95, stroke_width=0)
                bar.move_to([x, axis_y + h / 2, 0])
                lab = c.wrap(b.label, 17, slot * 0.95, align=ORIGIN, bold=True)
                lab.move_to([x, axis_y - 0.45, 0])
                val = c.T(fmt_num(b.value, v.value_prefix, v.value_suffix, v.decimals), 20, bold=True, color=col)
                val.next_to(bar, UP, buff=0.15)
                c.at(t, FadeIn(lab, shift=UP * 0.15), GrowFromEdge(bar, DOWN), sfx="pop.wav", rt=0.7)
                c.play(FadeIn(val, scale=0.8), rt=0.25)
        c.hold()


# ======================================================================
class Series(Cue):
    name: str = ""
    values: List[float]
    color_theme: ThemeColor = "accent"


class Annotation(Cue):
    index: int
    text: str
    series: int = 0


@register
class LineChart(Component):
    name = "LineChart"
    description = "Animated line chart (1-3 series) with gridlines, x labels and callout annotations tied to spoken words."
    best_for = "trends over time, growth curves, stock/price history, performance over versions"

    class Spec(VisualSpec):
        component_type: Literal["LineChart"] = "LineChart"
        series: List[Series]
        x_labels: List[str] = Field(default_factory=list)
        y_prefix: str = ""
        y_suffix: str = ""
        annotations: List[Annotation] = Field(default_factory=list)
        fill_area: bool = True

    example = {"component_type": "LineChart", "heading": "Weekly active users", "y_suffix": "k",
               "x_labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
               "series": [{"name": "Users", "values": [10, 14, 13, 28, 41, 66]}],
               "annotations": [{"index": 3, "text": "Launch", "trigger_keyword": "launch"}]}
    example_narration = "Growth was flat until the April launch, when users shot up past sixty thousand."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        legend_h = 0.7 if len(v.series) > 1 else 0.0
        pad_l, pad_b = 1.1, 0.8
        px0, px1 = body.left + pad_l, body.right - 0.3
        py0, py1 = body.bottom + pad_b, body.top - 0.5 - legend_h
        allv = [x for s in v.series for x in s.values]
        lo, hi = min(0, min(allv)), max(allv)
        ticks = nice_ticks(lo, hi * 1.05, 4)
        ymin, ymax = ticks[0], ticks[-1]
        npts = max(len(s.values) for s in v.series)

        def P(i, val):
            x = px0 + (px1 - px0) * (i / max(1, npts - 1))
            y = py0 + (py1 - py0) * ((val - ymin) / (ymax - ymin))
            return np.array([x, y, 0.0])

        grid = VGroup()
        for tv in ticks:
            y = P(0, tv)[1]
            grid.add(Line([px0, y, 0], [px1, y, 0], stroke_width=1.2, color=c.theme.stroke, stroke_opacity=0.9))
            grid.add(c.T(fmt_num(tv, v.y_prefix, v.y_suffix, 0 if tv == int(tv) else 1), 14, color=c.theme.dim).move_to([px0 - 0.1, y, 0], aligned_edge=RIGHT))
        xl = VGroup()
        if v.x_labels:
            step = max(1, math.ceil(len(v.x_labels) / (5 if c.portrait else 9)))
            for i, lab in enumerate(v.x_labels):
                if i % step == 0:
                    xl.add(c.T(lab, 14, color=c.theme.dim).move_to(P(i, ymin) + DOWN * 0.35))
        c.play(FadeIn(grid), FadeIn(xl), rt=0.6)

        lines = []
        if legend_h:
            leg = VGroup(*[VGroup(Dot(radius=0.08, color=c.color(s.color_theme)), c.T(s.name, 16, color=c.theme.dim)).arrange(RIGHT, buff=0.15)
                           for s in v.series]).arrange(RIGHT, buff=0.5).move_to([body.cx if hasattr(body, "cx") else 0, body.top - 0.3, 0])
            c.play(FadeIn(leg), rt=0.3)
        draws = []
        for s in v.series:
            col = c.color(s.color_theme)
            pts = [P(i, val) for i, val in enumerate(s.values)]
            line = VMobject(stroke_color=col, stroke_width=5 if not c.portrait else 6).set_points_smoothly(pts) if len(pts) > 2 else \
                VMobject(stroke_color=col, stroke_width=5).set_points_as_corners(pts)
            line.set_fill(opacity=0)
            lines.append((line, pts, col))
            draws.append(Create(line, rate_func=smooth))
        draw_t = min(2.6, max(1.0, c.dur * 0.35))
        c.play(*draws, rt=draw_t)
        if v.fill_area:
            for line, pts, col in lines:
                area = Polygon(*([pts[0] * RIGHT + P(0, ymin)[1] * UP] + pts + [pts[-1][0] * RIGHT + P(0, ymin)[1] * UP]),
                               fill_color=col, fill_opacity=0.12, stroke_width=0)
                self.ctx.scene.add(area)
                area.set_z_index(-1)
        dots = []
        for line, pts, col in lines:
            for p in pts:
                d = Dot(p, radius=0.07, color=col)
                dots.append(d)
        c.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.05), rt=0.6)

        if v.annotations:
            times = c.cue_times([a.exact_time for a in v.annotations], start_offset=max(0.6, c.now - c.t0 + 0.2))
            for a, t in zip(v.annotations, times):
                s = v.series[min(a.series, len(v.series) - 1)]
                i = max(0, min(a.index, len(s.values) - 1))
                p = P(i, s.values[i])
                col = c.color(s.color_theme)
                ring = Circle(radius=0.2, color=col, stroke_width=3).move_to(p)
                lab = c.T(a.text, 18, bold=True)
                bubble = c.pack(lab.width + 0.7, lab.height + 0.5, lab, col, pad=0.1, glow=False)
                up = p[1] < (py0 + py1) / 2
                bubble.next_to(p, UP if up else DOWN, buff=0.35)
                bubble.shift(LEFT * max(0, bubble.get_right()[0] - body.right) + RIGHT * max(0, body.left - bubble.get_left()[0]))
                c.at(t, Create(ring), FadeIn(bubble, shift=UP * 0.15), sfx="card_pop.wav", rt=0.5)
        c.hold()


# ======================================================================
class SliceItem(Cue):
    label: str
    value: float
    color_theme: ThemeColor = "accent"


@register
class DonutChart(Component):
    name = "DonutChart"
    description = "Donut / pie breakdown with a legend and centre label; slices reveal as they are spoken."
    best_for = "shares, breakdowns, budgets, market split, composition"

    class Spec(VisualSpec):
        component_type: Literal["DonutChart"] = "DonutChart"
        slices: List[SliceItem]
        center_value: str = ""
        center_label: str = ""

    example = {"component_type": "DonutChart", "heading": "Where the budget goes", "center_value": "$1.2M", "center_label": "Total",
               "slices": [{"label": "Engineering", "value": 55, "color_theme": "cyan", "trigger_keyword": "engineering"},
                          {"label": "Marketing", "value": 25, "color_theme": "purple", "trigger_keyword": "marketing"},
                          {"label": "Ops", "value": 20, "color_theme": "amber", "trigger_keyword": "ops"}]}
    example_narration = "Engineering takes fifty five percent, marketing twenty five, and ops the remaining twenty."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        total = sum(s.value for s in v.slices) or 1
        R = min(body.w * (0.5 if c.portrait else 0.28), body.h * (0.32 if c.portrait else 0.5)) 
        cx = 0 if c.portrait else body.left + R + 0.4
        cy = body.top - R - 0.2 if c.portrait else body.cy
        ring_w = R * 0.42
        cum = 0.0
        sectors = []
        for s in v.slices:
            ang = TAU * s.value / total
            sec = AnnularSector(inner_radius=R - ring_w, outer_radius=R, angle=ang * 0.992, start_angle=PI / 2 - cum - ang,
                                fill_color=c.color(s.color_theme), fill_opacity=1, stroke_width=0)
            sec.move_arc_center_to([cx, cy, 0])
            sectors.append(sec)
            cum += ang
        centre = VGroup()
        if v.center_value:
            centre.add(c.T(v.center_value, 44, bold=True))
        if v.center_label:
            centre.add(c.T(v.center_label, 18, color=c.theme.dim))
        centre.arrange(DOWN, buff=0.1)
        c.fit(centre, 2 * (R - ring_w) * 0.9, 2 * (R - ring_w) * 0.9, pad=0.0)
        centre.move_to([cx, cy, 0])

        legend = VGroup()
        for s in v.slices:
            col = c.color(s.color_theme)
            pct = f"{100 * s.value / total:.0f}%"
            row = VGroup(RoundedRectangle(width=0.3, height=0.3, corner_radius=0.08, fill_color=col, fill_opacity=1, stroke_width=0),
                         c.T(s.label, 22, bold=True), c.T(pct, 22, bold=True, color=col)).arrange(RIGHT, buff=0.25)
            legend.add(row)
        legend.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        if c.portrait:
            legend.move_to([0, cy - R - 0.5 - legend.height / 2, 0])
        else:
            legend.move_to([cx + R + 1.2 + legend.width / 2, cy, 0])
        c.fit(legend, body.w, body.h, pad=0.0)

        c.play(FadeIn(centre, scale=0.9), rt=0.4)
        times = c.cue_times([s.exact_time for s in v.slices], start_offset=0.6)
        for sec, row, t in zip(sectors, legend, times):
            c.at(t, FadeIn(sec, scale=0.85), FadeIn(row, shift=LEFT * 0.2), sfx="pop.wav", rt=0.6)
        c.hold()


# ======================================================================
class TableRow(Cue):
    cells: List[str]

    @model_validator(mode="before")
    @classmethod
    def _from_list(cls, data):
        return {"cells": data} if isinstance(data, list) else data


@register
class ComparisonTable(Component):
    name = "ComparisonTable"
    description = "Feature comparison grid with a highlighted column; rows reveal as spoken. Cells '✓' / '✗' become icons."
    best_for = "product comparisons, plan tiers, framework vs framework, feature matrices"

    class Spec(VisualSpec):
        component_type: Literal["ComparisonTable"] = "ComparisonTable"
        columns: List[str]
        rows: List[TableRow]
        highlight_column: Optional[int] = None

    example = {"component_type": "ComparisonTable", "heading": "Free vs Pro", "columns": ["Feature", "Free", "Pro"],
               "highlight_column": 2,
               "rows": [{"cells": ["Projects", "3", "Unlimited"], "trigger_keyword": "projects"},
                        {"cells": ["Support", "✗", "✓"], "trigger_keyword": "support"}]}
    example_narration = "Free gives you three projects and no support, while Pro is unlimited with priority support."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        ncol = len(v.columns)
        first_w = body.w * (0.34 if ncol > 2 else 0.5)
        other_w = (body.w - first_w) / max(1, ncol - 1)
        widths = [first_w] + [other_w] * (ncol - 1)
        xs, x = [], body.left
        for w in widths:
            xs.append(x + w / 2)
            x += w
        nrows = len(v.rows)
        row_h = min(1.7 if c.portrait else 1.2, (body.h - 1.0) / max(1, nrows) - 0.1)
        size = 22 if ncol <= 3 else 18

        def cell(text, w, bold=False, color=None):
            t = text.strip()
            if t in ("✓", "yes", "Yes", "true"):
                return c.icon("circle-check", 0.5, c.color("green"))
            if t in ("✗", "no", "No", "false", "x", "X"):
                return c.icon("circle-x", 0.5, c.color("red"))
            return c.wrap(t, size, w - 0.3, align=ORIGIN, bold=bold, color=color)

        head = VGroup()
        for i, name in enumerate(v.columns):
            col = c.accent if (v.highlight_column == i) else c.theme.text
            m = cell(name, widths[i], bold=True, color=col)
            m.move_to([xs[i], 0, 0])
            head.add(m)
        head_bg = RoundedRectangle(width=body.w, height=0.9, corner_radius=0.15, fill_color=c.theme.card_alt, fill_opacity=1, stroke_color=c.theme.stroke)
        head_bg.move_to([0, 0, 0])
        head_grp = VGroup(head_bg, head)
        head_grp.move_to([0, body.top - 0.45, 0])
        head.move_to(head_bg.get_center() * 0 + head_bg.get_center())
        for i, m in enumerate(head):
            m.set_x(xs[i])

        rows = []
        for r_i, row in enumerate(v.rows):
            bg = RoundedRectangle(width=body.w, height=row_h, corner_radius=0.12,
                                  fill_color=c.theme.card if r_i % 2 == 0 else c.theme.card_alt, fill_opacity=0.95, stroke_width=0)
            y = body.top - 0.9 - 0.15 - row_h / 2 - r_i * (row_h + 0.1)
            bg.move_to([0, y, 0])
            cells = VGroup()
            for i, txt in enumerate(row.cells[:ncol]):
                m = cell(txt, widths[i], bold=(i == 0 or v.highlight_column == i), color=c.accent if v.highlight_column == i and i != 0 else None)
                c.fit(m, widths[i], row_h, pad=0.05)
                m.move_to([xs[i], y, 0])
                cells.add(m)
            rows.append(VGroup(bg, cells))
        allrows = VGroup(*rows)

        c.play(FadeIn(head_grp, shift=DOWN * 0.2), rt=0.5)
        if v.highlight_column is not None and nrows:
            hc = v.highlight_column
            top = head_bg.get_top()[1]
            bot = rows[-1][0].get_bottom()[1]
            hl = RoundedRectangle(width=widths[hc] - 0.1, height=top - bot + 0.1, corner_radius=0.15, stroke_color=c.accent, stroke_width=3, fill_opacity=0)
            hl.move_to([xs[hc], (top + bot) / 2, 0])
            c.play(Create(hl), rt=0.5)
        times = c.cue_times([r.exact_time for r in v.rows], start_offset=0.9)
        for r, t in zip(rows, times):
            c.at(t, FadeIn(r, shift=UP * 0.2), sfx="pop.wav", rt=0.45)
        c.hold()
