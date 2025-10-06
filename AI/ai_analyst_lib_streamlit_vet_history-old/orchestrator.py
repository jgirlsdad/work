# orchestrator.py
import json, traceback
from typing import Any, Dict
from tool_registry import discover, save_catalog_json, call_tool

def build_runtime_catalog() -> str:
    discover("mylab")
    save_catalog_json()
    return "Catalog built."

def run_tool_call(call: Dict[str, Any]) -> Dict[str, Any]:
    try:
        out = call_tool(call["tool"], **call.get("kwargs", {}))
        return {"ok": True, "result": out}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}
