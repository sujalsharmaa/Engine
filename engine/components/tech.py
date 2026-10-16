"""Developer-oriented components: code window, terminal, crash dialog, hex inspector, B-tree."""

import math
from typing import List, Literal, Optional

import numpy as np
from manim import *  # noqa: F401,F403
from pydantic import AliasChoices, ConfigDict, Field

from engine.components._common import left_pack
from engine.registry import Component, Cue, VisualSpec, register
from engine.theme import ThemeColor
from engine.ui import code_lines_markup


def window_chrome(c, w, h, title, fill):
    win = c.card(w, h, "#334155", fill=fill, glow=True)
    dots = VGroup(Dot(radius=0.08, color="#FF5F56"), Dot(radius=0.08, color="#FFBD2E"), Dot(radius=0.08, color="#27C93F")
                  ).arrange(RIGHT, buff=0.14).move_to(win.get_corner(UL) + RIGHT * 0.65 + DOWN * 0.38)
    tt = c.T(title, 15, color=c.theme.dim, mono=True).move_to(win.get_top() + DOWN * 0.38)
    sep = Line(win.get_left() + UP * (h / 2 - 0.76), win.get_right() + UP * (h / 2 - 0.76), color="#1E293B", stroke_width=2)
    return VGroup(win, dots, tt, sep)


# ======================================================================
class CodeStep(Cue):
    lines: List[int]
    note: str = ""


@register
class MacOSCodeWindow(Component):
    name = "MacOSCodeWindow"
    description = "macOS-style editor window with real syntax highlighting, typing or line reveal, diff mode and step-by-step line spotlight with notes."
    best_for = "code explanations, snippets, diffs, config files, queries, one-liners"

    class Spec(VisualSpec):
        component_type: Literal["MacOSCodeWindow"] = "MacOSCodeWindow"
        filepath: str = "~/src/main.py"
        language: str = "python"
        code_lines: List[str]
        highlight_lines: List[int] = Field(default_factory=list)   # 1-based, lit from the start
        steps: List[CodeStep] = Field(default_factory=list)        # spotlight lines when spoken
        reveal: Literal["lines", "typing", "instant"] = "lines"
        diff: bool = False                                          # lines start with '+', '-' or ' '
        show_line_numbers: bool = True
        badge_text: Optional[str] = None

    example = {"component_type": "MacOSCodeWindow", "heading": "Retry with backoff", "filepath": "~/app/retry.py", "language": "python",
               "code_lines": ["def fetch(url):", "    for attempt in range(5):", "        try:", "            return http.get(url)", "        except Timeout:", "            sleep(2 ** attempt)"],
               "steps": [{"lines": [2], "note": "Try up to five times", "trigger_keyword": "five"},
                         {"lines": [6], "note": "Wait longer each time", "trigger_keyword": "longer"}],
               "badge_text": "Exponential backoff"}
    example_narration = "We try up to five times, and each failure waits longer than the last."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        raw = list(v.code_lines)
        markers = [None] * len(raw)
        if v.diff:
            for i, l in enumerate(raw):
                markers[i] = l[:1] if l[:1] in "+-" else " "
                raw[i] = l[1:]
        marks = code_lines_markup(raw, v.language)
        size = 17
        probe = Text("MMMMMMMMMM", font=c.mono, font_size=c.fs(size)) if c.mono else Text("MMMMMMMMMM", font_size=c.fs(size))
        cw = probe.width / 10
        note_h = 1.3 if any(s.note for s in v.steps) else 0
        win_w = body.w
        win_h = min(body.h - note_h - (0.2 if note_h else 0), max(3.2, len(raw) * 0.62 + 1.8))
        chrome = window_chrome(c, win_w, win_h, v.filepath, c.theme.code_bg)
        chrome.move_to([0, body.top - win_h / 2 - (0 if not note_h else 0), 0])
        win = chrome[0]

        rows = VGroup()
        for i, (m, txt) in enumerate(zip(marks, raw)):
            kw = dict(font_size=c.fs(size))
            if c.mono:
                kw["font"] = c.mono
            mt = MarkupText(m, **kw)
            indent = len(txt) - len(txt.lstrip(" "))
            lead = []
            if v.show_line_numbers:
                lead.append(Text(f"{i + 1:2d}", font_size=c.fs(size - 2), color="#475569", **({"font": c.mono} if c.mono else {})))
            if v.diff:
                mk = markers[i]
                lead.append(Text(mk, font_size=c.fs(size), color={"+": "#10B981", "-": "#F43F5E"}.get(mk, "#475569"), **({"font": c.mono} if c.mono else {})))
            row = VGroup(*lead, mt).arrange(RIGHT, buff=0.3, aligned_edge=ORIGIN)
            mt.shift(RIGHT * indent * cw)
            rows.add(row)
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        c.fit(rows, win_w - 0.3, win_h - 1.2, pad=0.1)
        rows.move_to(win.get_center() + DOWN * 0.3)
        rows.align_to(win, LEFT).shift(RIGHT * 0.45)
        step = rows[1].get_center()[1] - rows[0].get_center()[1] if len(rows) > 1 else -0.5
        rh = abs(step)

        def band(i, color, op):
            r = Rectangle(width=win_w - 0.3, height=rh * 1.05, fill_color=color, fill_opacity=op, stroke_width=0)
            r.move_to([win.get_center()[0], rows[i].get_center()[1], 0])
            return r

        bg_bands = VGroup()
        for i in range(len(rows)):
            if v.diff and markers[i] in ("+", "-"):
                bg_bands.add(band(i, "#10B981" if markers[i] == "+" else "#F43F5E", 0.16))
            elif (i + 1) in v.highlight_lines:
                bg_bands.add(band(i, c.accent, 0.2))

        c.play(FadeIn(chrome), FadeIn(bg_bands), sfx="whoosh_soft.wav", rt=0.6)
        span = max(1.0, min(c.dur * 0.35, 3.0))
        if v.reveal == "typing":
            per = max(0.2, span / len(rows))
            for r in rows:
                c.play(AddTextLetterByLetter(r[-1], time_per_char=min(0.03, per / max(8, len(r[-1])))), FadeIn(VGroup(*r[:-1])), rt=per)
                c.mark_sfx("tick.wav", db=-22)
        elif v.reveal == "instant":
            c.play(FadeIn(rows), rt=0.4)
        else:
            c.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.1) for r in rows], lag_ratio=0.12), rt=span)

        if v.badge_text:
            bt = c.T(v.badge_text, 14, bold=True, color=c.accent)
            badge = c.pack(bt.width + 0.6, 0.5, bt, c.accent, pad=0.05, glow=False)
            badge.move_to([win.get_right()[0] - badge.width / 2 - 0.3, win.get_top()[1] - 0.38, 0])
            c.play(FadeIn(badge, scale=0.85), sfx="card_pop.wav", rt=0.5)

        if v.steps:
            times = c.cue_times([s.exact_time for s in v.steps], start_offset=max(0.8, c.now - c.t0 + 0.3))
            active_band, note = None, None
            for s, t in zip(v.steps, times):
                idxs = [l - 1 for l in s.lines if 0 <= l - 1 < len(rows)]
                new_bands = VGroup(*[band(i, c.accent, 0.28) for i in idxs])
                anims = [FadeIn(new_bands)]
                anims += [rows[i].animate.set_opacity(1.0 if i in idxs else 0.35) for i in range(len(rows))]
                if active_band is not None:
                    anims.append(FadeOut(active_band))
                if note is not None:
                    anims.append(FadeOut(note))
                note = None
                if s.note:
                    nt = c.wrap(s.note, 20, body.w - 1.2, align=ORIGIN, bold=True)
                    note = c.pack(body.w, note_h, nt, c.accent, pad=0.2)
                    note.move_to([0, body.bottom + note_h / 2, 0])
                    anims.append(FadeIn(note, shift=UP * 0.2))
                c.at(t, *anims, sfx="pop.wav", rt=0.45)
                active_band = new_bands
            c.hold()
            return
        c.hold()


# ======================================================================
class TermLine(Cue):
    kind: Literal["command", "output", "error", "success", "comment"] = "output"
    text: str


@register
class TerminalTyping(Component):
    name = "TerminalTyping"
    description = "Terminal session: commands are typed with a prompt, outputs/errors/successes appear in colour."
    best_for = "CLI tutorials, DevOps demos, install steps, debugging sessions, git/docker/kubectl walk-throughs"

    class Spec(VisualSpec):
        component_type: Literal["TerminalTyping"] = "TerminalTyping"
        title: str = "bash"
        prompt: str = "$ "
        lines: List[TermLine]

    example = {"component_type": "TerminalTyping", "heading": "Spin up Prometheus", "title": "zsh — 80x24",
               "lines": [{"kind": "command", "text": "docker run -p 9090:9090 prom/prometheus", "trigger_keyword": "run"},
                         {"kind": "output", "text": "level=info msg=\"Server is ready to receive web requests.\""},
                         {"kind": "command", "text": "curl localhost:9090/metrics | head -2", "trigger_keyword": "curl"},
                         {"kind": "success", "text": "# HELP go_goroutines Number of goroutines"}]}
    example_narration = "Run the container, then curl the metrics endpoint to confirm it is serving data."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        n = len(v.lines)
        win_h = min(body.h, max(3.4, n * 0.62 + 1.6))
        chrome = window_chrome(c, body.w, win_h, v.title, "#070A12")
        chrome.move_to([0, body.top - win_h / 2, 0])
        win = chrome[0]
        colors = {"command": c.theme.text, "output": "#94A3B8", "error": "#F43F5E", "success": "#10B981", "comment": "#697098"}
        rows, cmds = VGroup(), {}
        for i, ln in enumerate(v.lines):
            if ln.kind == "command":
                p = c.T(v.prompt, 17, color=c.accent, bold=True, mono=True)
                t = c.T(ln.text, 17, color=colors["command"], mono=True)
                row = VGroup(p, t).arrange(RIGHT, buff=0.14)
                cmds[i] = (p, t)
            else:
                row = c.T(ln.text, 16, color=colors[ln.kind], mono=True)
            rows.add(row)
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        c.fit(rows, body.w - 0.4, win_h - 1.3, pad=0.1)
        rows.move_to(win.get_center() + DOWN * 0.3).align_to(win, LEFT).shift(RIGHT * 0.4)
        c.play(FadeIn(chrome), sfx="whoosh_soft.wav", rt=0.5)
        times = c.cue_times([l.exact_time for l in v.lines], start_offset=0.9, end_pad=1.2)
        cursor = Rectangle(width=0.14, height=0.3, fill_color=c.accent, fill_opacity=1, stroke_width=0)
        for i, (ln, t) in enumerate(zip(v.lines, times)):
            if i in cmds:
                p, tx = cmds[i]
                cursor.next_to(p, RIGHT, buff=0.05)
                c.at(t, FadeIn(p), FadeIn(cursor), rt=0.15)
                per = min(0.035, max(0.01, (c.end - c.now - 0.6) / max(1, len(ln.text)) / max(1, n - i)))
                c.play(AddTextLetterByLetter(tx, time_per_char=per), cursor.animate.next_to(tx, RIGHT, buff=0.05), rt=max(0.2, per * len(ln.text)))
                c.mark_sfx("tick.wav", db=-20)
                c.scene.remove(cursor)
            else:
                c.at(t, FadeIn(rows[i], shift=UP * 0.1), sfx="success.wav" if ln.kind == "success" else ("error.wav" if ln.kind == "error" else None), rt=0.25, db=-16)
        c.hold()


# ======================================================================
@register
class RetroCrashDialog(Component):
    name = "RetroCrashDialog"
    description = "Terminal with failing logs and a classic OS error dialog that wiggles, plus a red stamp. Dramatic 'it broke' moment."
    best_for = "failure hooks, outages, bugs, bottlenecks, 'what goes wrong' scenes"

    class Spec(VisualSpec):
        component_type: Literal["RetroCrashDialog"] = "RetroCrashDialog"
        heading: str = "Single Point of Failure"
        terminal_title: str = "system_daemon.exe"
        terminal_logs: List[str] = Field(default_factory=list)
        error_title: str = "System Error"
        error_message: str = "Cannot connect to server. Service is not responding."
        stamp_text: str = "CRITICAL BOTTLENECK"

    example = {"component_type": "RetroCrashDialog", "heading": "3 AM, Production", "error_title": "Collector Overload",
               "error_message": "50,000 agents pushing at once.", "stamp_text": "OUTAGE", "trigger_keyword": "crash"}
    example_narration = "When your servers crash at three AM, everything falls over at once."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        red = c.color("red")
        c.show_header(v, red)
        logs_txt = v.terminal_logs or ["[04:21:18] INFO  Connecting to 10.0.4.21:9088...",
                                       "[04:21:21] WARN  Timeout after 3000ms. Retrying...",
                                       "[04:21:24] FATAL Socket closed by remote host."]
        tw, th = body.w, min(body.h, 6.2 if c.portrait else 4.8)
        term = c.card(tw, th, "#334155", fill="#070A12", glow=False).move_to([0, body.top - th / 2, 0])
        logs = VGroup(*[c.T(l, 14, color="#64748B", mono=True) for l in logs_txt]).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        c.fit(logs, tw - 0.5, th * 0.35, pad=0.05)
        logs.move_to(term.get_top() + DOWN * (0.3 + logs.height / 2)).align_to(term, LEFT).shift(RIGHT * 0.3)

        mw = min(7.0, body.w - 0.6)
        mbg = RoundedRectangle(width=mw, height=2.7, corner_radius=0.08, fill_color="#D4D0C8", fill_opacity=1, stroke_color=WHITE, stroke_width=2.5)
        bar = Rectangle(width=mw - 0.1, height=0.46, fill_color="#0A246A", fill_opacity=1, stroke_width=0).move_to(mbg.get_top() + DOWN * 0.27)
        ttl = Text(v.error_title, font_size=c.fs(15), weight=BOLD, color=WHITE, **({"font": c.ui_font} if c.ui_font else {})).move_to(bar).align_to(bar, LEFT).shift(RIGHT * 0.2)
        icon = VGroup(Circle(radius=0.28, fill_color=red, fill_opacity=1, stroke_color=WHITE, stroke_width=2), c.T("✕", 18, bold=True, color="#FFFFFF"))
        icon[1].move_to(icon[0])
        msg = c.wrap(v.error_message, 17, mw - 1.7, bold=True, color="#111827")
        row = VGroup(icon, msg).arrange(RIGHT, buff=0.3).move_to(mbg.get_center() + UP * 0.1)
        btn = VGroup(Rectangle(width=1.3, height=0.44, fill_color="#D4D0C8", fill_opacity=1, stroke_color="#111827", stroke_width=1.5),
                     Text("Retry", font_size=c.fs(14), color="#111827", **({"font": c.ui_font} if c.ui_font else {}))).move_to(mbg.get_bottom() + UP * 0.45)
        btn[1].move_to(btn[0])
        modal = VGroup(mbg, bar, ttl, row, btn).move_to(term.get_center() + DOWN * 0.5)

        st = c.T(v.stamp_text, 22, bold=True, color=red)
        stamp = VGroup(RoundedRectangle(width=st.width + 0.7, height=st.height + 0.4, corner_radius=0.08, stroke_color=red, stroke_width=4), st.move_to(ORIGIN))
        stamp.rotate(-8 * DEGREES).next_to(modal, DOWN, buff=0.5)

        c.play(FadeIn(term), FadeIn(logs), rt=0.7)
        t = c.cue_times([v.exact_time], start_offset=1.2, end_pad=2.0)[0]
        c.at(t, FadeIn(modal, scale=0.85), sfx="error.wav", rt=0.4)
        c.play(Wiggle(modal, scale_value=1.03, rotation_angle=0.015 * TAU), rt=0.5)
        if v.stamp_text:
            c.play(FadeIn(stamp, scale=2.2), sfx="hit.wav", rt=0.25)
        c.hold()


# ======================================================================
class HexRow(Cue):
    offset: str
    bytes: List[str]
    ascii: str = ""


class HexHighlight(Cue):
    row: int
    col_start: int
    col_end: int            # inclusive
    label: str
    value_desc: str = ""
    color_theme: ThemeColor = "cyan"


@register
class HexMemoryInspector(Component):
    name = "HexMemoryInspector"
    description = "Hex dump grid; byte ranges are outlined and annotated with callout cards as they are explained."
    best_for = "file formats, headers, binary protocols, memory layout, packet structure"

    class Spec(VisualSpec):
        component_type: Literal["HexMemoryInspector"] = "HexMemoryInspector"
        subheading: str = "Binary Header Layout"
        rows: List[HexRow] = Field(default_factory=lambda: [
            HexRow(offset="0000:", bytes=["53", "51", "4C", "69", "74", "65", "20", "66"], ascii="SQLite f"),
            HexRow(offset="0008:", bytes=["6F", "72", "6D", "61", "74", "20", "33", "00"], ascii="ormat 3."),
            HexRow(offset="0010:", bytes=["10", "00", "01", "01", "00", "40", "20", "20"], ascii="Page 4096B"),
        ])
        highlights: List[HexHighlight]

    example = {"component_type": "HexMemoryInspector", "heading": "A 100-byte header", "highlights": [
        {"row": 0, "col_start": 0, "col_end": 7, "label": "Magic string", "value_desc": "SQLite format 3", "color_theme": "amber", "trigger_keyword": "magic"},
        {"row": 2, "col_start": 0, "col_end": 1, "label": "Page size", "value_desc": "4096 bytes", "color_theme": "cyan", "trigger_keyword": "page"}]}
    example_narration = "It starts with a magic string, then the page size tells the engine how big each page is."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        c.show_header(v)
        gw, gh = body.w, min(body.h * 0.55, 4.2)
        board = c.card(gw, gh, c.color("green"), fill="#060B11").move_to([0, body.top - gh / 2, 0])
        rows_g, cells = VGroup(), {}
        for ri, r in enumerate(v.rows):
            off = c.T(r.offset, 16, color=c.color("amber"), bold=True, mono=True)
            cg = VGroup()
            for ci, hx in enumerate(r.bytes):
                box = RoundedRectangle(width=0.58, height=0.48, corner_radius=0.06, fill_color="#0F172A", fill_opacity=0.9, stroke_color="#334155", stroke_width=1.2)
                tx = c.T(hx, 14, mono=True).move_to(box)
                grp = VGroup(box, tx)
                cells[(ri, ci)] = box
                cg.add(grp)
            cg.arrange(RIGHT, buff=0.07)
            parts = [off, cg] + ([c.T(r.ascii, 14, color=c.color("green"), mono=True)] if r.ascii and not c.portrait else [])
            rows_g.add(VGroup(*parts).arrange(RIGHT, buff=0.3))
        rows_g.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        c.fit(rows_g, gw - 0.4, gh - 0.4, pad=0.0)
        rows_g.move_to(board.get_center())
        c.play(FadeIn(board), FadeIn(rows_g), sfx="whoosh_soft.wav", rt=0.7)

        callouts = []
        cw_ = (body.w - 0.3 * (min(3, len(v.highlights)) - 1)) / min(3, len(v.highlights)) if not c.portrait else body.w
        ch_ = 1.5
        y_base = body.top - gh - 0.5
        times = c.cue_times([h.exact_time for h in v.highlights], start_offset=0.9)
        for k, (h, t) in enumerate(zip(v.highlights, times)):
            col = c.color(h.color_theme)
            cs = [cells[(h.row, i)] for i in range(h.col_start, h.col_end + 1) if (h.row, i) in cells]
            if not cs:
                continue
            outline = SurroundingRectangle(VGroup(*cs), color=col, buff=0.05, stroke_width=3.5, corner_radius=0.08)
            tint = [m.animate.set_fill(col, opacity=0.35) for m in cs]
            inner = VGroup(c.T(h.label, 18, bold=True, color=col), c.wrap(h.value_desc, 15, cw_ - 0.5, align=ORIGIN)).arrange(DOWN, buff=0.1)
            card = c.pack(cw_, ch_, inner, col, pad=0.15)
            if c.portrait:
                card.move_to([0, y_base - ch_ / 2 - (k % 3) * (ch_ + 0.25), 0])
            else:
                card.move_to([-body.w / 2 + cw_ / 2 + (k % 3) * (cw_ + 0.3), y_base - ch_ / 2 - (k // 3) * (ch_ + 0.2), 0])
            c.at(t, Create(outline), *tint, FadeIn(card, shift=UP * 0.2), sfx="card_pop.wav", rt=0.5)
        c.hold()


# ======================================================================
class BTreeNodeSpec(Cue):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    page_id: str
    keys_text: str
    subtext: str = ""
    level: int = 0                       # 0 = root, 1 = internal, 2 = leaf ...
    is_target_path: bool = Field(False, validation_alias=AliasChoices("is_target_path", "is_targetPath"))


@register
class BTreeCameraZoom(Component):
    name = "BTreeCameraZoom"
    description = "Tree / index structure by level with the lookup path highlighted step by step while the camera zooms along it."
    best_for = "B-trees, indexes, binary trees, decision trees, hierarchies, search paths, DNS resolution"

    class Spec(VisualSpec):
        component_type: Literal["BTreeCameraZoom"] = "BTreeCameraZoom"
        heading: str = "Logarithmic B-Tree Lookup"
        query_text: str = "SELECT * FROM metrics WHERE id = 42"
        nodes: List[BTreeNodeSpec]

    example = {"component_type": "BTreeCameraZoom", "heading": "Index lookup", "query_text": "WHERE id = 42", "nodes": [
        {"page_id": "Root", "keys_text": "10 | 50 | 90", "level": 0, "is_target_path": True, "trigger_keyword": "root"},
        {"page_id": "Page 20", "keys_text": "10 | 30", "level": 1},
        {"page_id": "Page 30", "keys_text": "40 | 45", "level": 1, "is_target_path": True, "trigger_keyword": "internal"},
        {"page_id": "Page 70", "keys_text": "90 | 100", "level": 1},
        {"page_id": "Leaf 42", "keys_text": "id = 42 ✓", "subtext": "O(log N)", "level": 2, "is_target_path": True, "trigger_keyword": "leaf"}]}
    example_narration = "Start at the root, hop to an internal page, and land on the leaf holding row forty two."

    def render(self):
        c, v = self.ctx, self.v
        body = c.region(bool(v.heading))
        green = c.color("green")
        banner = c.T(v.query_text, 22, bold=True, color=green, mono=True)
        c.fit(banner, body.w, 0.9, pad=0.05)
        banner.move_to([0, (c.header_y if v.heading else c.full.top), 0])
        c.play(FadeIn(banner, shift=DOWN * 0.2), sfx="whoosh_soft.wav", rt=0.5)

        levels = {}
        for i, nd in enumerate(v.nodes):
            levels.setdefault(nd.level, []).append(i)
        L = sorted(levels)
        area_top, area_bot = body.top - (0.3 if v.heading else 0.2), body.bottom
        lvl_h = (area_top - area_bot) / len(L)
        cards = {}
        for li, lv in enumerate(L):
            idxs = levels[lv]
            k = len(idxs)
            cw = min(3.4, (body.w - 0.3 * (k - 1)) / k)
            ch = min(1.5, lvl_h * 0.62)
            y = area_top - lvl_h * (li + 0.5)
            for j, ni in enumerate(idxs):
                nd = v.nodes[ni]
                col = c.color("cyan") if nd.is_target_path else "#334155"
                parts = [c.T(nd.page_id, 17, bold=True, color=c.theme.text if nd.is_target_path else c.theme.dim),
                         c.T(nd.keys_text, 15, color=c.color("cyan") if nd.is_target_path else c.theme.dim, mono=True)]
                if nd.subtext:
                    parts.append(c.T(nd.subtext, 12, color=c.theme.dim))
                card = c.pack(cw, ch, VGroup(*parts).arrange(DOWN, buff=0.07), col, pad=0.1, glow=nd.is_target_path)
                card.move_to([(j - (k - 1) / 2) * (cw + 0.3), y, 0])
                cards[ni] = (card, cw, ch)
        edges = VGroup()
        for li in range(1, len(L)):
            prev, cur = levels[L[li - 1]], levels[L[li]]
            for j, ni in enumerate(cur):
                pi = prev[min(len(prev) - 1, int(j * len(prev) / len(cur)))]
                a = cards[pi][0].get_bottom()
                b = cards[ni][0].get_top()
                path = v.nodes[ni].is_target_path and v.nodes[pi].is_target_path
                edges.add(Line(a, b, stroke_width=4 if path else 2, color=c.color("cyan") if path else "#334155"))
        everything = VGroup(*[cd[0] for cd in cards.values()])
        c.play(FadeIn(everything, lag_ratio=0.0, shift=UP * 0.2), Create(edges), sfx="card_pop.wav", rt=0.9)

        path_nodes = [i for i in sorted(cards, key=lambda i: v.nodes[i].level) if v.nodes[i].is_target_path]
        times = c.cue_times([v.nodes[i].exact_time for i in path_nodes], start_offset=max(1.0, c.now - c.t0 + 0.2), end_pad=1.4)
        frame = c.scene.camera.frame
        for ni, t in zip(path_nodes, times):
            card = cards[ni][0]
            c.at(t, Indicate(card, scale_factor=1.08, color=green),
                 frame.animate.move_to(card.get_center() * 0.6).set(height=c.H * 0.8), sfx="pop.wav", rt=0.7)
        c.play(frame.animate.move_to(ORIGIN).set(height=c.H), rt=0.5)
        c.hold()
