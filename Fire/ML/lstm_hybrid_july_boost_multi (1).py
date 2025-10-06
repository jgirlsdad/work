"""
lstm_hybrid_july_boost_multi.py

Hybrid LSTM with July-boosted asymmetric MAE loss (multi-horizon).

Fix: asymmetric_mae now reduces horizon dimension to return (batch,)
to satisfy Keras expectations.
"""

import numpy as np
import pandas as pd
from typing import Tuple

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# ---------------- Config ----------------
DATA_FILE = "full_data.csv"
DATE_COL = "Yrmo"
TARGET_COL = "VPD"
FEATURES = ["F1","F2","F3","F4","F5","F6"]

LOOKBACK = 12
HORIZON  = 12
EPOCHS   = 100
BATCH    = 16
LSTM_UNITS = 64
DROPOUT = 0.1

# Loss/weighting parameters
W_UNDER = 2.0     # underprediction penalty multiplier in loss
W_OVER  = 1.0     # overprediction penalty multiplier in loss
JULY_BOOST = 1.5  # extra sample weight multiplier for July targets
MAG_SCALE = 0.5   # magnitude weighting strength; weight = 1 + MAG_SCALE * |VPD|

SEED = 1337
np.random.seed(SEED)
tf.random.set_seed(SEED)

# ---------------- Helpers ----------------
def chronological_split(n: int, train=0.6, val=0.2) -> Tuple[int,int]:
    train_end = int(train * n)
    val_end   = int((train + val) * n)
    return train_end, val_end

def asymmetric_mae(y_true, y_pred):
    """
    Asymmetric MAE with horizon reduction.
    Returns shape (batch,) as required by Keras.
    """
    diff = y_true - y_pred
    under = tf.where(diff > 0, diff, 0.0)
    over  = tf.where(diff < 0, -diff, 0.0)
    # Reduce across horizon -> scalar per sample
    loss = W_UNDER * tf.reduce_mean(under, axis=-1) + W_OVER * tf.reduce_mean(over, axis=-1)
    return loss

def make_supervised(df: pd.DataFrame,
                    y_scaled: np.ndarray,
                    X_scaled: np.ndarray,
                    lookback: int,
                    horizon: int):
    N = len(df)
    ys, Xs, idxs, months = [], [], [], []
    for i in range(lookback, N - horizon + 1):
        y_hist = y_scaled[i - lookback:i]
        X_hist = X_scaled[i - lookback:i, :]
        X_win  = np.column_stack([y_hist, X_hist])
        y_fut  = y_scaled[i:i + horizon]
        months_fut = df["month"].iloc[i:i + horizon].values
        ys.append(y_fut)
        Xs.append(X_win)
        idxs.append(i)
        months.append(months_fut)
    return (np.array(Xs, dtype="float32"),
            np.array(ys, dtype="float32"),
            np.array(idxs, dtype="int32"),
            np.array(months, dtype="int32"))

# ---------------- Load & preprocess ----------------
df = pd.read_csv(DATA_FILE)
df[DATE_COL] = pd.to_datetime(df[DATE_COL].astype(str) + "01", format="%Y%m%d")
df = df.sort_values(DATE_COL).reset_index(drop=True)
df = df[[DATE_COL, TARGET_COL] + FEATURES].dropna().reset_index(drop=True)
df = df.rename(columns={DATE_COL: "date"})
df["month"] = df["date"].dt.month

n = len(df)
train_end, val_end = chronological_split(n, 0.6, 0.2)
train = df.iloc[:train_end].copy()
val   = df.iloc[train_end:val_end].copy()
test  = df.iloc[val_end:].copy()

train_clim = train.groupby("month")[TARGET_COL].mean()
def deseasonalize(block: pd.DataFrame, clim: pd.Series) -> pd.Series:
    return block.apply(lambda r: r[TARGET_COL] - float(clim.loc[r["month"]]), axis=1)

df["anom"] = pd.concat([
    deseasonalize(train, train_clim),
    deseasonalize(val,   train_clim),
    deseasonalize(test,  train_clim),
], ignore_index=True)

y_train_anom = deseasonalize(train, train_clim).values
y_mean = float(np.mean(y_train_anom))
y_std  = float(np.std(y_train_anom) if np.std(y_train_anom) != 0 else 1.0)
df["anom_scaled"] = (df["anom"] - y_mean) / y_std

feat_means = {f: float(train[f].mean()) for f in FEATURES}
feat_stds  = {f: float(train[f].std() if train[f].std() != 0 else 1.0) for f in FEATURES}
for f in FEATURES:
    df[f + "_scaled"] = (df[f] - feat_means[f]) / feat_stds[f]
scaled_feature_cols = [f + "_scaled" for f in FEATURES]

y_scaled = df["anom_scaled"].values
X_scaled = df[scaled_feature_cols].values

X_all, y_all, idxs, month_matrix = make_supervised(df, y_scaled, X_scaled, LOOKBACK, HORIZON)

start_idx = LOOKBACK
end_idx   = len(df) - HORIZON + 1
supervised_rows = np.arange(start_idx, end_idx)

train_rows = supervised_rows[supervised_rows < train_end]
val_rows   = supervised_rows[(supervised_rows >= train_end) & (supervised_rows < val_end)]
test_rows  = supervised_rows[supervised_rows >= val_end]

def mask_rows(rows, arr_idx):
    return np.isin(arr_idx, rows)

mask_train = mask_rows(train_rows, idxs)
mask_val   = mask_rows(val_rows, idxs)
mask_test  = mask_rows(test_rows, idxs)

X_train, y_train = X_all[mask_train], y_all[mask_train]
X_val,   y_val   = X_all[mask_val],   y_all[mask_val]
X_test,  y_test  = X_all[mask_test],  y_all[mask_test]
months_train     = month_matrix[mask_train]
months_val       = month_matrix[mask_val]
months_test      = month_matrix[mask_test]
idx_test         = idxs[mask_test]

# ---------------- Model ----------------
model = keras.Sequential([
    layers.Input(shape=(LOOKBACK, 1 + len(FEATURES))),
    layers.LSTM(LSTM_UNITS, dropout=DROPOUT),
    layers.Dense(HORIZON)
])
model.compile(optimizer="adam", loss=asymmetric_mae)

callbacks = [
    EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True, min_delta=1e-4),
    ModelCheckpoint("best_lstm_hybrid_multi.h5", monitor="val_loss", save_best_only=True, verbose=1)
]

history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=EPOCHS,
    batch_size=BATCH,
    verbose=2
)

pred_scaled = model.predict(X_test, verbose=0)

rows = []
for i in range(pred_scaled.shape[0]):
    init_idx = idx_test[i]
    for h in range(HORIZON):
        verif_idx = init_idx + h
        verif_date = df.loc[verif_idx, "date"]
        month = int(df.loc[verif_idx, "month"])
        obs_anom = df.loc[verif_idx, "anom"]
        pred_anom = float(pred_scaled[i, h] * y_std + y_mean)
        obs = float(obs_anom + float(train_clim.loc[month]))
        pred = float(pred_anom + float(train_clim.loc[month]))
        mae = abs(obs - pred)
        rows.append({
            "date": verif_date,
            "horizon": h + 1,
            "month": month,
            "observed": obs,
            "predicted": pred,
            "mae": mae
        })

out = pd.DataFrame(rows).sort_values(["date","horizon"]).reset_index(drop=True)
out.to_csv("forecast_results_hybrid_multi.csv", index=False)

monthly = out.groupby(["month","horizon"])["mae"].mean().reset_index()
monthly.rename(columns={"mae":"mean_mae"}, inplace=True)
monthly.to_csv("monthly_mae_hybrid.csv", index=False)

print("Saved: forecast_results_hybrid_multi.csv, monthly_mae_hybrid.csv")
print("Done.")
