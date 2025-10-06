# app.py (CLI-ish to keep it short)
import argparse, json, pandas as pd
from tool_registry import discover, get_catalog
from orchestrator import run_tool_call
from prompts import PLAN_PROMPT, CODE_PROMPT
from openai import OpenAI

def chat_complete(client, model, system, user):
    msgs=[{"role":"system","content":system},{"role":"user","content":user}]
    out = client.chat.completions.create(model=model, messages=msgs)
    return out.choices[0].message.content

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--goal", required=True)
    ap.add_argument("--model", default="gpt-4o-mini")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)

    discover("mylab")
    catalog_json = json.dumps(get_catalog(), indent=2)

    schema = df.dtypes.to_frame("dtype").to_string()
    plan_text = chat_complete(
        OpenAI(), args.model,
        "You are a careful planner; do not produce code.",
        f"DATA SCHEMA (first rows)\n{schema}\n\nGOAL: {args.goal}\n\n{PLAN_PROMPT}"
    )
    plan_json = plan_text.strip()

    code_text = chat_complete(
        OpenAI(), args.model,
        "You output only one JSON line describing which library tool to call.",
        CODE_PROMPT.format(catalog_json=catalog_json, plan_json=plan_json)
    )
    tool_call = json.loads(code_text)

    if tool_call.get("kwargs", {}).get("df") == "__DATAFRAME__":
        tool_call["kwargs"]["df"] = df
    result = run_tool_call(tool_call)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()
