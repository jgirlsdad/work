import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras import layers

# -------------------------------
# CONFIG
# -------------------------------
CSV_PATH = "fake_vpd.csv"  # expects YYYY-MM format in date column
DATE_COL = "date"
TARGET = "VPD"
FEATURES = ["F1","F2","F3","F4","F5","F6"]
LOOKBACK = 6
HORIZON = 12
ENSEMBLE_SIZE = 3
EPOCHS = 5

# -------------------------------
# Load + scale
# -------------------------------
df = pd.read_csv(CSV_PATH)
df[DATE_COL] = pd.to_datetime(df[DATE_COL].astype(str) + "-01")
df = df[[DATE_COL, TARGET] + FEATURES].dropna().reset_index(drop=True)

scaler = StandardScaler()
scaled = scaler.fit_transform(df.drop(columns=[DATE_COL]).values)
data = pd.DataFrame(scaled, columns=[TARGET] + FEATURES)
target_scaler = StandardScaler().fit(df[[TARGET]])

# -------------------------------
# Make supervised sequences
# -------------------------------
def make_sequences(data, lookback, horizon):
    X, y, idxs = [], [], []
    arr = data.values
    for i in range(len(arr) - lookback - horizon):
        X.append(arr[i:i+lookback])
        y.append(arr[i+lookback:i+lookback+horizon, 0])
        idxs.append(i+lookback)
    return np.array(X), np.array(y), np.array(idxs)

X, y, idxs = make_sequences(data, LOOKBACK, HORIZON)

# Chronological split 60-20-20
n = len(X)
train_end = int(0.6*n)
val_end = int(0.8*n)
X_train, y_train = X[:train_end], y[:train_end]
X_val, y_val, val_idx = X[train_end:val_end], y[train_end:val_end], idxs[train_end:val_end]
X_test, y_test, test_idx = X[val_end:], y[val_end:], idxs[val_end:]

# -------------------------------
# Model builder
# -------------------------------
def build_model(input_shape, horizon):
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.LSTM(32, dropout=0.2),
        layers.Dense(horizon)
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model

# -------------------------------
# Train ensemble on training set
# -------------------------------
ensemble = []
for i in range(ENSEMBLE_SIZE):
    m = build_model((LOOKBACK, len(data.columns)), HORIZON)
    m.fit(X_train, y_train, epochs=EPOCHS, batch_size=16, verbose=0)
    ensemble.append(m)

# -------------------------------
# Ensemble rollouts
# -------------------------------
val_preds = np.mean([m.predict(X_val, verbose=0) for m in ensemble], axis=0)
y_val_inv = target_scaler.inverse_transform(y_val)
val_preds_inv = target_scaler.inverse_transform(val_preds)

test_preds = np.mean([m.predict(X_test, verbose=0) for m in ensemble], axis=0)
y_test_inv = target_scaler.inverse_transform(y_test)
test_preds_inv = target_scaler.inverse_transform(test_preds)

# -------------------------------
# Monthly bias computation
# -------------------------------
biases = {}
rows_bias = []

for month in range(1, 13):
    diffs = []
    for i in range(len(val_preds_inv)):
        init_date = df.loc[val_idx[i], DATE_COL]
        for h in range(HORIZON):
            verif_date = init_date + pd.DateOffset(months=h+1)
            if verif_date.month == month:
                diffs.append(y_val_inv[i, h] - val_preds_inv[i, h])
    if len(diffs) > 0:
        bias = float(np.mean(diffs))
        biases[month] = bias
        rows_bias.append({"month": month, "bias": bias, "n_samples": len(diffs)})

pd.DataFrame(rows_bias).to_csv("lstm_monthly_bias_corrections.csv", index=False)

# -------------------------------
# Apply bias correction to validation set for ratio computation
# -------------------------------
val_bias_corrected = []
val_obs = []
for i in range(len(val_preds_inv)):
    init_date = df.loc[val_idx[i], DATE_COL]
    for h in range(HORIZON):
        verif_date = init_date + pd.DateOffset(months=h+1)
        raw = val_preds_inv[i, h]
        bias = biases.get(verif_date.month, 0.0)
        bias_corrected = raw + bias
        val_bias_corrected.append((verif_date.month, bias_corrected))
        val_obs.append((verif_date.month, y_val_inv[i, h]))

val_bias_corrected = pd.DataFrame(val_bias_corrected, columns=["month","bias_corrected"])
val_obs = pd.DataFrame(val_obs, columns=["month","obs"])
val_join = val_bias_corrected.join(val_obs.set_index("month"), on="month")

# -------------------------------
# Compute monthly ratios using bias-corrected forecasts
# -------------------------------
ratios = {}
rows_ratio = []
for month in range(1, 13):
    subset = val_join[val_join["month"]==month]
    if len(subset) > 0 and subset["bias_corrected"].mean() != 0:
        ratio = float(subset["obs"].mean() / subset["bias_corrected"].mean())
        ratios[month] = ratio
        rows_ratio.append({"month": month, "ratio": ratio, "n_samples": len(subset)})

pd.DataFrame(rows_ratio).to_csv("lstm_monthly_ratio_corrections.csv", index=False)

# -------------------------------
# Apply corrections to test set
# -------------------------------
rows = []
for i in range(len(test_preds_inv)):
    init_date = df.loc[test_idx[i], DATE_COL]
    for h in range(HORIZON):
        verif_date = init_date + pd.DateOffset(months=h+1)
        raw = test_preds_inv[i, h]
        bias = biases.get(verif_date.month, 0.0)
        bias_corrected = raw + bias
        ratio = ratios.get(verif_date.month, 1.0)
        ratio_corrected = bias_corrected * ratio
        rows.append({
            "date": verif_date,
            "horizon": h+1,
            "obs": y_test_inv[i, h],
            "raw_pred": raw,
            "bias_corrected_pred": bias_corrected,
            "ratio_corrected_pred": ratio_corrected
        })

out = pd.DataFrame(rows)
out.to_csv("lstm_monthly_corrected_predictions.csv", index=False)

print("Saved predictions → lstm_monthly_corrected_predictions.csv")
print("Saved monthly mean biases → lstm_monthly_bias_corrections.csv")
print("Saved monthly ratios (from bias-corrected) → lstm_monthly_ratio_corrections.csv")
