# tool_registry.py
from dataclasses import dataclass, asdict
from typing import Callable, Any, Dict, List
import importlib, inspect, pkgutil, json

@dataclass
class ToolSpec:
    name: str
    path: str
    summary: str
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    tags: List[str]
    version: str = "1.0.0"

_REGISTRY: Dict[str, ToolSpec] = {}
_FUNCS: Dict[str, Callable[..., Any]] = {}

def tool(summary: str, inputs: Dict[str,str], outputs: Dict[str,str], tags: List[str], version="1.0.0"):
    def deco(fn: Callable[..., Any]):
        fqname = f"{fn.__module__}:{fn.__name__}"
        spec = ToolSpec(
            name=fn.__name__, path=fqname, summary=summary,
            inputs=inputs, outputs=outputs, tags=tags, version=version
        )
        _REGISTRY[fn.__name__] = spec
        _FUNCS[fn.__name__] = fn
        return fn
    return deco

def discover(package: str = "mylab") -> None:
    pkg = importlib.import_module(package)
    for _, modname, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        importlib.import_module(modname)

def get_catalog() -> Dict[str, Any]:
    return {k: asdict(v) for k, v in _REGISTRY.items()}

def call_tool(name: str, **kwargs):
    if name not in _FUNCS:
        raise KeyError(f"Unknown tool: {name}")
    sig = inspect.signature(_FUNCS[name])
    sig.bind_partial(**kwargs)
    return _FUNCS[name](**kwargs)

def save_catalog_json(path="tool_catalog.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(get_catalog(), f, indent=2)
