# streamlit_app.py
import os, json, re, io, traceback
from typing import Optional, Dict, Any, List
import streamlit as st
import pandas as pd
import time, os, json
from pathlib import Path
# Local imports
from tool_registry import discover, get_catalog
from orchestrator import run_tool_call
from prompts import PLAN_PROMPT, CODE_PROMPT
from safety import lint_proposed_code, sandbox_test_tool
from proposer import build_new_tool_prompt

# --- OpenAI client helper ---
def get_openai_client(api_key: str):
    try:
        from openai import OpenAI
    except Exception as e:
        st.error("OpenAI library missing. Install with:  pip install openai")
        st.stop()
    os.environ["OPENAI_API_KEY"] = api_key
    return OpenAI()

def chat_complete(client, model: str, system: str, user: str, temperature: float = 0.2) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=temperature,
    )
    return resp.choices[0].message.content

# --- UI ---
st.set_page_config(page_title="AI Analyst Chatbot", page_icon="🤖", layout="wide")
st.title("🤖 AI Analyst Chatbot — Streamlit + Local Library")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4.1"], index=0)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
    st.caption("Tip: set the OPENAI_API_KEY env var to avoid pasting each time.")
    st.markdown("---")
    st.header("Run Controls")
    do_gen_plan = st.button("1) Generate PLAN")
    do_choose_tool = st.button("2) Choose Tool (JSON call)")
    do_run = st.button("3) Run Tool")
    all_in = st.button("Analyze & Run (1→3)")

uploaded = st.file_uploader("Upload a CSV", type=["csv"])
goal = st.text_area("Describe your analysis goal", placeholder="e.g., Forecast next 6 months of VPD using lagged features F1..F6")

df: Optional[pd.DataFrame] = None
if uploaded is not None:
    try:
        df = pd.read_csv(uploaded)
        st.success(f"Loaded CSV: **{uploaded.name}** with shape {df.shape}")
        with st.expander("Preview / Schema", expanded=False):
            st.dataframe(df.head(20))
            schema_text = df.dtypes.to_frame("dtype").to_string()
            st.code(schema_text, language="text")
    except Exception as e:
        st.error(f"Failed to read CSV: {e}")

# session state
if "plan_text" not in st.session_state:
    st.session_state.plan_text = ""
if "tool_call_text" not in st.session_state:
    st.session_state.tool_call_text = ""

# Validate key if actions
if (do_gen_plan or do_choose_tool or do_run or all_in) and not api_key:
    st.warning("Please provide your OpenAI API Key in the sidebar.")
    st.stop()

# Discover tools & catalog
try:
    discover("mylab")
    catalog_json = json.dumps(get_catalog(), indent=2)
except Exception as e:
    st.error("Error discovering local tools. Ensure the 'mylab' package exists.")
    st.exception(e)
    st.stop()

# Helper to show artifacts
def show_artifacts(result: Dict[str, Any]):
    st.subheader("Run Result")
    if not result.get("ok"):
        st.error("Tool execution failed.")
        st.code(result.get("error",""), language="text")
        with st.expander("Traceback"):
            st.code(result.get("traceback",""), language="text")
        return
    st.success("Tool executed successfully.")
    out = result.get("result", {})
    # Heuristics: show known keys/paths
    for k, v in out.items():
        if isinstance(v, str) and v.lower().endswith(".csv"):
            try:
                df_art = pd.read_csv(v)
                st.markdown(f"**{k}** — {v}")
                st.dataframe(df_art.head(50))
                st.download_button(f"Download {v}", data=open(v, "rb").read(), file_name=v, mime="text/csv")
            except Exception:
                st.code(f"{k}: {v}")
        elif isinstance(v, str) and v.lower().endswith((".png",".jpg",".jpeg",".webp",".svg")):
            st.markdown(f"**{k}** — {v}")
            st.image(v)
            st.download_button(f"Download {v}", data=open(v, "rb").read(), file_name=v)
        else:
            # print simple values or nested dicts
            st.code(f"{k}: {v}", language="json" if isinstance(v, (dict, list)) else "text")

# Driver
client = get_openai_client(api_key) if (api_key and (do_gen_plan or do_choose_tool or all_in)) else None

# 1) Generate PLAN
if do_gen_plan or all_in:
    if df is None or not goal.strip():
        st.warning("Upload a CSV and enter a goal first.")
    else:
        schema_text = df.dtypes.to_frame("dtype").to_string()
        user_prompt = f"DATA SCHEMA (dtypes)\n{schema_text}\n\nGOAL:\n{goal}\n\n{PLAN_PROMPT}"
        with st.spinner("Calling ChatGPT for PLAN..."):
            plan_text = chat_complete(client, model, "You are a careful planner; do not produce code.", user_prompt, temperature)
        st.session_state.plan_text = plan_text
        st.subheader("PLAN (model output)")
        st.code(plan_text, language="json")

# 2) Choose Tool (JSON call)
if do_choose_tool or all_in:
    if not st.session_state.plan_text.strip():
        st.warning("Generate a PLAN first.")
    else:
        plan_json = st.session_state.plan_text.strip()
        user_prompt = CODE_PROMPT.format(catalog_json=catalog_json, plan_json=plan_json)
        with st.spinner("Asking ChatGPT to select a library tool (JSON call)..."):
            tool_call_text = chat_complete(client, model, "Output only one JSON line describing which library tool to call.", user_prompt, temperature)
        st.session_state.tool_call_text = tool_call_text.strip()
        st.subheader("Tool Call (JSON)")
        st.code(st.session_state.tool_call_text, language="json")

# 3) Run Tool
if do_run or all_in:
    if not st.session_state.tool_call_text.strip():
        st.warning("Choose a tool first.")
    else:
        try:
            call = json.loads(st.session_state.tool_call_text)
        except Exception:
            # extract last JSON-ish block
            m = re.search(r"\{[\s\S]*\}$", st.session_state.tool_call_text.strip(), re.MULTILINE)
            if not m:
                st.error("Could not parse tool call JSON.")
                st.stop()
            call = json.loads(m.group(0))

        # Inject dataframe if requested
        kwargs = call.get("kwargs", {})
        if isinstance(kwargs.get("df"), str) and kwargs["df"] == "__DATAFRAME__":
            if df is None:
                st.error("No DataFrame available. Upload a CSV.")
                st.stop()
            call["kwargs"]["df"] = df

        with st.spinner(f"Running tool: {call.get('tool')} ..."):
            result = run_tool_call(call)

        # --- Append to run history ---
        try:
           
            hist_dir = Path("runs"); hist_dir.mkdir(parents=True, exist_ok=True)
            hist_path = hist_dir / "history.jsonl"
            record = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "dataset": getattr(uploaded, "name", None),
                "goal": goal,
                "model": model,
                "tool_call": call,
                "ok": bool(result.get("ok")),
                "result_keys": list((result.get("result") or {}).keys()),
                "error": (result.get("error") if not result.get("ok") else None)
            }
            with open(hist_path, "a", encoding="utf-8") as hf:
                hf.write(json.dumps(record, default=str) + "\n")
        except Exception as _e:
            pass

        show_artifacts(result)

st.markdown("---")
st.header("📜 Run History")

colH1, colH2, colH3 = st.columns([1,1,1])
with colH1:
    hist_refresh = st.button("Refresh History")
with colH2:
    hist_clear = st.button("Clear History")
with colH3:
    st.download_button("Download History (.jsonl)", data=open("runs/history.jsonl","rb").read() if Path("runs/history.jsonl").exists() else b"", file_name="history.jsonl")

if hist_clear:
    from pathlib import Path
    hp = Path("runs/history.jsonl")
    if hp.exists():
        hp.unlink()
    st.success("History cleared.")

# Show table
from pathlib import Path
hp = Path("runs/history.jsonl")
rows = []
if hp.exists():
    with open(hp, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except:
                pass

if rows:
    import pandas as _pd
    # summarize for display
    disp = []
    for r in rows[-200:]:
        disp.append({
            "Time": r.get("ts"),
            "Dataset": r.get("dataset") or "(unknown)",
            "Goal": (r.get("goal") or "")[:80] + ("…" if r.get("goal") and len(r.get("goal"))>80 else ""),
            "Model": r.get("model"),
            "Tool": (r.get("tool_call") or {}).get("tool"),
            "OK": r.get("ok"),
            "Artifacts/Keys": ", ".join(r.get("result_keys") or []),
            "Error?": (r.get("error") or "")[:80] + ("…" if r.get("error") and len(r.get("error"))>80 else ""),
        })
    st.dataframe(_pd.DataFrame(disp))
else:
    st.info("No runs logged yet.")


# Sample data helper
st.markdown("---")
st.subheader("📂 Sample Dataset")
st.write("Use this small monthly sample to try the app quickly.")
try:
    import pandas as _pd
    _sdf = _pd.read_csv("data/sample_vpd.csv")
    st.dataframe(_sdf.head(12))
    st.download_button("Download sample_vpd.csv", data=open("data/sample_vpd.csv","rb").read(), file_name="sample_vpd.csv", mime="text/csv")
except Exception as e:
    st.warning("Sample dataset not found.")


# =====================
# Propose → Vet → Approve Flow
# =====================
st.header("💡 Propose & Vet New Tool (when missing)")

with st.expander("When the chosen tool doesn't exist, draft it, test in sandbox, then approve to add to library.", expanded=False):
    tool_name = st.text_input("New tool function name (e.g., regression_baseline)")
    signature = st.text_input("Required signature (e.g., \"def regression_baseline(df: pd.DataFrame, target: str) -> dict:\")")
    gen_draft = st.button("Draft Tool Code")
    code_area = st.text_area("Proposed Tool Code (editable)", height=260, key="proposed_code_area")
    lint_btn = st.button("Run Safety Lint")
    test_btn = st.button("Test in Sandbox")
    approve_btn = st.button("Approve & Add to Library")

    # Prepare dataset context for prompting
    dataset_context = ""
    if 'df' in locals() and df is not None:
        try:
            dataset_context = f"Shape: {df.shape}\nDtypes:\n{df.dtypes.to_string()}\nHead:\n{df.head(5).to_string()}"
        except Exception:
            pass

    if gen_draft:
        if not api_key:
            st.warning("Add your OpenAI API key in the sidebar.")
        elif not tool_name or not signature:
            st.warning("Provide a tool name and signature.")
        elif not st.session_state.get("plan_text", "").strip():
            st.warning("You need a PLAN first (Step 1).")
        else:
            client = get_openai_client(api_key)
            prompt = build_new_tool_prompt(
                tool_name=tool_name,
                signature=signature,
                dataset_context=dataset_context or "(no preview available)",
                plan_json=st.session_state["plan_text"].strip()
            )
            with st.spinner("Asking ChatGPT to draft the new tool..."):
                code_text = chat_complete(client, model, "Write only the function definition. Follow constraints strictly.", prompt, temperature)
            st.session_state["proposed_code_area"] = code_text
            st.experimental_rerun()

    # Keep textarea synced with session
    if "proposed_code_area" in st.session_state and not code_area:
        st.session_state["proposed_code_area"] = st.session_state["proposed_code_area"]
        st.experimental_rerun()

    if lint_btn:
        code_text = st.session_state.get("proposed_code_area", "").strip()
        if not code_text:
            st.warning("No code to lint.")
        else:
            ok, issues = lint_proposed_code(code_text)
            if ok:
                st.success("Lint passed (no blocking issues). See notes/warnings below.")
            else:
                st.error("Lint FAILED (dangerous constructs detected).")
            if issues:
                st.code("\n".join(issues), language="text")
            else:
                st.write("No issues.")

    if test_btn:
        code_text = st.session_state.get("proposed_code_area", "").strip()
        if not code_text:
            st.warning("No code to test.")
        else:
            # Guess kwargs from signature minimally; let user enter JSON overrides
            default_kwargs = {}
            kwargs_json = st.text_area("Sandbox kwargs (JSON)", value=json.dumps(default_kwargs), key="kwargs_json")
            try:
                kwargs = json.loads(kwargs_json) if kwargs_json else {}
            except Exception as e:
                st.error(f"Invalid kwargs JSON: {e}")
                kwargs = {}

            # If df is part of kwargs and user did not provide it, auto-inject
            if "df" in (signature or "") and "df" not in kwargs:
                if 'df' in locals() and df is not None:
                    kwargs["df"] = df
                else:
                    st.warning("Signature expects 'df', but no DataFrame available. Upload a CSV.")
                    kwargs = kwargs

            with st.spinner("Running in sandbox..."):
                result = sandbox_test_tool(code_text, tool_name, kwargs, timeout=25)
            if result.get("ok"):
                st.success("Sandbox run succeeded.")
                st.code(json.dumps(result.get("result"), indent=2), language="json")
            else:
                st.error("Sandbox run failed.")
                st.code(result.get("stdout","") or "(no stdout)", language="text")
                if result.get("stderr"):
                    st.code(result["stderr"], language="text")

    if approve_btn:
        code_text = st.session_state.get("proposed_code_area", "").strip()
        if not code_text or not tool_name:
            st.warning("Provide tool name and code before approving.")
        else:
            # Save into mylab/_proposed/<tool_name>.py and also into mylab/ so it becomes discoverable
            proposed_dir = Path("mylab/_proposed")
            proposed_dir.mkdir(parents=True, exist_ok=True)
            dest = proposed_dir / f"{tool_name}.py"
            # Ensure it has @tool decorator import; if missing, wrap minimally
            if "@tool" not in code_text:
                # Wrap bare function with a default decorator metadata
                wrapped = f"from tool_registry import tool\nimport pandas as pd, numpy as np\n\n@tool(summary='Proposed tool', inputs={{}}, outputs={{}}, tags=['proposed'])\n{code_text.strip()}\n"
                code_text = wrapped
            dest.write_text(code_text, encoding="utf-8")
            # Also mirror into mylab/ root with same name
            official = Path("mylab") / f"{tool_name}.py"
            official.write_text(code_text, encoding="utf-8")
            st.success(f"Saved and registered as mylab/{tool_name}.py. Use 'Analyze & Run' to rediscover and use it.")
