"""Diagram & sequence components: architecture, process steps, timeline, mind map."""

import math
from typing import List, Literal, Optional

import numpy as np
from manim import *  # noqa: F401,F403
from pydantic import Field

from engine.components._common import left_pack, number_badge
from engine.registry import Component, Cue, VisualSpec, register
from engine.theme import ThemeColor


def rect_edge_point(center, half_w, half_h, toward):
    d = np.array(toward, dtype=float) - np.array(center, dtype=float)
    d[2] = 0
    if abs(d[0]) < 1e-6 and abs(d[1]) < 1e-6:
        return np.array(center, dtype=float)
    tx = half_w / abs(d[0]) if abs(d[0]) > 1e-6 else 1e9
    ty = half_h / abs(d[1]) if abs(d[1]) > 1e-6 else 1e9
    return np.array(center, dtype=float) + d * min(tx, ty)


# ======================================================================
class ArchNodeItem(Cue):
    node_id: str
    label: str
    sublabel: str = ""
    icon: str = "server"
    color_theme: ThemeColor = "cyan"


class ArchEdgeItem(Cue):
    source: str
    target: str
    label: str = ""
    color_theme: ThemeColor = "cyan"
    is_blocked: bool = False


@register
class ArchitectureFlowCanvas(Component):
    name = "ArchitectureFlowCanvas"
    description = "System/architecture diagram: icon nodes, labelled arrows, data packets flowing along edges. Pipeline, fan-out or split layouts."
    best_for = "system design, data pipelines, request flows, microservices, networking, CI/CD"

    class Spec(VisualSpec):
        component_type: Literal["ArchitectureFlowCanvas"] = "ArchitectureFlowCanvas"
        layout_mode: Literal["pipeline", "fan_out", "comparison_split"] = "pipeline"
        nodes: List[ArchNodeItem]
        edges: List[ArchEdgeItem] = Field(default_factory=list)

    example = {"component_type": "ArchitectureFlowCanvas", "heading": "Request Flow", "subheading": "From browser to database",
               "nodes": [{"node_id": "web", "label": "Browser", "sublabel": "HTTPS", "icon": "globe", "color_theme": "blue", "trigger_keyword": "browser"},
                         {"node_id": "api", "label": "API", "sublabel": "FastAPI", "icon": "fastapi", "color_theme": "cyan", "trigger_keyword": "api"},
                         {"node_id": "db", "label": "Postgres", "sublabel": "Primary", "icon": "postgresql", "color_theme": "green", "trigger_keyword": "database"}],
               "edges": [{"source": "web", "target": "api", "label": "REST"}, {"source": "api", "target": "db", "label": "SQL", "color_theme": "green"}]}
    example_narration = "The browser calls the API, and the API reads from the database."

    def _layout(self, body, n):
        c, mode = self.ctx, self.v.layout_mode
        gap = 0.55
        pos, cw, ch = [], 0, 0
        if mode == "fan_out" and n >= 3:
            rest = n - 1
            if c.portrait:
                cols = 2 if rest > 2 else rest
                rows = math.ceil(rest / cols)
                cw = (body.w - gap * (cols - 1)) / cols
                ch = min(2.4, (body.h - 2.2 - gap * rows) / rows)
                pos.append((0, body.top - ch / 2))
                for i in range(rest):
                    r, k = divmod(i, cols)
                    inrow = min(cols, rest - r * cols)
                    x = (k - (inrow - 1) / 2) * (cw + gap)
                    pos.append((x, body.top - ch - 1.2 - r * (ch + gap) - ch / 2))
            else:
                ch = min(1.7, (body.h - gap * (rest - 1)) / rest)
                cw = min(3.0, (body.w - 2.2) / 2)
                pos.append((body.left + cw / 2, body.cy))
                for i in range(rest):
                    pos.append((body.right - cw / 2, body.top - ch / 2 - i * (ch + gap)
                                - (body.h - (rest * ch + (rest - 1) * gap)) / 2))
        elif mode == "comparison_split" and n >= 2:
            half = math.ceil(n / 2)
            groups = [list(range(half)), list(range(half, n))]
            if c.portrait:
                cw = min(body.w, (body.w - gap * (half - 1)) / max(1, half))
                ch = min(2.4, (body.h - 1.5) / 2)
                pos = [None] * n
                for gi, g in enumerate(groups):
                    y = body.top - ch / 2 - gi * (ch + 1.4)
                    for k, idx in enumerate(g):
                        pos[idx] = ((k - (len(g) - 1) / 2) * (cw + gap), y)
            else:
                cw = min(3.0, (body.w - 2.0) / 2)
                ch = min(1.8, (body.h - gap * (half - 1)) / half)
                pos = [None] * n
                for gi, g in enumerate(groups):
                    x = body.left + cw / 2 if gi == 0 else body.right - cw / 2
                    for k, idx in enumerate(g):
                        pos[idx] = (x, body.top - ch / 2 - k * (ch + gap) - (body.h - (len(g) * ch + (len(g) - 1) * gap)) / 2)
        else:  # pipeline
            if c.portrait:
                cols = 1 if n <= 4 else 2
                rows = math.ceil(n / cols)
                cw = (body.w - gap * (cols - 1)) / cols
                ch = min(2.0, (body.h - gap * (rows - 1)) / rows)
                for i in range(n):
                    r, k = divmod(i, cols)
                    if r % 2 == 1:
                        k = cols - 1 - k          # snake so arrows stay short
                    x = (k - (cols - 1) / 2) * (cw + gap)
                    y = body.top - ch / 2 - r * (ch + gap) - (body.h - (rows * ch + (rows - 1) * gap)) / 2
                    pos.append((x, y))
            else:
                cols = n if n <= 4 else math.ceil(n / 2)
                rows = math.ceil(n / cols)
                cw = min(3.0, (body.w - gap * (cols - 1)) / cols)
                ch = min(2.0, (body.h - gap * (rows - 1)) / rows)
                for i in range(n):
                    r, k = divmod(i, cols)
                    if r % 2 == 1:
                        k = cols - 1 - k
                    x = (k - (cols - 1) / 2) * (cw + gap)
                    y = body.top - ch / 2 - r * (ch + gap) - (body.h - (rows * ch + (rows - 1) * gap)) / 2
                    pos.append((x, y))
        return pos, cw, ch

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        nodes = v.nodes
        n = len(nodes)
        pos, cw, ch = self._layout(body, n)
        cards, by_id = [], {}
        for nd, (x, y) in zip(nodes, pos):
            col = c.color(nd.color_theme)
            ic = c.icon(nd.icon, 0.6, col)
            items = [ic, c.wrap(nd.label, 20, cw - 0.4, align=ORIGIN, bold=True)]
            if nd.sublabel:
                items.append(c.wrap(nd.sublabel, 14, cw - 0.4, align=ORIGIN, color=c.theme.dim))
            inner = VGroup(*items).arrange(DOWN, buff=0.12)
            card = c.pack(cw, ch, inner, col, pad=0.15)
            card.move_to([x, y, 0])
            cards.append(card)
            by_id[nd.node_id] = (card, (x, y), col)

        times = c.cue_times([nd.exact_time for nd in nodes], start_offset=0.7, end_pad=2.6)
        shown_at = {}
        for nd, card, t in zip(nodes, cards, times):
            c.at(t, FadeIn(card, scale=0.88), sfx="card_pop.wav", rt=0.5)
            shown_at[nd.node_id] = t

        packets = []
        for e in v.edges:
            if e.source not in by_id or e.target not in by_id:
                continue
            (cs, ps, _), (ct, pt, _) = by_id[e.source], by_id[e.target]
            col = c.color("red" if e.is_blocked else e.color_theme)
            a = rect_edge_point([*ps, 0], cw / 2, ch / 2, [*pt, 0])
            b = rect_edge_point([*pt, 0], cw / 2, ch / 2, [*ps, 0])
            arrow = Arrow(a, b, buff=0.08, color=col, stroke_width=4, max_tip_length_to_length_ratio=0.25)
            extras = [arrow]
            if e.label:
                lab = c.T(e.label, 14, color=col, bold=True)
                mid = (a + b) / 2
                norm = np.array([-(b - a)[1], (b - a)[0], 0])
                norm = norm / (np.linalg.norm(norm) + 1e-9)
                lab.move_to(mid + norm * 0.3 * (1 if norm[1] >= 0 or abs(norm[0]) > abs(norm[1]) else -1))
                extras.append(lab)
            if e.is_blocked:
                x = VGroup(Circle(radius=0.2, fill_color=col, fill_opacity=1, stroke_color=WHITE, stroke_width=2),
                           c.T("✕", 14, bold=True, color="#FFFFFF")).move_to((a + b) / 2)
                extras.append(x)
            t_e = max(shown_at[e.source], shown_at[e.target]) + 0.3
            c.at(t_e, *[Create(m) if m is arrow else FadeIn(m) for m in extras], sfx="whoosh_soft.wav", rt=0.5)
            if not e.is_blocked:
                packets.append((Dot(radius=0.09, color=col), Line(a, b)))
        loops = 0
        while packets and c.now + 1.3 < c.end and loops < 3:
            c.play(*[MoveAlongPath(p, path, rate_func=smooth) for p, path in packets], rt=1.1)
            for p, _ in packets:
                c.scene.remove(p)
            loops += 1
        c.hold()


# ======================================================================
class StepItem(Cue):
    title: str
    detail: str = ""
    icon: str = ""
    color_theme: ThemeColor = "accent"


@register
class ProcessSteps(Component):
    name = "ProcessSteps"
    description = "Numbered how-to / pipeline steps connected by arrows; active step lights up as it is spoken, finished steps turn into check marks."
    best_for = "tutorials, how-it-works, onboarding, recipes, workflows, step 1-2-3"

    class Spec(VisualSpec):
        component_type: Literal["ProcessSteps"] = "ProcessSteps"
        steps: List[StepItem]

    example = {"component_type": "ProcessSteps", "heading": "Deploy in 4 steps",
               "steps": [{"title": "Build", "detail": "docker build", "trigger_keyword": "build"},
                         {"title": "Test", "detail": "pytest -q", "trigger_keyword": "test"},
                         {"title": "Push", "detail": "to registry", "trigger_keyword": "push"},
                         {"title": "Release", "detail": "kubectl apply", "trigger_keyword": "release"}]}
    example_narration = "First build the image, then test it, push it to the registry, and finally release."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        n = len(v.steps)
        gap = 0.5
        if c.portrait:
            cw, ch = body.w, min(2.5, (body.h - gap * (n - 1)) / n)
            centers = [(0, body.top - ch / 2 - i * (ch + gap) - (body.h - (n * ch + (n - 1) * gap)) / 2) for i in range(n)]
        else:
            cols = n if n <= 4 else math.ceil(n / 2)
            rows = math.ceil(n / cols)
            cw = min(3.2, (body.w - gap * (cols - 1)) / cols)
            ch = min(2.8, (body.h - gap * (rows - 1)) / rows)
            centers = []
            for i in range(n):
                r, k = divmod(i, cols)
                if r % 2 == 1:
                    k = cols - 1 - k
                centers.append(((k - (cols - 1) / 2) * (cw + gap), body.top - ch / 2 - r * (ch + gap) - (body.h - (rows * ch + (rows - 1) * gap)) / 2))
        cards, badges = [], []
        for i, (st, (x, y)) in enumerate(zip(v.steps, centers)):
            col = c.color(st.color_theme)
            badge = number_badge(c, i + 1, col, r=0.32)
            title = c.wrap(st.title, 24, cw - 1.4 if c.portrait else cw - 0.5, bold=True)
            parts = [title]
            if st.detail:
                parts.append(c.wrap(st.detail, 16, cw - 1.4 if c.portrait else cw - 0.5, color=c.theme.dim))
            txt = VGroup(*parts).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
            if c.portrait:
                inner = VGroup(badge, txt).arrange(RIGHT, buff=0.4)
                card = left_pack(c, cw, ch, inner, col)
            else:
                head = VGroup(c.icon(st.icon, 0.55, col) if st.icon else VGroup(), badge).arrange(RIGHT, buff=0.3)
                inner = VGroup(head, txt).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
                card = left_pack(c, cw, ch, inner, col, pad_x=0.3)
            card.move_to([x, y, 0])
            cards.append(card)
            badges.append(badge)
        times = c.cue_times([s.exact_time for s in v.steps], start_offset=0.7)
        prev = None
        for i, (card, t) in enumerate(zip(cards, times)):
            anims = [FadeIn(card, shift=UP * 0.3 if not c.portrait else RIGHT * 0.4)]
            if prev is not None:
                (px, py), (nx, ny) = centers[i - 1], centers[i]
                a = rect_edge_point([px, py, 0], cw / 2, ch / 2, [nx, ny, 0])
                b = rect_edge_point([nx, ny, 0], cw / 2, ch / 2, [px, py, 0])
                anims.append(Create(Arrow(a, b, buff=0.06, color=c.accent, stroke_width=4)))
            c.at(t, *anims, sfx="card_pop.wav", rt=0.55)
            prev = card
        c.hold()


# ======================================================================
class TimelineEvent(Cue):
    date: str
    title: str
    detail: str = ""
    color_theme: ThemeColor = "accent"


@register
class Timeline(Component):
    name = "Timeline"
    description = "Chronological timeline (vertical on phones, horizontal on 16:9) with a progress line that extends as each event is spoken."
    best_for = "history, roadmaps, company story, version releases, biography, project plans"

    class Spec(VisualSpec):
        component_type: Literal["Timeline"] = "Timeline"
        events: List[TimelineEvent]

    example = {"component_type": "Timeline", "heading": "A Brief History of the Web",
               "events": [{"date": "1991", "title": "First website", "detail": "CERN", "trigger_keyword": "first"},
                          {"date": "1995", "title": "JavaScript", "detail": "10 days", "trigger_keyword": "javascript"},
                          {"date": "2007", "title": "iPhone", "detail": "Mobile web", "trigger_keyword": "iphone"}]}
    example_narration = "The first website launched in 1991, JavaScript arrived in 1995, and the iPhone reshaped everything in 2007."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        ev = v.events
        n = len(ev)
        pts, cards = [], []
        if c.portrait or n > 5:
            lx = body.left + 0.7
            step = body.h / n
            ch = min(2.4, step - 0.2)
            cw = body.w - 1.5
            for i, e in enumerate(ev):
                y = body.top - step * (i + 0.5)
                pts.append(np.array([lx, y, 0]))
                col = c.color(e.color_theme)
                parts = [c.T(e.date, 18, bold=True, color=col), c.wrap(e.title, 24, cw - 0.8, bold=True)]
                if e.detail:
                    parts.append(c.wrap(e.detail, 16, cw - 0.8, color=c.theme.dim))
                card = left_pack(c, cw, ch, VGroup(*parts).arrange(DOWN, aligned_edge=LEFT, buff=0.08), col)
                card.move_to([lx + 0.5 + cw / 2, y, 0])
                cards.append(card)
            track_a, track_b = pts[0] + UP * step * 0.35, pts[-1] + DOWN * step * 0.35
        else:
            ly = body.cy
            step = body.w / n
            cw, ch = min(3.6, step * 1.5), min(2.0, body.h / 2 - 0.5)
            for i, e in enumerate(ev):
                x = body.left + step * (i + 0.5)
                pts.append(np.array([x, ly, 0]))
                col = c.color(e.color_theme)
                parts = [c.T(e.date, 20, bold=True, color=col), c.wrap(e.title, 22, cw - 0.4, bold=True)]
                if e.detail:
                    parts.append(c.wrap(e.detail, 15, cw - 0.4, color=c.theme.dim))
                card = c.pack(cw, ch, VGroup(*parts).arrange(DOWN, buff=0.1), col, pad=0.15)
                up = i % 2 == 0
                card.move_to([x, ly + (ch / 2 + 0.6) * (1 if up else -1), 0])
                cards.append(card)
            track_a, track_b = pts[0] + LEFT * step * 0.45, pts[-1] + RIGHT * step * 0.45
        base = Line(track_a, track_b, stroke_width=4, color=c.theme.stroke)
        c.play(Create(base), rt=0.5)
        prog_start = track_a
        times = c.cue_times([e.exact_time for e in ev], start_offset=0.8)
        last = track_a
        for e, p, card, t in zip(ev, pts, cards, times):
            col = c.color(e.color_theme)
            seg = Line(last, p, stroke_width=6, color=c.accent)
            dot = Dot(p, radius=0.16, color=col)
            stem = Line(p, card.get_bottom() if card.get_center()[1] > p[1] else card.get_top(), stroke_width=2, color=col) if not (c.portrait or n > 5) else \
                Line(p, [card.get_left()[0], p[1], 0], stroke_width=2, color=col)
            c.at(t, Create(seg), FadeIn(dot, scale=0.4), Create(stem), FadeIn(card, shift=UP * 0.2), sfx="pop.wav", rt=0.55)
            last = p
        c.hold()


# ======================================================================
class Branch(Cue):
    label: str
    detail: str = ""
    icon: str = ""
    color_theme: ThemeColor = "cyan"
    children: List[str] = Field(default_factory=list)


@register
class MindMap(Component):
    name = "MindMap"
    description = "Central concept with radiating branches (and small child pills). Branches pop in as they are mentioned."
    best_for = "concept overviews, taxonomies, 'types of X', brainstorming, summaries of a topic"

    class Spec(VisualSpec):
        component_type: Literal["MindMap"] = "MindMap"
        center: str
        center_icon: str = ""
        branches: List[Branch]

    example = {"component_type": "MindMap", "center": "Machine Learning", "center_icon": "brain-circuit",
               "branches": [{"label": "Supervised", "icon": "tags", "color_theme": "cyan", "children": ["Regression", "Classification"], "trigger_keyword": "supervised"},
                            {"label": "Unsupervised", "icon": "network", "color_theme": "purple", "children": ["Clustering"], "trigger_keyword": "unsupervised"},
                            {"label": "Reinforcement", "icon": "gamepad-2", "color_theme": "amber", "children": ["Agents", "Rewards"], "trigger_keyword": "reinforcement"}]}
    example_narration = "Machine learning comes in three flavours: supervised, unsupervised, and reinforcement learning."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        n = len(v.branches)
        nw = min(3.6, body.w * 0.46) if c.portrait else min(3.6, body.w * 0.3)
        cen_w, cen_h = (4.2, 1.9) if c.portrait else (3.4, 2.0)
        centre_items = [c.icon(v.center_icon, 0.8, c.accent)] if v.center_icon else []
        centre_items.append(c.wrap(v.center, 26, cen_w - 0.6, align=ORIGIN, bold=True))
        cen = c.pack(cen_w, cen_h, VGroup(*centre_items).arrange(DOWN, buff=0.12), c.accent, pad=0.2)

        def make_node(b):
            col = c.color(b.color_theme)
            items = ([c.icon(b.icon, 0.5, col)] if b.icon else []) + [c.wrap(b.label, 20, nw - 0.4, align=ORIGIN, bold=True)]
            if b.detail:
                items.append(c.wrap(b.detail, 13, nw - 0.4, align=ORIGIN, color=c.theme.dim))
            if b.children:
                items.append(c.wrap(" · ".join(b.children[:4]), 13, nw - 0.4, align=ORIGIN, color=col))
            h = max(1.2, 0.95 + 0.3 * len(items))
            return c.pack(nw, h, VGroup(*items).arrange(DOWN, buff=0.1), col, pad=0.12), h

        nodes = [make_node(b) for b in v.branches]
        node_h = max(h for _, h in nodes)
        if c.portrait:
            cen.move_to([0, body.top - cen_h / 2, 0])
            rows_n = math.ceil(n / 2)
            area_top = body.top - cen_h - 0.9
            gap_y = min(0.35, max(0.15, (area_top - body.bottom - rows_n * node_h) / max(1, rows_n)))
            for i, (nd, h) in enumerate(nodes):
                r, k = divmod(i, 2)
                inrow = min(2, n - r * 2)
                x = (k - (inrow - 1) / 2) * (nw + 0.3)
                nd.move_to([x, area_top - node_h / 2 - r * (node_h + gap_y), 0])
        else:
            cen.move_to(body.center)
            right = list(range(0, n, 2))
            left = list(range(1, n, 2))
            for col_idx, group in ((1, right), (-1, left)):
                m = len(group)
                gy = min(0.4, max(0.15, (body.h - m * node_h) / max(1, m)))
                for j, i in enumerate(group):
                    y = body.cy + ((m - 1) / 2 - j) * (node_h + gy)
                    nodes[i][0].move_to([col_idx * (body.w / 2 - nw / 2 - 0.1), y, 0])
        c.play(FadeIn(cen, scale=0.85), sfx="card_pop.wav", rt=0.6)

        times = c.cue_times([b.exact_time for b in v.branches], start_offset=0.9)
        for (b, (node, h)), t in zip(zip(v.branches, nodes), times):
            col = c.color(b.color_theme)
            target = node.get_center()
            a = rect_edge_point(cen.get_center(), cen_w / 2, cen_h / 2, target)
            bb = rect_edge_point(target, nw / 2, h / 2, cen.get_center())
            link = Line(a, bb, stroke_width=3.5, color=col)
            c.at(t, Create(link), FadeIn(node, scale=0.85), sfx="pop.wav", rt=0.55)
        c.hold()
