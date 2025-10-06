# AI Analyst Chatbot — Streamlit + Local Library

This project lets a chatbot (ChatGPT via OpenAI API) **decide the analysis** and then **run vetted local functions** from your own library instead of generating ad‑hoc code.

## Features
- Upload a CSV, describe your goal.
- Chatbot generates a **PLAN** (JSON rationale).
- Chatbot selects a **tool call** (JSON) from your local library (`mylab/`).
- Runner executes your vetted function and shows artifacts (plots/CSVs).
- Add more tools with `@tool` decorator; they’re auto-discovered.

## Quickstart
```bash
# 1) Create/activate your env, then install deps
python -m pip install -r requirements.txt

# 2) Set your OpenAI key
# Linux/macOS:
export OPENAI_API_KEY="sk-..."
# Windows PowerShell:
setx OPENAI_API_KEY "sk-..."

# 3) Launch the UI
streamlit run streamlit_app.py
```

## Files
- `streamlit_app.py` — Streamlit chatbot UI (PLAN → tool call → run).  
- `app.py` — CLI version (no UI).  
- `prompts.py` — PLAN & CODE prompt templates.  
- `tool_registry.py` — decorator + registry for your tools.  
- `orchestrator.py` — executes tool calls.  
- `mylab/` — starter tools (`eda.py`, `forecasting.py`, `util.py`).

## Add your own tools
Create functions in `mylab/*.py`, decorate with `@tool(summary=..., inputs=..., outputs=..., tags=...)`. Example in `mylab/eda.py`.

## Safety
The model never executes raw Python here. It returns **structured JSON** indicating which vetted function to call. You retain full control of the code that actually runs.
