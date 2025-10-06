import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras import layers

# -------------------------------
# CONFIG
# -------------------------------
CSV_PATH = "full_data.csv"   # update path if needed
DATE_COL = "Yrmo"
TARGET = "VPD"
FEATURES = ["F1","F2","F3","F4","F5","F6"]
LOOKBACK = 6
HORIZON = 3
VAL_SIZE = 24

# -------------------------------
# Load + scale
# -------------------------------
df = pd.read_csv(CSV_PATH, parse_dates=[DATE_COL])
df = df[[DATE_COL, TARGET] + FEATURES].dropna().reset_index(drop=True)

scaler = StandardScaler()
scaled = scaler.fit_transform(df.drop(columns=[DATE_COL]).values)
data = pd.DataFrame(scaled, columns=[TARGET] + FEATURES)

target_scaler = StandardScaler()
target_scaler.fit(df[[TARGET]])

# -------------------------------
# Build supervised sequences
# -------------------------------
def make_sequences(data, lookback, horizon):
    X, y, idxs = [], [], []
    arr = data.values
    for i in range(len(arr) - lookback - horizon):
        X.append(arr[i:i+lookback])
        y.append(arr[i+lookback:i+lookback+horizon, 0])  # only target col
        idxs.append(i+lookback)
    return np.array(X), np.array(y), np.array(idxs)

X, y, idxs = make_sequences(data, LOOKBACK, HORIZON)

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
# One-iteration smoke test
# -------------------------------
start = 0
end = VAL_SIZE

X_train, y_train = X[:start+end], y[:start+end]
X_val, y_val = X[start+end:start+end+VAL_SIZE], y[start+end:start+end+VAL_SIZE]
val_idxs = idxs[start+end:start+end+VAL_SIZE]

model = build_model((LOOKBACK, len(data.columns)), HORIZON)
model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=5,
    batch_size=16,
    verbose=1
)

y_pred = model.predict(X_val, verbose=0)
print("Shapes: y_val", y_val.shape, "y_pred", y_pred.shape)

# -------------------------------
# Save outputs with date values
# -------------------------------
# Convert back to original scale
y_val_inv = target_scaler.inverse_transform(y_val)
y_pred_inv = target_scaler.inverse_transform(y_pred)

rows = []
for i in range(len(y_val_inv)):
    row = {
        "date": df.loc[val_idxs[i], DATE_COL],
        **{f"y_true_t+{j+1}": y_val_inv[i, j] for j in range(HORIZON)},
        **{f"y_pred_t+{j+1}": y_pred_inv[i, j] for j in range(HORIZON)}
    }
    rows.append(row)

out = pd.DataFrame(rows)
out.to_csv("lstm_smoketest_predictions.csv", index=False)

print("\nSaved predictions with dates → lstm_smoketest_predictions.csv")
