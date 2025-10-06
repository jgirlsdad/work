# mylab/eda.py
import pandas as pd
from .util import maybe_import_mpl
from tool_registry import tool

@tool(
  summary="Quick EDA summary and optional histograms",
  inputs={"df":"pd.DataFrame","target":"Optional[str]"},
  outputs={"summary_csv":"str","plot_path":"Optional[str]"},
  tags=["eda","summary","plot_optional"]
)
def quick_eda(df: pd.DataFrame, target: str|None = None):
    desc = df.describe(include="all").transpose()
    out_csv = "eda_summary.csv"
    desc.to_csv(out_csv)
    plot_path = None
    plt = maybe_import_mpl()
    if plt:
        try:
            df.select_dtypes("number").hist(figsize=(10,6))
            plt.savefig("histograms.png", dpi=120, bbox_inches="tight")
            plot_path = "histograms.png"
        except Exception:
            pass
    return {"summary_csv": out_csv, "plot_path": plot_path}
