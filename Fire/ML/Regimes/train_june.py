# train_fullseries_focus_month_ensemble_loss.py
# -------------------------------------------------------
# Full-series training with regime-focused weighting + ENSEMBLE
# Selectable loss: "mae", "mse", "huber", or "asym_mae"
# Outputs: full forecasts + monthly×horizon MAE + horizon MAE
# -------------------------------------------------------

import os, random
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.preprocessing import StandardScaler

# =========================
# CONFIG
# =========================
CSV_PATH = "../full_data.csv"     # expects columns: Yrmo, VPD, F1..F6
TARGET = "VPD"
FEATURES = ["F1","F2","F3","F4","F5","F6"]

LOOKBACK  = 24
HORIZON   = 6
VAL_SIZE  = 96
ROLL_STEP = 24

FOCUS_MONTH   = 6          # emphasize this month (June=6)
FOCUS_WEIGHT  = 1.5        # >1.0 boosts focus-month samples during training

ENSEMBLE_N = 5
AGG = "median"             # "median" (robust) or "mean"
BASE_SEED = 1337
MC_DROPOUT_PASSES = 0      # >0 enables MC Dropout averaging at inference

# ---- Loss selection ----
LOSS_TYPE   = "mae"        # "mae" | "mse" | "huber" | "asym_mae"
HUBER_DELTA = 1.0
ASYM_LAMBDA = 1.5          # under-pred penalty for "asym_mae"

OUTPUT_DIR = "."
MODEL_TAG = f"FullSeries_FocusM{FOCUS_MONTH}_Ens{ENSEMBLE_N}_{AGG}_{LOSS_TYPE}"
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# =========================
# UTILS
# =========================
def set_global_seed(seed: int):
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)

def derive_month_from_yrmo(df: pd.DataFrame) -> pd.DataFrame:
    yrmo_str = df["Yrmo"].astype(str).str.strip()
    dt = pd.to_datetime(yrmo_str, format="%Y%m", errors="coerce")
    mask_na = dt.isna()
    if mask_na.any():
        dt2 = pd.to_datetime(yrmo_str[mask_na], format="%Y-%m", errors="coerce")
        dt = dt.fillna(dt2)
    mask_na = dt.isna()
    if mask_na.any():
        month_fallback = yrmo_str[mask_na].str[-2:].str.zfill(2).astype(int)
        month_series = pd.Series(index=yrmo_str.index, dtype="Int64")
        month_series[~mask_na] = dt[~mask_na].dt.month
        month_series[mask_na] = month_fallback
        df["Month"] = month_series.astype(int)
    else:
        df["Month"] = dt.dt.month
    return df

def make_sequences_with_anchors(df_scaled: pd.DataFrame,
                                lookback: int,
                                horizon: int,
                                yrmo_series: pd.Series):
    arr = df_scaled.values
    X, y, anchor_yrmo, anchor_month = [], [], [], []
    for i in range(len(arr) - lookback - horizon):
        X.append(arr[i:i+lookback])
        y.append(arr[i+lookback:i+lookback+horizon, 0])  # target column is 0 post-scale
        anchor_idx = i + lookback
        a_yrmo = yrmo_series.iloc[anchor_idx]
        anchor_yrmo.append(a_yrmo)
        anchor_month.append(int(str(a_yrmo)[-2:]))  # robust month fallback
    return np.array(X), np.array(y), np.array(anchor_yrmo), np.array(anchor_month)

# -------- Losses ----------
def asym_mae_factory(lam: float):
    @tf.function
    def asym_mae(y_true, y_pred):
        # elementwise on (batch, horizon)
        diff  = y_true - y_pred
        under = tf.nn.relu(diff)     # y_true > y_pred
        over  = tf.nn.relu(-diff)    # y_pred > y_true
        per_elem = lam * under + over
        return tf.reduce_mean(per_elem)  # mean over batch and horizon
    return asym_mae

def get_loss(loss_type: str):
    lt = loss_type.lower()
    if lt == "mae":
        return keras.losses.MeanAbsoluteError()
    if lt == "mse":
        return keras.losses.MeanSquaredError()
    if lt == "huber":
        return keras.losses.Huber(delta=HUBER_DELTA)
    if lt == "asym_mae":
        return asym_mae_factory(ASYM_LAMBDA)
    raise ValueError(f"Unknown LOSS_TYPE: {loss_type}")

# -------- Model ----------
def build_model(input_shape, horizon):
    # June-style Dense-LSTM hybrid
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.LSTM(64, dropout=0.2),
        layers.Dense(32, activation="relu"),
        layers.Dense(horizon)
    ])
    model.compile(optimizer="adam", loss=get_loss(LOSS_TYPE), metrics=["mae"])
    return model

# =========================
# LOAD + PREP
# =========================
df = pd.read_csv(CSV_PATH)
df = df[["Yrmo", TARGET] + FEATURES].dropna().reset_index(drop=True)
df = derive_month_from_yrmo(df)

# Global scaling
scaler = StandardScaler()
scaled = scaler.fit_transform(df[[TARGET] + FEATURES])
data_scaled = pd.DataFrame(scaled, columns=[TARGET] + FEATURES)

# Target scaler for inverse-transform
target_scaler = StandardScaler()
target_scaler.fit(df[[TARGET]])

# Sequences over full series
X, y, anchor_yrmo, anchor_month = make_sequences_with_anchors(
    data_scaled, LOOKBACK, HORIZON, df["Yrmo"]
)
print(f"Full-series sequences: X={X.shape}, y={y.shape}")

# Focus weighting (per-sample)
sample_weight = np.ones(len(X), dtype=np.float32)
sample_weight[anchor_month == FOCUS_MONTH] = FOCUS_WEIGHT

# =========================
# WALK-FORWARD ENSEMBLE
# =========================
preds_all, trues_all, yrmo_all = [], [], []

for start in range(0, len(X) - VAL_SIZE, ROLL_STEP):
    end = start + VAL_SIZE
    if end > len(X): break
    print("Start ",start)
    X_train, y_train = X[:start+end], y[:start+end]
    X_val,   y_val   = X[start+end:start+end+VAL_SIZE], y[start+end:start+end+VAL_SIZE]
    sw_train = sample_weight[:start+end]

    if len(X_val) == 0: break

    # Ensemble members for this fold
    member_preds = []
    for k in range(ENSEMBLE_N):
        print("   Member ",k)
        set_global_seed(BASE_SEED + k)
        model = build_model((LOOKBACK, len(FEATURES)+1), HORIZON)
        cb = keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)

        model.fit(
            X_train, y_train,
            sample_weight=sw_train,
            validation_data=(X_val, y_val),
            epochs=50, batch_size=32, verbose=0, callbacks=[cb]
        )

        if MC_DROPOUT_PASSES and MC_DROPOUT_PASSES > 0:
            mc_stack = []
            for _ in range(MC_DROPOUT_PASSES):
                mc_stack.append(model(X_val, training=True).numpy())
            preds_member = np.mean(np.stack(mc_stack, axis=0), axis=0)
        else:
            preds_member = model.predict(X_val, verbose=0)

        member_preds.append(preds_member)

    member_preds = np.stack(member_preds, axis=0)  # (members, fold_len, horizon)
    fold_pred = member_preds.mean(axis=0) if AGG == "mean" else np.median(member_preds, axis=0)

    preds_all.append(fold_pred)
    trues_all.append(y_val)
    yrmo_all.append(anchor_yrmo[start+end:start+end+VAL_SIZE])

if not preds_all:
    raise SystemExit("No predictions generated. Reduce VAL_SIZE or increase data length.")

# Stack folds
preds_all = np.vstack(preds_all)   # (N_val_total, HORIZON)
trues_all = np.vstack(trues_all)
yrmo_all  = np.concatenate(yrmo_all)

# Inverse transform (linear scaler → OK to aggregate before inverse)
y_true_inv = target_scaler.inverse_transform(trues_all)
y_pred_inv = target_scaler.inverse_transform(preds_all)

# =========================
# BUILD RESULTS & SAVE
# =========================
yrmo_flat = np.repeat(yrmo_all, HORIZON)
horizons  = np.tile(np.arange(1, HORIZON+1), len(yrmo_all))
actuals   = y_true_inv.flatten()
preds     = y_pred_inv.flatten()

df_results = pd.DataFrame({
    "Yrmo": yrmo_flat,
    "Horizon": horizons,
    "Actual": actuals,
    "Predicted": preds
})

mo = pd.to_datetime(df_results["Yrmo"].astype(str), format="%Y%m", errors="coerce").dt.month
mask_na = mo.isna()
if mask_na.any():
    mo.loc[mask_na] = df_results.loc[mask_na, "Yrmo"].astype(str).str[-2:].astype(int)
df_results["Month"] = mo.astype(int)

df_results["Model"]        = MODEL_TAG
df_results["FocusMonth"]   = FOCUS_MONTH
df_results["FocusWeight"]  = FOCUS_WEIGHT
df_results["EnsembleN"]    = ENSEMBLE_N
df_results["Aggregation"]  = AGG
df_results["LossType"]     = LOSS_TYPE
df_results["AsymLambda"]   = ASYM_LAMBDA if LOSS_TYPE == "asym_mae" else np.nan
df_results["HuberDelta"]   = HUBER_DELTA if LOSS_TYPE == "huber" else np.nan

out_forecasts = Path(OUTPUT_DIR) / f"forecast_fullseries_{MODEL_TAG}.csv"
df_results.to_csv(out_forecasts, index=False)
print(f"✅ Saved forecasts → {out_forecasts}")

# =========================
# METRICS
# =========================
monthly_mae = (
    df_results.groupby(["Month","Horizon"])
    .apply(lambda x: float(np.mean(np.abs(x["Predicted"] - x["Actual"]))))
    .reset_index(name="Mean_MAE")
)
out_mae = Path(OUTPUT_DIR) / f"monthly_mae_fullseries_{MODEL_TAG}.csv"
monthly_mae.to_csv(out_mae, index=False)
print(f"✅ Saved monthly MAE → {out_mae}")

h_mae = (
    df_results.groupby(["Horizon"])
    .apply(lambda x: float(np.mean(np.abs(x["Predicted"] - x["Actual"]))))
    .reset_index(name="Mean_MAE")
)
out_hmae = Path(OUTPUT_DIR) / f"horizon_mae_fullseries_{MODEL_TAG}.csv"
h_mae.to_csv(out_hmae, index=False)
print(f"✅ Saved horizon MAE → {out_hmae}")

# (Optional) quick peek
print("\nTop of monthly MAE:")
print(monthly_mae.sort_values(["Month","Horizon"]).head(12))
print("\nHorizon MAE:")
print(h_mae)
