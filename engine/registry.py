"""
engine/registry.py
-------------------------------------------------------------------------
Component registry. A component = (Pydantic Spec + render() method).
Adding a new visual to the studio is ONE class in engine/components/:

    @register
    class MyThing(Component):
        name = "MyThing"
        description = "what it is for"
        class Spec(VisualSpec):
            component_type: Literal["MyThing"] = "MyThing"
            ...
        example = {...}
        def render(self): ...

The schema, the LLM prompt, the docs and the test gallery are all generated
from this registry, so nothing else has to be edited.
"""

from typing import Any, ClassVar, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, model_validator


class Cue(BaseModel):
    """Mixin: any item can be bound to a spoken word."""
    model_config = ConfigDict(extra="allow")
    trigger_keyword: str = ""          # word/phrase in the narration that triggers this item
    exact_time: Optional[float] = None  # filled by the compiler (absolute seconds)


class TextItem(Cue):
    """A list item. In JSON it can be a bare string or {"text": ..., "trigger_keyword": ...}."""
    text: str

    @model_validator(mode="before")
    @classmethod
    def _from_str(cls, data):
        return {"text": data} if isinstance(data, str) else data


class VisualSpec(Cue):
    component_type: str
    heading: str = ""
    subheading: str = ""


class Component:
    name: ClassVar[str]
    description: ClassVar[str] = ""
    best_for: ClassVar[str] = ""
    Spec: ClassVar[Type[VisualSpec]]
    example: ClassVar[Dict[str, Any]] = {}
    example_narration: ClassVar[str] = ""

    def __init__(self, ctx, spec):
        self.ctx = ctx
        self.v = spec

    def render(self) -> None:  # pragma: no cover
        raise NotImplementedError


REGISTRY: Dict[str, Type[Component]] = {}


def register(cls: Type[Component]) -> Type[Component]:
    REGISTRY[cls.name] = cls
    return cls


def load_components() -> Dict[str, Type[Component]]:
    """Import every module in engine.components so decorators run."""
    import importlib
    import pkgutil
    import engine.components as pkg

    for m in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"engine.components.{m.name}")
    return REGISTRY


def component_names() -> List[str]:
    return sorted(load_components().keys())
