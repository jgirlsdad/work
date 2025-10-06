# prompts.py
PLAN_PROMPT = """You are a senior data analyst. First decide WHAT to do before coding.
Return ONLY JSON with:
{
  "task_type": "eda|regression|classification|forecasting|clustering",
  "target": "str|null",
  "candidates": [ {"method":"...", "why":"...", "library_tool":"<preferred_tool_name_or_null>"} ],
  "choice": {"method":"...", "why":"...", "library_tool":"<tool_or_null>"},
  "inputs_needed": {"date_col":"... (if ts)", "exog_cols":"[...] (if any)", "notes":"..."}
}
Prefer existing library tools when available. If no exact match, choose the closest tool + minimal glue code.
"""

CODE_PROMPT = """Use the PLAN and the tool catalog below. Your job is to PRODUCE A SINGLE JSON CALL that the runner will execute.
Rules:
- If PLAN.choice.library_tool is not null, produce: {"tool": "<name>", "kwargs": {...}} with concrete kwarg values.
- kwarg values must reference columns exactly as they appear.
- Do NOT emit raw Python; only the JSON call.

CATALOG (JSON):
{catalog_json}

PLAN (JSON):
{plan_json}

Return ONLY one line of JSON with the tool call.
"""
