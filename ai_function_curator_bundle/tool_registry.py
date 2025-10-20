from dataclasses import dataclass, asdict
from typing import Callable, Any, Dict, List, Tuple
import importlib, pkgutil, json

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

def discover(package: str = "mylab") -> List[Tuple[str, str]]:
    pkg = importlib.import_module(package)
    failures: List[Tuple[str, str]] = []
    for _, modname, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        try:
            importlib.import_module(modname)
        except Exception as e:
            failures.append((modname, repr(e)))
    return failures

def get_catalog() -> Dict[str, Any]:
    return {k: asdict(v) for k, v in _REGISTRY.items()}
