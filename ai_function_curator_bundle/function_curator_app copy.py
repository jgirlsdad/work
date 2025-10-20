import sys, os, re, json, importlib.util as iul
from pathlib import Path
from typing import List, Dict, Any, Optional
import inspect, importlib
import streamlit as st
from openai import OpenAI
from datetime import datetime

# --- Local imports ---
from tool_registry import discover, get_catalog
from safety import lint_proposed_code, sandbox_test_function

# --- Path setup ---
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Streamlit setup ---
st.set_page_config(page_title="AI Function Curator", page_icon="🧰", layout="wide")
st.title("🧰 AI Function Curator — Build & Vet Analytics Functions")

FEEDBACK_DIR = ROOT / "feedback_logs"
FEEDBACK_DIR.mkdir(exist_ok=True)

# --- Sidebar configuration ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4.1"], index=0)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
    st.caption("Sandbox tests run in a temporary folder; your project files are untouched.")


# -------------------------------
# Utility functions
# -------------------------------
def get_client():
    os.environ["OPENAI_API_KEY"] = api_key
    return OpenAI()


def chat_complete(system: str, user: str) -> str:
    """Call GPT and safely extract returned text."""
    client = get_client()
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = resp.choices[0]
        content = getattr(choice.message, "content", None)

        if content and content.strip().startswith("```python"):
            content = re.sub(r"^```python|```$", "", content.strip(), flags=re.MULTILINE).strip()

        if not content:
            st.warning("⚠️ AI returned an empty message. Check your model or API key access.")
            st.code(str(resp), language="text")
            return ""

        print("Content", content)
        return content

    except Exception as e:
        st.error(f"❌ OpenAI API call failed: {e}")
        return ""
def record_feedback(func_name: str, decision: str, feedback: str, code_text: str) -> Path:
    log = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "function": func_name,
        "decision": decision,
        "feedback": (feedback or "").strip(),
        "code_excerpt": (code_text or "").strip()[:1000],
    }
    log_file = FEEDBACK_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{func_name}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    return log_file

def display_feedback_history(limit: int = 10):
    logs = sorted(FEEDBACK_DIR.glob("*.json"), reverse=True)[:limit]
    if not logs:
        st.info("No feedback logs yet.")
        return
    for lf in logs:
        with open(lf, "r", encoding="utf-8") as f:
            data = json.load(f)
        st.markdown(f"### 📝 {data['function']} — {data['decision']}")
        st.caption(f"📅 {data['timestamp']}")
        if data.get("feedback"):
            st.write(data["feedback"])
        st.code(data.get("code_excerpt",""), language="python")
        st.divider()

# -------------------------------
# UI Section 1: Function description
# -------------------------------
st.subheader("1) Describe the function you want")
idea = st.text_area(
    "Create a function that takes a csv as input and prints out the columns and data types",
    placeholder="Example: Weighted rolling correlation with handling for NaNs and irregular timestamps.",
    key="idea_box",
)

# -------------------------------
# UI Section 2: Local library discovery
# -------------------------------
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

query = st.text_input("Keyword search (optional)", "", key="lib_search")
if st.button("Search Local Tools", key="search_btn"):
    if not catalog_json or catalog_json == "{}":
        st.info("No tools registered yet.")
    else:
        q = query.strip().lower()
        matches = []
        for name, spec in json.loads(catalog_json).items():
            hay = " ".join([name, spec.get("summary", ""), " ".join(spec.get("tags", []))]).lower()
            if not q or q in hay:
                matches.append((name, spec))
        if matches:
            st.success(f"Found {len(matches)} tool(s).")
            for name, spec in matches:
                st.markdown(f"### 🧩 **{name}** — {spec.get('summary', '(no summary)')}")
                st.code(json.dumps(spec, indent=2), language="json")
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
            st.info("No matches.")


# -------------------------------
# UI Section 3: Suggest existing libraries
# -------------------------------
st.subheader("3) External Python packages that may already do this")
if st.button("Suggest existing libraries / functions", key="suggest_btn"):
    if not api_key:
        st.warning("Add your OpenAI API key in the sidebar.")
    elif not idea.strip():
        st.warning("Describe your function first.")
    else:
        system = "You are an expert Python data scientist and librarian. Be concise and practical."
        user = f"The user wants to implement a function:\n{idea}\n\nList up to 5 existing Python packages or built-ins that already implement this. For each: package.function, why relevant, caveats. Return a numbered list."
        with st.spinner("Asking GPT..."):
            suggestions = chat_complete(system, user)
        st.code(suggestions, language="markdown")


# -------------------------------
# UI Section 4: Generate Draft Function
# -------------------------------
st.subheader("4) Generate draft function")
colA, colB = st.columns([1, 1])
with colA:
    fname = st.text_input("Function name", value="new_analysis_function", key="fname_input")
with colB:
    sig_hint = st.text_input("Signature hint (optional)", "", key="sig_hint_input")

if st.button("Generate Draft", key="generate_btn"):
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

        # --- Raw GPT output ---
        st.markdown("#### 🪵 Raw GPT Output")
        st.code(draft or "(empty)", language="python")

        # --- Write directly into editable box ---
        if draft and draft.strip():
            cleaned = re.sub(r"^```python|```$", "", draft.strip(), flags=re.MULTILINE).strip()
            st.session_state["draft_code_area"] = cleaned
            st.success("✅ Draft generated successfully!")
            st.text_area("Draft function (editable)", value=cleaned, height=300, key="draft_editor")
        else:
            st.warning("⚠️ No draft content returned from model.")

# If session already has draft, show it persistently
elif "draft_code_area" in st.session_state:
    st.text_area("Draft function (editable)", value=st.session_state["draft_code_area"], height=300, key="draft_editor")


# -------------------------------
# UI Section 5: Lint & Run Sandbox Test
# -------------------------------
# -------------------------------
# UI Section 5: Lint & Run Sandbox Test
# -------------------------------
# -------------------------------
# UI Section 5: Lint & Run Test (manual, sandbox temp dir)
# -------------------------------
st.subheader("5) Lint & Run Test (manual, sandbox temp dir)")

test_file_path = st.text_input(
    "Path to test CSV file",
    "data/sample_test.csv",
    key="test_csv_path",
)

if st.button("Run Safety Lint", key="lint_btn"):
    code_text = st.session_state.get("draft_code_area", "").strip()
    if not code_text:
        st.warning("No code to lint.")
    else:
        ok, issues = lint_proposed_code(code_text)
        (st.success if ok else st.error)("Lint " + ("passed" if ok else "FAILED"))
        if issues:
            st.code("\n".join(issues), language="text")

kwargs_text = st.text_area("kwargs JSON for test", value="{}", height=100, key="kwargs_box")

if st.button("Run Test in Sandbox", key="sandbox_btn"):
    code_text = st.session_state.get("draft_code_area", "").strip()
    if not code_text:
        st.warning("No code to run.")
    else:
        try:
            kwargs = json.loads(kwargs_text) if kwargs_text.strip() else {}
        except Exception as e:
            st.error(f"Invalid kwargs JSON: {e}")
            kwargs = {}

        func_name = st.session_state.get("fname_input", "new_analysis_function")

        # If function expects csv_file, supply the path string
        if re.search(rf"def\s+{re.escape(func_name)}\s*\([^)]*csv_file", code_text):
            kwargs.setdefault("csv_file", str(Path(test_file_path).resolve()))
            st.info(f"Passing csv_file='{kwargs['csv_file']}' to function.")

        with st.spinner("Running in sandbox..."):
            result = sandbox_test_function(code_text, func_name, kwargs, timeout=25)

        if result.get("ok"):
            st.success("Sandbox run succeeded.")
            st.code(json.dumps(result.get("result"), indent=2), language="json")
        else:
            st.error("Sandbox run failed.")
            st.code(result.get("stdout", "") or "(no stdout)")
            if result.get("stderr"):
                st.code(result["stderr"])

# # -------------------------------
# UI Section 6: Review and Feedback (stable via form)
# -------------------------------
st.subheader("6) Review and Feedback")

with st.form(key="feedback_form", clear_on_submit=False):
    review_choice = st.radio(
        "Your rating:",
        ["✅ Accept (save later)", "❌ Needs Revision"],
        horizontal=True,
        key="review_choice_radio",
    )

    feedback_text = st.text_area(
        "Feedback",
        placeholder="Explain what’s wrong or what should change...",
        height=120,
        key="feedback_text_area",
    )

    submit = st.form_submit_button("Submit Review")

if submit:
    try:
        func_name = st.session_state.get("fname_input", "new_function")
        code_text = st.session_state.get("draft_code_area", "")
        if not code_text.strip():
            st.warning("No draft code to attach to feedback.")
        else:
            log_file = record_feedback(func_name, review_choice, feedback_text, code_text)
            st.success(f"✅ Feedback saved to {log_file}")
    except Exception as e:
        st.error(f"Failed to save feedback: {e}")

# Show history toggle (outside the form so it doesn't clear)
show_hist = st.checkbox("Show recent feedback history", key="show_history_checkbox", value=False)
if show_hist:
    display_feedback_history()

# -------------------------------
# Step 7: Revise with Feedback (stable form)
# -------------------------------
    st.info("🧠 Calling GPT model for revision...")
    with st.spinner("Revising with GPT..."):
        revision = chat_complete(system, user)
    st.success("🤖 GPT revision complete.")

    if revision and revision.strip():
        cleaned = re.sub(r"^```python|```$", "", revision.strip(), flags=re.MULTILINE).strip()
        st.session_state["draft_code_area"] = cleaned
        st.markdown("#### ✏️ Revised Function:")
        edited = st.text_area(
            "Editable Revised Function",
            value=cleaned,
            height=300,
            key="revised_editor",
        )
        st.session_state["draft_code_area"] = edited
    else:
        st.warning("⚠️ No revision content returned from GPT.")













st.markdown("---")
st.caption("When satisfied, copy the function into your vetted library (mylab/) manually.")
