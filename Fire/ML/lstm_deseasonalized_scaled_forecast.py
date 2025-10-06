"""
lstm_deseasonalized_scaled_forecast.py

What this script does
---------------------
- Loads full_data.csv (expects columns: Yrmo, VPD, F1..F6)
- Converts Yrmo (YYYYMM) -> pandas datetime (YYYY-MM-01)
- Splits chronologically: 60% train / 20% val / 20% test
- Deseasonalizes VPD using TRAIN-ONLY monthly means (no leakage)
- Standard-scales:
    • VPD anomalies (train mean/std)
    • All features F1..F6 (train mean/std)
- Trains a simple LSTM that outputs a 12-step horizon of anomalies
- Inference on the test set; then UN-scales anomalies and ADDS BACK monthly means
- Writes:
    • forecast_results.csv  (date, horizon, observed, predicted, mae)
    • monthly_mae.csv       (month, horizon, mean_mae)

Notes
-----
- This is CPU/GPU agnostic. For GPU, run inside your TF-enabled Docker.
- Tune LOOKBACK/EPOCHS/LSTM width for your hardware and accuracy needs.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from typing import Tuple

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.metrics import mean_absolute_error

# ---------------- Config ----------------
DATA_FILE = "full_data.csv"   # input file (Yrmo, VPD, F1..F6)
DATE_COL = "Yrmo"
TARGET_COL = "VPD"
FEATURES = ["F1","F2","F3","F4","F5","F6"]

LOOKBACK = 12        # months of history fed into LSTM
HORIZON  = 12        # forecast length
EPOCHS   = 30        # bump up in Docker if you want
BATCH    = 16
LSTM_UNITS = 64
DROPOUT = 0.1
SEED = 1337

OUT_FORECAST = "forecast_results.csv"
OUT_MONTHLY  = "monthly_mae.csv"
OUT_DEBUG    = "preproc_params.json"

np.random.seed(SEED)
tf.random.set_seed(SEED)

# ---------------- Helpers ----------------
def chronological_split(n: int, train=0.6, val=0.2) -> Tuple[int,int]:
    """Return index splits (train_end, val_end) for n rows."""
    train_end = int(train * n)
    val_end   = int((train + val) * n)
    return train_end, val_end

def make_supervised(y_scaled: np.ndarray,
                    X_scaled: np.ndarray,
                    dates: np.ndarray,
                    lookback: int,
                    horizon: int):
    """
    Build (X, y, idxs) where:
      X shape: (N, lookback, 1 + num_features)  [we'll concat y + features]
      y shape: (N, horizon)   (multi-output direct)
    We use the scaled anomalies for y, and scaled features for X.
    """
    N = len(y_scaled)
    out_X, out_y, out_dates_idx = [], [], []
    for i in range(lookback, N - horizon + 1):
        # past windows
        y_hist = y_scaled[i - lookback:i]                       # (lookback,)
        X_hist = X_scaled[i - lookback:i, :]                    # (lookback, F)
        # concat y as first channel then features
        window = np.column_stack([y_hist, X_hist])              # (lookback, 1+F)
        out_X.append(window)
        # future targets
        out_y.append(y_scaled[i:i + horizon])
        out_dates_idx.append(i)  # index of first forecasted step
    return np.array(out_X), np.array(out_y), np.array(out_dates_idx)

# ---------------- Load ----------------
df = pd.read_csv(DATA_FILE)
if DATE_COL not in df.columns:
    raise ValueError(f"Cannot find '{DATE_COL}' in {DATA_FILE}.")

# Parse Yrmo -> timestamp
df[DATE_COL] = pd.to_datetime(df[DATE_COL].astype(str) + "01", format="%Y%m%d")
df = df.sort_values(DATE_COL).reset_index(drop=True)
df = df[[DATE_COL, TARGET_COL] + FEATURES].dropna().reset_index(drop=True)
df = df.rename(columns={DATE_COL: "date"})
df["month"] = df["date"].dt.month

# ---------------- Split ----------------
n = len(df)
if n < (LOOKBACK + HORIZON + 24):
    print("Warning: dataset is small for the chosen lookback/horizon; consider reducing LOOKBACK/HORIZON.")
train_end, val_end = chronological_split(n, 0.6, 0.2)

train = df.iloc[:train_end].copy()
val   = df.iloc[train_end:val_end].copy()
test  = df.iloc[val_end:].copy()

# ---------------- Deseasonalize (TRAIN-ONLY monthly means) ----------------
train_clim = train.groupby("month")[TARGET_COL].mean()  # Series: month -> mean VPD

def deseasonalize(block: pd.DataFrame, clim: pd.Series) -> pd.Series:
    return block.apply(lambda r: r[TARGET_COL] - float(clim.loc[r["month"]]), axis=1)

df["anom"]   = pd.concat([
    deseasonalize(train, train_clim),
    deseasonalize(val,   train_clim),
    deseasonalize(test,  train_clim),
], ignore_index=True)

# Rewrite with the new column (aligned)
df.loc[:, "anom"] = df["anom"].values

# ---------------- Scaling (TRAIN stats ONLY) ----------------
# Target anomalies scaling (z-score)
y_train = train.assign(anom=train.apply(lambda r: r[TARGET_COL] - float(train_clim.loc[r["month"]]), axis=1))["anom"].values
y_mean, y_std = float(np.mean(y_train)), float(np.std(y_train) if np.std(y_train) != 0 else 1.0)

df["anom_scaled"] = (df["anom"] - y_mean) / y_std

# Feature scaling (z-score each feature)
feat_means = {}
feat_stds  = {}
for f in FEATURES:
    mu = train[f].mean()
    sd = train[f].std() if train[f].std() != 0 else 1.0
    feat_means[f] = float(mu)
    feat_stds[f]  = float(sd)
    df[f + "_scaled"] = (df[f] - mu) / sd

scaled_feature_cols = [f + "_scaled" for f in FEATURES]

# ---------------- Build supervised arrays ----------------
y_scaled = df["anom_scaled"].values  # (N,)
X_scaled = df[scaled_feature_cols].values  # (N, F)
dates    = df["date"].values

X_all, y_all, idxs = make_supervised(y_scaled, X_scaled, dates, LOOKBACK, HORIZON)

# We need to map idxs (which points to the first forecasted step) to splits
# The supervised arrays start at LOOKBACK and end at N - HORIZON + 1
start_idx = LOOKBACK
end_idx   = len(df) - HORIZON + 1
supervised_rows = np.arange(start_idx, end_idx)

# find split positions within supervised rows
train_rows = supervised_rows[supervised_rows < train_end]
val_rows   = supervised_rows[(supervised_rows >= train_end) & (supervised_rows < val_end)]
test_rows  = supervised_rows[supervised_rows >= val_end]

def row_mask(rows, arr_idx):
    mask = np.isin(arr_idx + 0, rows)  # arr_idx already corresponds to first forecasted step
    return mask

mask_train = row_mask(train_rows, idxs)
mask_val   = row_mask(val_rows, idxs)
mask_test  = row_mask(test_rows, idxs)

X_train, y_train = X_all[mask_train], y_all[mask_train]
X_val,   y_val   = X_all[mask_val],   y_all[mask_val]
X_test,  y_test  = X_all[mask_test],  y_all[mask_test]
idx_test         = idxs[mask_test]

# Add a channel axis for LSTM input
X_train = X_train.astype("float32")
X_val   = X_val.astype("float32")
X_test  = X_test.astype("float32")

# ---------------- Model ----------------
model = keras.Sequential([
    layers.Input(shape=(LOOKBACK, 1 + len(FEATURES))),  # anom channel + F features
    layers.LSTM(LSTM_UNITS, dropout=DROPOUT),
    layers.Dense(HORIZON)
])
model.compile(optimizer="adam", loss="mae")

# Train
model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH,
          validation_data=(X_val, y_val), verbose=1)

# Predict (scaled anomaly space)
pred_scaled = model.predict(X_test, verbose=0)  # shape (Ntest, HORIZON)

# ---------------- Invert scaling + reseasonalize ----------------
# Build rows of results for each (sample, horizon)
rows = []
for i in range(pred_scaled.shape[0]):
    init_idx = idx_test[i]  # index in df of the first forecasted step
    init_date = df.loc[init_idx, "date"]
    for h in range(HORIZON):
        verif_idx = init_idx + h
        verif_date = df.loc[verif_idx, "date"]
        month = int(df.loc[verif_idx, "month"])

        # Observed anomaly (unscaled) at that future step
        obs_anom = df.loc[verif_idx, "anom"]

        # Predicted anomaly (unscaled)
        pred_anom = (pred_scaled[i, h] * y_std) + y_mean

        # Add back training climatology
        obs = obs_anom + float(train_clim.loc[month])
        pred = pred_anom + float(train_clim.loc[month])

        mae = abs(obs - pred)

        rows.append({
            "date": verif_date,
            "horizon": h + 1,
            "month": month,
            "observed": float(obs),
            "predicted": float(pred),
            "mae": float(mae)
        })

out = pd.DataFrame(rows).sort_values(["date","horizon"]).reset_index(drop=True)
out.to_csv(OUT_FORECAST, index=False)

# ---------------- Monthly MAE ----------------
monthly = out.groupby(["month","horizon"])["mae"].mean().reset_index()
monthly.rename(columns={"mae":"mean_mae"}, inplace=True)
monthly.to_csv(OUT_MONTHLY, index=False)

print(f"Saved: {OUT_FORECAST}, {OUT_MONTHLY}")
print("Done.")
