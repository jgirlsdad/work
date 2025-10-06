import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras import layers

# -------------------------------
# CONFIG (smoke test version)
# -------------------------------
CSV_PATH = "full_data.csv"
TARGET = "VPD"
FEATURES = ["F1","F2","F3","F4","F5","F6"]
LOOKBACK = 6
HORIZON = 3
VAL_SIZE = 24

# -------------------------------
# Load + scale
# -------------------------------
df = pd.read_csv(CSV_PATH)
df = df[[TARGET] + FEATURES].dropna().reset_index(drop=True)

scaler = StandardScaler()
scaled = scaler.fit_transform(df.values)
data = pd.DataFrame(scaled, columns=df.columns)

target_scaler = StandardScaler()
target_scaler.fit(df[[TARGET]])

# -------------------------------
# Build supervised sequences
# -------------------------------
def make_sequences(data, lookback, horizon):
    X, y = [], []
    arr = data.values
    for i in range(len(arr) - lookback - horizon):
        X.append(arr[i:i+lookback])
        y.append(arr[i+lookback:i+lookback+horizon, 0])
    return np.array(X), np.array(y)

X, y = make_sequences(data, LOOKBACK, HORIZON)

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

model = build_model((LOOKBACK, len(df.columns)), HORIZON)
callbacks = [
    keras.callbacks.EarlyStopping(monitor="val_loss", patience=2, restore_best_weights=True)
]

model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=5,
    batch_size=16,
    verbose=1,
    callbacks=callbacks
)

y_pred = model.predict(X_val, verbose=0)
print("Shapes: y_val", y_val.shape, "y_pred", y_pred.shape)
