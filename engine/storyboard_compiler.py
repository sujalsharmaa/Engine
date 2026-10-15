"""
Step 2: The Storyboard Compiler & Pydantic Schema
-----------------------------------------------------------------
Defines the strict type-safe schema for your video components. 
The LLM output maps script text to structured visual commands, 
synchronizing with the audio timestamps from Step 1.
"""

import json
from pathlib import Path
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field


# =====================================================================
# 1. VISUAL COMPONENT SCHEMAS (Your Proprietary Moat Primitives)
# =====================================================================

class TiltedCardItem(BaseModel):
    title: str
    value: str
    subtext: Optional[str] = None
    color_theme: Literal["cyan", "blue", "green", "red", "amber"] = "cyan"
    is_hero: bool = False
    trigger_keyword: str  # The spoken word that snaps this card into view


class SceneTiltedCards(BaseModel):
    component_type: Literal["TiltedCardComparison"] = "TiltedCardComparison"
    heading: str
    subheading: str
    cards: List[TiltedCardItem]


class SceneCodeWindow(BaseModel):
    component_type: Literal["MacOSCodeWindow"] = "MacOSCodeWindow"
    filepath: str
    code_snippet: str
    highlight_lines: List[int] = Field(default_factory=list)


class SceneBTreeZoom(BaseModel):
    component_type: Literal["BTreeCameraZoom"] = "BTreeCameraZoom"
    query_text: str
    target_page: int
    focus_nodes: List[str] = Field(default_factory=list)


# A union of all available component types in your custom studio engine
SceneComponent = Union[SceneTiltedCards, SceneCodeWindow, SceneBTreeZoom]


class VideoScene(BaseModel):
    scene_id: str
    narration_text: str
    start_time: float
    end_time: float
    visual: SceneComponent


class VideoStoryboard(BaseModel):
    title: str
    fps: int = 60
    resolution: tuple = (1920, 1080)
    scenes: List[VideoScene] = Field(default_factory=list)


# =====================================================================
# 2. THE STORYBOARD COMPILER ENGINE
# =====================================================================

class StoryboardCompiler:
    def __init__(self, timestamps_json_path: str = "word_timestamps.json"):
        ts_path = Path(timestamps_json_path)
        if not ts_path.exists():
            raise FileNotFoundError(f"Timestamp file missing: {ts_path}. Run Step 1 first!")
        
        with open(ts_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.words = data.get("words", [])

    def find_word_time(self, keyword: str) -> float:
        """Helper to match a keyword to its exact timestamp from Step 1 data."""
        kw = keyword.strip().lower()
        for item in self.words:
            if kw in item["word"].strip().lower():
                return float(item["start"])
        return 0.0

    def compile_storyboard(self, raw_llm_spec_path: str, output_path: str = "compiled_storyboard.json") -> VideoStoryboard:
        """
        Takes raw blueprint input, injects precise millisecond timestamps 
        from the audio alignment data, and validates via Pydantic.
        """
        spec_path = Path(raw_llm_spec_path)
        if not spec_path.exists():
            raise FileNotFoundError(f"LLM spec blueprint not found: {spec_path}")

        raw_data = json.loads(spec_path.read_text(encoding="utf-8"))
        
        # Post-process scenes to auto-bind keyword triggers to actual audio times
        for scene in raw_data.get("scenes", []):
            visual = scene.get("visual", {})
            if visual.get("component_type") == "TiltedCardComparison":
                for card in visual.get("cards", []):
                    kw = card.get("trigger_keyword", "")
                    # Automatically update card timing from audio alignment
                    card["exact_time"] = self.find_word_time(kw)

        # Validate everything through Pydantic
        storyboard = VideoStoryboard(**raw_data)
        
        out_file = Path(output_path)
        out_file.write_text(storyboard.model_dump_json(indent=2), encoding="utf-8")
        print(f"[+] Storyboard successfully compiled and validated! Saved to {out_file.resolve()}")
        
        return storyboard


# --- Example Local Test ---
if __name__ == "__main__":
    # 1. Create a sample LLM blueprint file to demonstrate compilation
    sample_blueprint = {
        "title": "SQLite vs Traditional Databases",
        "scenes": [
            {
                "scene_id": "scene_database_scale",
                "narration_text": "While MySQL has 5 million and Postgres has 1 million, SQLite hits 1 trillion deployments.",
                "start_time": 25.0,
                "end_time": 40.0,
                "visual": {
                    "component_type": "TiltedCardComparison",
                    "heading": "Database Deployment Scale",
                    "subheading": "Comparing active production installations",
                    "cards": [
                        {"title": "MySQL", "value": "5M", "color_theme": "cyan", "trigger_keyword": "million"},
                        {"title": "PostgreSQL", "value": "1M", "color_theme": "blue", "trigger_keyword": "postgres"},
                        {"title": "SQLite", "value": "1T", "subtext": "Active deployments", "color_theme": "green", "is_hero": True, "trigger_keyword": "trillion"}
                    ]
                }
            }
        ]
    }
    
    blueprint_path = Path("sample_blueprint.json")
    blueprint_path.write_text(json.dumps(sample_blueprint, indent=2))

    try:
        compiler = StoryboardCompiler("word_timestamps.json")
        compiler.compile_storyboard("sample_blueprint.json")
    except FileNotFoundError as e:
        print(f"[-] Note: {e} (Make sure word_timestamps.json exists from Step 1).")