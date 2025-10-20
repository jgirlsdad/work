import sys, os, re, json, importlib.util as iul
from pathlib import Path
from typing import List, Dict, Any, Optional
import inspect, importlib
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

import streamlit as st
from openai import OpenAI

from tool_registry import discover, get_catalog
from safety import lint_proposed_code, sandbox_test_function

st.set_page_config(page_title="AI Function Curator", page_icon="🧰", layout="wide")
st.title("🧰 AI Function Curator — Build & Vet Analytics Functions")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY",""))
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4.1"], index=0)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
    st.caption("Sandbox tests run in a temporary folder; your project files are untouched.")


def get_client():
    os.environ["OPENAI_API_KEY"] = api_key
    return OpenAI()


def chat_complete(system: str, user: str) -> str:
    client = get_client()
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
        # Safely extract text from all possible structures
        choice = resp.choices[0]
        if hasattr(choice, "message"):
            content = getattr(choice.message, "content", None)
        elif isinstance(choice, dict) and "message" in choice:
            content = choice["message"].get("content")
        else:
            content = None

        # Handle markdown code fences
        if content and content.strip().startswith("```python"):
            content = content.strip().strip("`python").strip("`").strip()

        if not content:
            st.warning("⚠️ AI returned an empty message. Check your model or API key access.")
            st.code(str(resp), language="text")
            return ""
        print("Content", content)
        return content
    except Exception as e:
        st.error(f"❌ OpenAI API call failed: {e}")
        return ""


# ===============================================================
# 1) Describe the function you want
# ===============================================================
st.subheader("1) Describe the function you want")
idea = st.text_area("What should it do? Inputs/outputs? Edge cases?", 
    placeholder="Example: Weighted rolling correlation with handling for NaNs and irregular timestamps."
)

# ===============================================================
# 2) Check local library (mylab)
# ===============================================================
st.subheader("2) Check local library (mylab)")
local_failures = []
catalog_json = "{}"
try:
    local_failures = discover("mylab")
    catalog = get_catalog()
    catalog_json = json.dumps(catalog, indent=2)
    if local_failures:
        st.warning("Some local modules failed to import:")
        for m, err in local_failures:
            st.code(f"{m}: {err}")
except Exception as e:
    st.error("Could not import 'mylab'. Ensure it exists and is importable.")
    st.exception(e)

query = st.text_input("Keyword search (optional)", "")
if st.button("Search Local Tools"):
    if not catalog_json or catalog_json == "{}":
        st.info("No tools registered yet.")
    else:
        q = query.strip().lower()
        matches = []
        for name, spec in json.loads(catalog_json).items():
            hay = " ".join([name, spec.get("summary",""), " ".join(spec.get("tags",[]))]).lower()
            if not q or q in hay:
                matches.append((name, spec))
        if matches:
            st.success(f"Found {len(matches)} tool(s).")
            for name, spec in matches:
                st.markdown(f"### 🧩 **{name}** — {spec.get('summary','(no summary)')}")
                st.code(json.dumps(spec, indent=2), language="json")

                # Try to load and show source code
                try:
                    mod_path, func_name = spec["path"].split(":")
                    mod = importlib.import_module(mod_path)
                    fn = getattr(mod, func_name)
                    src = inspect.getsource(fn)
                    st.code(src, language="python")
                    st.caption(f"📂 File: {mod.__file__}")
                except Exception as e:
                    st.warning(f"Could not load source for {name}: {e}")
        else:
            st.info("No matches found.")


# ===============================================================
# 3) External Python packages that may already do this
# ===============================================================
st.subheader("3) External Python packages that may already do this")
if st.button("Suggest existing libraries / functions"):
    if not api_key:
        st.warning("Add your OpenAI API key in the sidebar.")
    elif not idea.strip():
        st.warning("Describe your function first.")
    else:
        system = "You are an expert Python data scientist and librarian. Be concise and practical."
        user = f"""The user wants to implement a function:\n{idea}\n\nList up to 5 existing Python packages or built-ins that already implement this. For each: package.function, why relevant, caveats. Return a numbered list."""
        with st.spinner("Asking GPT..."):
            suggestions = chat_complete(system, user)
        st.code(suggestions, language="markdown")


# ===============================================================
# 4) Generate draft function
# ===============================================================
st.subheader("4) Generate draft function")
colA, colB = st.columns([1, 1])
with colA:
    fname = st.text_input("Function name", value="new_analysis_function")
with colB:
    sig_hint = st.text_input("Signature hint (optional)",
        placeholder="def new_analysis_function(df: pd.DataFrame, col: str, window:int) -> dict:")

# Initialize session key once
if "draft_code_area" not in st.session_state:
    st.session_state["draft_code_area"] = ""

if st.button("Generate Draft"):
    if not api_key:
        st.warning("Add your OpenAI API key in the sidebar.")
    elif not idea.strip():
        st.warning("Describe your function first.")
    elif not fname.strip():
        st.warning("Provide a function name.")
    else:
        system = "You are a senior Python data scientist. Write clean, production-ready functions."
        user = f'''
Write a SINGLE Python function named "{fname}". Follow these rules:
- Put ALL imports at the TOP of the file.
- Allowed libs only: pandas, numpy, matplotlib (optional), scikit-learn, statsmodels, math, statistics.
- If matplotlib import fails at runtime, handle gracefully (skip plots).
- No network, no os/subprocess/sys/shutil/socket/requests usage.
- Include a precise docstring with args/returns/examples.
- Validate inputs and handle NaNs robustly.
- Return a small dict or DataFrame.
- Keep under ~120 lines.
- Do NOT decorate or register anything.

Desired functionality:
{idea}

Signature hint (optional):
{sig_hint or "(none)"}

Return only the function definition.
'''
        with st.spinner("Asking GPT to draft..."):
            draft = chat_complete(system, user)

        draft_clean = (draft or "").strip()
        if draft_clean.startswith("```python"):
            draft_clean = draft_clean.removeprefix("```python").removesuffix("```").strip()
        elif draft_clean.startswith("```"):
            draft_clean = draft_clean.strip("`").strip()

        st.session_state["draft_code_area"] = draft_clean
        st.success("✅ Draft generated successfully!")

# --- Single unified text area (no duplicate key error) ---
st.text_area(
    "Draft function (editable)",
    value=st.session_state["draft_code_area"],
    height=300,
    key="draft_code_area"
)


# ===============================================================
# 5) Lint & Run Test (manual, sandbox temp dir)
# ===============================================================
# ===============================================================
# 5) Lint & Run Test (manual, sandbox temp dir)
# ===============================================================
# ===============================================================
# 5) Lint & Run Test (manual, sandbox temp dir)
# ===============================================================
st.subheader("5) Lint & Run Test (manual, sandbox temp dir)")

if st.button("Run Safety Lint"):
    code_text = st.session_state.get("draft_code_area", "").strip()
    if not code_text:
        st.warning("No code to lint.")
    else:
        ok, issues = lint_proposed_code(code_text)
        (st.success if ok else st.error)("Lint " + ("passed" if ok else "FAILED"))
        if issues:
            st.code("\n".join(issues), language="text")

# --- Known test file path box ---
DEFAULT_TEST_FILE = Path("data/sample_test.csv")

test_file_path = st.text_input(
    "Path to test CSV file (default = data/sample_test.csv)",
    str(DEFAULT_TEST_FILE)
)

if not Path(test_file_path).exists():
    st.error(f"❌ Test file not found: {test_file_path}")
    st.info("Please ensure your known sample test dataset exists at that location.")
else:
    st.success(f"✅ Using test dataset: {test_file_path}")

# --- JSON kwargs input ---
kwargs_text = st.text_area(
    "kwargs JSON for test (optional, overrides defaults)",
    value="{}",
    height=120
)

if st.button("Run Test in Sandbox"):
    code_text = st.session_state.get("draft_code_area", "").strip()
    if not code_text:
        st.warning("No code to run.")
    else:
        try:
            kwargs = json.loads(kwargs_text) if kwargs_text.strip() else {}
        except Exception as e:
            st.error(f"Invalid kwargs JSON: {e}")
            kwargs = {}

        # Always use known test file unless user provides one
        if "csv_file" not in kwargs:
            kwargs["csv_file"] = str(Path(test_file_path).resolve())

        with st.spinner(f"Running in sandbox with {kwargs['csv_file']}..."):
            try:
                result = sandbox_test_function(code_text, fname, kwargs, timeout=25)
            except Exception as e:
                st.error(f"❌ Sandbox execution crashed: {e}")
                st.stop()

        # Normalize and display results
        if not isinstance(result, dict):
            st.error(f"Unexpected sandbox return type: {type(result)}")
            st.code(str(result))
        elif result.get("ok"):
            st.success("✅ Sandbox run succeeded.")
            st.code(json.dumps(result.get("result"), indent=2), language="json")
            if result.get("stdout"):
                st.text_area("Console Output", result["stdout"], height=120)
        else:
            st.error("❌ Sandbox run failed.")
            st.code(result.get("stdout", "") or "(no stdout)")
            if result.get("stderr"):
                st.text_area("Error Output", result["stderr"], height=160)

st.markdown("---")
st.caption("When satisfied, copy the function into your vetted library (mylab/) manually.")
