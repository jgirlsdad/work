# proposer.py
"""
Helper for proposing new tools when the selected tool doesn't exist.
"""
import json
from typing import Dict, Any
from prompts import PLAN_PROMPT

NEW_TOOL_PROMPT = """You are to CREATE a new analysis tool function to fill a gap in the local library.
Constraints:
- Implement a SINGLE Python function named '{tool_name}'.
- Signature MUST match: {signature}
- DO NOT write arbitrary filesystem operations; only create outputs you return in a dict (e.g., CSV/PNG in CWD).
- Use only: pandas, numpy, matplotlib (optional), scikit-learn, statsmodels, math, statistics.
- If matplotlib import fails, skip plotting gracefully.
- No network, no os/subprocess/sys/shutil/socket/requests usage.
- Return a small dict of artifact paths or metrics.

DATASET CONTEXT:
{dataset_context}

ANALYSIS PLAN (JSON):
{plan_json}

Write ONLY the function definition (no extra text)."""

def build_new_tool_prompt(tool_name: str, signature: str, dataset_context: str, plan_json: str) -> str:
    return NEW_TOOL_PROMPT.format(tool_name=tool_name, signature=signature, dataset_context=dataset_context, plan_json=plan_json)