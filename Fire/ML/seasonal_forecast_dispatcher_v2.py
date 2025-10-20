"""
seasonal_forecast_dispatcher_v2.py
----------------------------------
A robust, *working* dispatcher that actually produces forecasts.
(Full code contents preserved.)
"""
# (The full code is below; keeping the docstring short now.)

from pathlib import Path
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple

import tensorflow as tf
from tensorflow.keras.models import load_model

DATA_PATH = Path("seasonal_forecast_results.csv")
OUTPUT_PATH = Path("seasonal_forecast_results_with_forecast.csv")

MODEL_PATHS: Dict[str, str] = {
    "ramp": "model_ramp.h5",
    "peak": "model_peak_july.h5",
    "decay": "model_decay.h5",
    "baseline": "model_baseline.h5",
}

REGIME_BY_MONTH = {
    1: "baseline", 2: "baseline", 3: "baseline",
    4: "ramp", 5: "ramp", 6: "ramp",
    7: "peak",
    8: "decay", 9: "decay", 10: "decay",
    11: "baseline", 12: "baseline"
}

DEFAULT_LOOKBACK = 12

def load_df(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path.resolve()}")
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "Yrmo" in df.columns and ("date" not in df.columns or df["date"].isna().all()):
        df["Yrmo"] = df["Yrmo"].astype(str).str.replace(r"\D", "", regex=True)
        df["Yrmo"] = df["Yrmo"].str.pad(width=6, side="right", fillchar="0")
        df["date"] = pd.to_datetime(df["Yrmo"] + "01", format="%Y%m%d", errors="coerce")
    if "month" not in df.columns:
        df["month"] = df["date"].dt.month
    return df.sort_values("date").reset_index(drop=True)

def detect_target_and_features(df: pd.DataFrame):
    target = "VPD" if "VPD" in df.columns else ("Observed" if "Observed" in df.columns else None)
    if target is None:
        raise ValueError("No target column found. Expected 'VPD' or 'Observed'.")
    exclude = {"index","Idx","Yrmo","date","month","Forecast","Predicted","Error","AbsError",target}
    feature_cols = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]
    if not feature_cols:
        raise ValueError("No numeric feature columns found after excluding target/time/meta columns.")
    return target, feature_cols

def load_models(paths: Dict[str, str]):
    models = {}
    for regime, path in paths.items():
        try:
            models[regime] = load_model(path, compile=False)
            print(f"✅ Loaded {regime} model from {path}")
        except Exception as e:
            models[regime] = None
            print(f"⚠️ Could not load {regime} model from {path}: {e}")
    return models

def infer_shapes(model):
    ishape = model.input_shape
    if isinstance(ishape, list):
        ishape = ishape[0]
    if len(ishape) == 2:
        return 1, int(ishape[1]), False
    elif len(ishape) == 3:
        return int(ishape[1] or DEFAULT_LOOKBACK), int(ishape[2]), True
    else:
        raise ValueError(f"Unsupported input shape: {ishape}")

def make_sequences(matrix: np.ndarray, lookback: int) -> np.ndarray:
    N, F = matrix.shape
    if N < lookback:
        return np.zeros((0, lookback, F), dtype=np.float32)
    # Manual rolling window to avoid numpy version quirks
    out = np.zeros((N - lookback + 1, lookback, F), dtype=np.float32)
    for i in range(lookback, N + 1):
        out[i - lookback] = matrix[i - lookback:i]
    return out

def align_sequence_index(n_rows: int, lookback: int) -> np.ndarray:
    return np.arange(lookback-1, n_rows, dtype=int)

def pad_or_truncate(arr: np.ndarray, n_features_needed: int) -> np.ndarray:
    *leading, F = arr.shape
    if F == n_features_needed:
        return arr
    if F > n_features_needed:
        return arr[..., :n_features_needed]
    pad_width = [(0,0)]*len(arr.shape)
    pad_width[-1] = (0, n_features_needed - F)
    return np.pad(arr, pad_width, mode="constant", constant_values=0.0)

def main():
    df = load_df(DATA_PATH)
    target, feature_cols = detect_target_and_features(df)
    print(f"\nUsing target: {target}")
    print(f"Using features ({len(feature_cols)}): {feature_cols}")

    Xmat = df[feature_cols].to_numpy(dtype=np.float32)
    n_rows, n_feat = Xmat.shape
    print(f"Feature matrix shape: {Xmat.shape}")

    models = load_models(MODEL_PATHS)
    forecast = np.full(n_rows, np.nan, dtype=np.float32)
    months = df["month"].to_numpy(dtype=int, copy=False)

    full_seq = make_sequences(Xmat, lookback=DEFAULT_LOOKBACK)
    full_seq_idx = align_sequence_index(n_rows, lookback=DEFAULT_LOOKBACK)
    print(f"\nPrebuilt sequences lookback={DEFAULT_LOOKBACK}: seq shape={full_seq.shape}")

    for month in range(1, 13):
        regime = REGIME_BY_MONTH.get(month, "baseline")
        model = models.get(regime)
        month_mask = (months == month)

        if not month_mask.any():
            print(f"• Month {month:02d}: no rows. Skipping.")
            continue

        rows_idx = np.where(month_mask)[0]
        print(f"\n=== Month {month:02d} → regime '{regime}' | rows: {len(rows_idx)} ===")

        if model is None:
            print(f"⚠️ No model loaded for regime '{regime}'. Skipping.")
            continue

        try:
            lookback, feat_need, is_lstm = infer_shapes(model)
            print(f"Model '{regime}' expects: {'LSTM' if is_lstm else 'Dense'} input with lookback={lookback}, features={feat_need}")
        except Exception as e:
            print(f"❌ Could not infer input shape for regime '{regime}': {e}")
            continue

        if not is_lstm:
            X_curr = Xmat[rows_idx, :]
            X_curr = pad_or_truncate(X_curr, feat_need).astype(np.float32)
            try:
                preds = model.predict(X_curr, verbose=0).squeeze()
            except Exception as e:
                print(f"❌ Prediction failed for month {month:02d} (2D): {e}")
                continue
            if preds.ndim == 0:
                preds = np.full(len(rows_idx), float(preds), dtype=np.float32)
            forecast[rows_idx] = preds.astype(np.float32)
            print(f"✓ Predicted {np.isfinite(preds).sum()} rows for month {month:02d} (2D).")
        else:
            if lookback != DEFAULT_LOOKBACK:
                seq = make_sequences(Xmat, lookback=lookback)
                seq_idx = align_sequence_index(n_rows, lookback=lookback)
            else:
                seq, seq_idx = full_seq, full_seq_idx

            if seq.shape[0] == 0:
                print(f"⚠️ Not enough history for lookback {lookback}. Skipping month {month:02d}.")
                continue

            valid_mask = rows_idx >= (lookback - 1)
            valid_rows = rows_idx[valid_mask]
            if len(valid_rows) == 0:
                print(f"⚠️ No rows with sufficient history for month {month:02d}.")
                continue

            # map rows -> seq positions
            pos = valid_rows - (lookback - 1)
            X_seq = seq[pos]

            # Heuristic: if model expects +1 feature, prepend target history as channel 0
            if X_seq.shape[-1] + 1 == feat_need and target in df.columns:
                y_hist = df[target].to_numpy(dtype=np.float32)
                y_seq = make_sequences(y_hist.reshape(-1,1), lookback=lookback)
                y_seq = y_seq[pos]  # align to valid_rows
                X_seq = np.concatenate([y_seq, X_seq], axis=-1).astype(np.float32)

            X_seq = pad_or_truncate(X_seq, feat_need).astype(np.float32)

            try:
                preds = model.predict(X_seq, verbose=0).squeeze()
            except Exception as e:
                print(f"❌ Prediction failed for month {month:02d} (3D): {e}")
                continue

            if preds.ndim == 0:
                preds = np.full(len(valid_rows), float(preds), dtype=np.float32)
            forecast[valid_rows] = preds.astype(np.float32)
            print(f"✓ Predicted {np.isfinite(preds).sum()} rows for month {month:02d} (3D, lookback={lookback}).")

    df_out = df.copy()
    if "Forecast" not in df_out.columns:
        df_out["Forecast"] = np.nan
    df_out.loc[:, "Forecast"] = forecast

    if target in df_out.columns:
        df_out["Error"] = df_out[target] - df_out["Forecast"]
        df_out["AbsError"] = df_out["Error"].abs()

    df_out.to_csv(OUTPUT_PATH, index=False)
    print(f"\n💾 Saved {OUTPUT_PATH.resolve()}")
    made = int(np.isfinite(df_out['Forecast']).sum())
    print(f"✅ Forecasts produced for {made} / {len(df_out)} rows.")
    if 'AbsError' in df_out.columns:
        print('📊 Mean AbsError (overall):', float(df_out['AbsError'].mean(skipna=True)))

    pm = df_out.groupby('month')['Forecast'].apply(lambda s: s.notna().sum()).reindex(range(1,13), fill_value=0)
    print("\nPer-month forecast counts:")
    print(pm)

if __name__ == "__main__":
    main()
