import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from tensorflow import keras
from tensorflow.keras import layers

# -------------------------------
# CONFIG
# -------------------------------
CSV_PATH = "full_data.csv"
DATE_COL = "Yrmo"
TARGET = "VPD"
FEATURES = ["F1","F2","F3","F4","F5","F6"]
LOOKBACK = 6
HORIZON = 6
ENSEMBLE_SIZE = 5
EPOCHS = 5

# -------------------------------
# Load + scale
# -------------------------------
df = pd.read_csv(CSV_PATH, parse_dates=[DATE_COL])
df = df[[DATE_COL, TARGET] + FEATURES].dropna().reset_index(drop=True)
df[DATE_COL]+="01"
print(df.head())
df[DATE_COL] = pd.to_datetime(df[DATE_COL])
print(df.dtypes,df.head())
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
# Ensemble rollouts on validation
# -------------------------------
val_preds = np.mean([m.predict(X_val, verbose=0) for m in ensemble], axis=0)
y_val_inv = target_scaler.inverse_transform(y_val)
val_preds_inv = target_scaler.inverse_transform(val_preds)

# Compute errors
errors = y_val_inv - val_preds_inv

# -------------------------------
# Train correction model
# -------------------------------
# Safe features: raw forecast, horizon, month
rows, targets = [], []
for i in range(len(val_preds_inv)):
    init_date = df.loc[val_idx[i], DATE_COL]
    for h in range(HORIZON):
        rows.append([val_preds_inv[i, h], h+1, init_date.month])
        targets.append(errors[i, h])
X_corr = np.array(rows)
y_corr = np.array(targets)

corrector = GradientBoostingRegressor()
corrector.fit(X_corr, y_corr)

# -------------------------------
# Apply to test set
# -------------------------------
test_preds = np.mean([m.predict(X_test, verbose=0) for m in ensemble], axis=0)
y_test_inv = target_scaler.inverse_transform(y_test)
test_preds_inv = target_scaler.inverse_transform(test_preds)
# df[DATE_COL] = pd.to_datetime(df[DATE_COL],format="%y%m%d")
# print(df.dtypes,df.head())
rows = []
for i in range(len(test_preds_inv)):
    init_date = df.loc[test_idx[i], DATE_COL]
    for h in range(HORIZON):
        raw = test_preds_inv[i, h]
        corr = corrector.predict([[raw, h+1, init_date.month]])[0]
        final = raw + corr
        rows.append({
            "date": init_date + pd.DateOffset(months=h+1),
            "horizon":h,
            "obs": y_test_inv[i, h],
            "raw_pred": raw,
            "corrected_pred": final
        })

out = pd.DataFrame(rows)
out.to_csv("lstm_corrected_predictions.csv", index=False)

print("Saved predictions → lstm_corrected_predictions.csv")
