"""
engine/storyboard_compiler.py
-------------------------------------------------------------------------
Complete Pydantic Schema & Audio-Synced Storyboard Compiler supporting
8 ByteMonk-caliber components, 5 studio themes, and 16:9 / 9:16 aspect ratios.
"""

import json
from pathlib import Path
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

ThemeColor = Literal["cyan", "blue", "green", "red", "amber", "purple", "coral"]
StudioTheme = Literal["cyber_cyan", "monk_purple", "emerald_matrix", "crimson_alert", "solar_gold"]
AspectRatio = Literal["16:9", "9:16"]


# =====================================================================
# 1. THE 8 PROPRIETARY VISUAL COMPONENT SCHEMAS
# =====================================================================

class SceneHeroQuoteHook(BaseModel):
    component_type: Literal["HeroQuoteHook"] = "HeroQuoteHook"
    speaker_name: str
    speaker_role: str = ""
    quote_text: str
    highlight_phrase: str = ""
    year_badge: Optional[str] = None
    theme_color: ThemeColor = "purple"
    trigger_keyword: str = ""
    exact_time: float = 0.0


class TiltedCardItem(BaseModel):
    title: str
    value: str
    subtext: Optional[str] = None
    icon: str = "database"
    color_theme: ThemeColor = "cyan"
    is_hero: bool = False
    trigger_keyword: str = ""
    exact_time: float = 0.0


class SceneTiltedCards(BaseModel):
    component_type: Literal["TiltedCardComparison"] = "TiltedCardComparison"
    heading: str
    subheading: str = ""
    cards: List[TiltedCardItem]


class ArchNodeItem(BaseModel):
    node_id: str
    label: str
    sublabel: str = ""
    icon: str = "server"
    color_theme: ThemeColor = "cyan"
    trigger_keyword: str = ""
    exact_time: float = 0.0


class ArchEdgeItem(BaseModel):
    source: str
    target: str
    label: str = ""
    color_theme: ThemeColor = "cyan"
    is_blocked: bool = False


class SceneArchitectureFlow(BaseModel):
    component_type: Literal["ArchitectureFlowCanvas"] = "ArchitectureFlowCanvas"
    heading: str
    subheading: str = ""
    layout_mode: Literal["pipeline", "fan_out", "comparison_split"] = "pipeline"
    nodes: List[ArchNodeItem]
    edges: List[ArchEdgeItem] = Field(default_factory=list)


class SceneCodeWindow(BaseModel):
    component_type: Literal["MacOSCodeWindow"] = "MacOSCodeWindow"
    heading: str = ""
    filepath: str = "~/src/main.c"
    language: str = "c"
    code_lines: List[str]
    highlight_lines: List[int] = Field(default_factory=list)
    badge_text: Optional[str] = None
    trigger_keyword: str = ""
    exact_time: float = 0.0


class SceneRetroCrashDialog(BaseModel):
    component_type: Literal["RetroCrashDialog"] = "RetroCrashDialog"
    heading: str = "Single Point of Failure"
    terminal_title: str = "system_daemon.exe"
    terminal_logs: List[str] = Field(default_factory=list)
    error_title: str = "System Error"
    error_message: str = "Cannot connect to server. Service is not responding."
    stamp_text: str = "CRITICAL BOTTLENECK"
    trigger_keyword: str = ""
    exact_time: float = 0.0


class HexHighlightItem(BaseModel):
    row: int
    col_start: int
    col_end: int
    label: str
    value_desc: str
    color_theme: ThemeColor = "cyan"
    trigger_keyword: str = ""
    exact_time: float = 0.0


class SceneHexMemoryInspector(BaseModel):
    component_type: Literal["HexMemoryInspector"] = "HexMemoryInspector"
    heading: str
    subheading: str = "Binary Header Layout"
    ascii_preview: str = "SQLite format 3\\0"
    highlights: List[HexHighlightItem]


class BTreeNodeSpec(BaseModel):
    page_id: str
    keys_text: str
    subtext: str = ""
    level: int = 0  # 0 = Root, 1 = Internal, 2 = Leaf
    is_targetPath: bool = False


class SceneBTreeZoom(BaseModel):
    component_type: Literal["BTreeCameraZoom"] = "BTreeCameraZoom"
    heading: str = "Logarithmic B-Tree Lookup"
    query_text: str = "SELECT * FROM metrics WHERE id = 42"
    nodes: List[BTreeNodeSpec]
    trigger_keyword: str = ""
    exact_time: float = 0.0


class CarouselCardItem(BaseModel):
    title: str
    subtitle: str
    icon: str = "zap"
    color_theme: ThemeColor = "cyan"
    trigger_keyword: str = ""
    exact_time: float = 0.0


class SceneFeatureCarousel(BaseModel):
    component_type: Literal["FeatureCarouselCards"] = "FeatureCarouselCards"
    heading: str
    subheading: str = ""
    cards: List[CarouselCardItem]


SceneComponent = Union[
    SceneHeroQuoteHook,
    SceneTiltedCards,
    SceneArchitectureFlow,
    SceneCodeWindow,
    SceneRetroCrashDialog,
    SceneHexMemoryInspector,
    SceneBTreeZoom,
    SceneFeatureCarousel,
]


class VideoScene(BaseModel):
    scene_id: str
    narration_text: str
    start_time: float = 0.0
    end_time: float = 8.0
    visual: SceneComponent


class VideoStoryboard(BaseModel):
    title: str
    aspect_ratio: AspectRatio = "16:9"
    studio_theme: StudioTheme = "cyber_cyan"
    fps: int = 60
    scenes: List[VideoScene] = Field(default_factory=list)


# =====================================================================
# 2. THE AUDIO-SYNCED STORYBOARD COMPILER
# =====================================================================

class StoryboardCompiler:
    def __init__(self, timestamps_json_path: str = "word_timestamps.json"):
        self.words = []
        ts_path = Path(timestamps_json_path)
        if ts_path.exists():
            data = json.loads(ts_path.read_text(encoding="utf-8"))
            self.words = data.get("words", [])

    def find_word_time(self, keyword: str, min_time: float = 0.0) -> float:
        """Finds the first occurrence of `keyword` at or after `min_time`."""
        if not keyword or not self.words:
            return min_time
        kw = keyword.strip().lower()
        for item in self.words:
            w_start = float(item.get("start", 0.0))
            if w_start >= min_time and kw in item.get("word", "").strip().lower():
                return round(w_start, 3)
        return min_time

    def compile_storyboard(
        self,
        raw_llm_spec_path: str,
        output_path: str = "compiled_storyboard.json"
    ) -> VideoStoryboard:
        spec_path = Path(raw_llm_spec_path)
        if not spec_path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {spec_path}")

        raw_data = json.loads(spec_path.read_text(encoding="utf-8"))

        # Bind trigger keywords inside every scene to actual spoken timestamps
        cursor_time = 0.0
        for scene in raw_data.get("scenes", []):
            s_start = float(scene.get("start_time", cursor_time))
            visual = scene.get("visual", {})
            c_type = visual.get("component_type", "")

            if c_type == "TiltedCardComparison":
                for card in visual.get("cards", []):
                    card["exact_time"] = self.find_word_time(card.get("trigger_keyword", ""), s_start)
            elif c_type == "ArchitectureFlowCanvas":
                for node in visual.get("nodes", []):
                    node["exact_time"] = self.find_word_time(node.get("trigger_keyword", ""), s_start)
            elif c_type == "HexMemoryInspector":
                for hl in visual.get("highlights", []):
                    hl["exact_time"] = self.find_word_time(hl.get("trigger_keyword", ""), s_start)
            elif c_type == "FeatureCarouselCards":
                for c_item in visual.get("cards", []):
                    c_item["exact_time"] = self.find_word_time(c_item.get("trigger_keyword", ""), s_start)
            else:
                if "trigger_keyword" in visual:
                    visual["exact_time"] = self.find_word_time(visual.get("trigger_keyword", ""), s_start)

            cursor_time = float(scene.get("end_time", s_start + 6.0))

        storyboard = VideoStoryboard(**raw_data)
        out_file = Path(output_path)
        out_file.write_text(storyboard.model_dump_json(indent=2), encoding="utf-8")
        print(f"[+] Compiled {len(storyboard.scenes)} scenes ({storyboard.aspect_ratio}) -> {out_file.resolve()}")
        return storyboard