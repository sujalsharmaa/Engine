"""
engine/schema.py
-------------------------------------------------------------------------
Top-level storyboard schema. Visual specs are validated against the
component registry, so a bad `component_type` or a missing field produces
a precise, human-readable error instead of a crash 10 minutes into a render.
"""

from typing import Any, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from engine.registry import REGISTRY, load_components
from engine.theme import THEMES

AspectRatio = Literal["16:9", "9:16", "1:1"]
Transition = Literal["fade", "slide", "zoom", "wipe", "cut"]
CameraMove = Literal["static", "push_in", "pull_out", "drift"]
CaptionStyle = Literal["off", "pop", "line"]


class VideoScene(BaseModel):
    model_config = ConfigDict(extra="allow")
    scene_id: str
    narration_text: str
    # Optional. In the default "auto" timing mode these are IGNORED and derived from the voiceover.
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    transition: Transition = "fade"
    camera: CameraMove = "push_in"
    visual: Any

    @field_validator("visual", mode="before")
    @classmethod
    def _validate_visual(cls, v):
        load_components()
        if hasattr(v, "component_type"):
            return v
        if not isinstance(v, dict):
            raise ValueError("visual must be an object")
        ctype = v.get("component_type")
        comp = REGISTRY.get(ctype)
        if comp is None:
            raise ValueError(f"unknown component_type {ctype!r}. Available: {', '.join(sorted(REGISTRY))}")
        return comp.Spec.model_validate(v)


class VideoStoryboard(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str = "Untitled"
    aspect_ratio: AspectRatio = "16:9"
    studio_theme: str = "cyber_cyan"
    fps: int = 30
    timing_mode: Literal["auto", "manual"] = "auto"
    captions: CaptionStyle = "pop"
    caption_color: str = "#FFFFFF"
    show_progress_bar: bool = True
    background: Literal["grid", "plain", "spotlight_only"] = "grid"
    scenes: List[VideoScene] = Field(default_factory=list)

    @field_validator("studio_theme")
    @classmethod
    def _theme_ok(cls, v):
        if v not in THEMES:
            raise ValueError(f"unknown studio_theme {v!r}. Available: {', '.join(THEMES)}")
        return v


def format_validation_error(err: ValidationError) -> str:
    lines = []
    for e in err.errors():
        loc = " -> ".join(str(x) for x in e["loc"])
        lines.append(f"  * {loc}: {e['msg']}")
    return "Storyboard validation failed:\n" + "\n".join(lines)


def collect_extras(model: Any, path: str = "") -> List[Tuple[str, str]]:
    """Return [(path, key)] for keys the schema does not know (likely LLM typos)."""
    out: List[Tuple[str, str]] = []
    if isinstance(model, BaseModel):
        for k in (model.model_extra or {}):
            out.append((path, k))
        for name in model.model_fields:
            out += collect_extras(getattr(model, name), f"{path}.{name}" if path else name)
    elif isinstance(model, list):
        for i, item in enumerate(model):
            out += collect_extras(item, f"{path}[{i}]")
    return out
