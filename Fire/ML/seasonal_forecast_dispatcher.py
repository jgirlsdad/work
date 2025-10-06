import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from pathlib import Path

DATA_PATH = Path("full_data.csv")
OUTPUT_PATH = Path("seasonal_forecast_results.csv")

MODEL_PATHS = {
    "ramp": "model_ramp.h5",
    "peak": "model_peak_july.h5",
    "decay": "model_decay.h5",
    "baseline": "model_baseline.h5"
}

REGIME_BY_MONTH = {
    1: "baseline", 2: "baseline", 3: "baseline",
    4: "ramp", 5: "ramp", 6: "ramp",
    7: "peak",
    8: "decay", 9: "decay", 10: "decay",
    11: "baseline", 12: "baseline"
}

def load_models():
    models = {}
    for regime, path in MODEL_PATHS.items():
        try:
            models[regime] = load_model(path, compile=False)
            print(f"✅ Loaded {regime} model from {path}")
        except Exception as e:
            print(f"⚠️ Could not load {regime} model: {e}")
    return models

def assign_regime(month: int) -> str:
    return REGIME_BY_MONTH.get(month, "baseline")

def forecast_for_row(row, models, X_features):
    regime = assign_regime(row["month"])
    model = models.get(regime)
    if model is None:
        return np.nan
    x_input = np.expand_dims(X_features.loc[row.name].values, axis=0)
    pred = model.predict(x_input, verbose=0)
    return float(pred.squeeze())

def run_forecast():
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["Yrmo"].astype(str) + "01", format="%Y%m%d", errors="coerce")
    df["month"] = df["date"].dt.month
    feature_cols = [c for c in df.columns if c not in ["Yrmo", "VPD", "date", "month"]]
    target_col = "VPD"
    models = load_models()
    print("\n🔁 Running regime-based forecasts...")
    df["Forecast"] = df.apply(lambda r: forecast_for_row(r, models, df[feature_cols]), axis=1)
    df["Error"] = df[target_col] - df["Forecast"]
    df["AbsError"] = df["Error"].abs()
    mae_by_month = df.groupby("month")["AbsError"].mean().reset_index()
    mae_by_month.columns = ["month", "MAE"]
    print("\n📊 Monthly MAE summary:")
    print(mae_by_month)
    df.to_csv(OUTPUT_PATH, index=False)
    mae_by_month.to_csv("monthly_mae_dispatcher.csv", index=False)
    print(f"\n💾 Saved forecasts to {OUTPUT_PATH}")
    print(f"💾 Saved monthly MAE to monthly_mae_dispatcher.csv")

if __name__ == "__main__":
    run_forecast()
