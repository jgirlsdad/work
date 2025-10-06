import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
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

# -------------------------------
# Train monthly linear regressions
# -------------------------------
monthly_models = {}
rows_coef = []

for month in range(1, 13):
    preds_month, obs_month = [], []
    for i in range(len(val_preds_inv)):
        init_date = df.loc[val_idx[i], DATE_COL]
        for h in range(HORIZON):
            verif_date = init_date + pd.DateOffset(months=h+1)
            if verif_date.month == month:
                preds_month.append(val_preds_inv[i, h])
                obs_month.append(y_val_inv[i, h])
    preds_month, obs_month = np.array(preds_month).reshape(-1, 1), np.array(obs_month)
    if len(preds_month) > 0:
        model = LinearRegression().fit(preds_month, obs_month)
        monthly_models[month] = model
        rows_coef.append({
            "month": month,
            "slope": model.coef_[0],
            "intercept": model.intercept_,
            "n_samples": len(preds_month)
        })

pd.DataFrame(rows_coef).to_csv("monthly_corrections.csv", index=False)

# -------------------------------
# Apply to test set
# -------------------------------
test_preds = np.mean([m.predict(X_test, verbose=0) for m in ensemble], axis=0)
y_test_inv = target_scaler.inverse_transform(y_test)
test_preds_inv = target_scaler.inverse_transform(test_preds)

rows = []
for i in range(len(test_preds_inv)):
    init_date = df.loc[test_idx[i], DATE_COL]
    for h in range(HORIZON):
        verif_date = init_date + pd.DateOffset(months=h+1)
        raw = test_preds_inv[i, h]
        if verif_date.month in monthly_models:
            corr = monthly_models[verif_date.month].predict([[raw]])[0] - raw
            final = raw + corr
        else:
            final = raw
        rows.append({
            "date": verif_date,
            "horizon":h,
            "obs": y_test_inv[i, h],
            "raw_pred": raw,
            "corrected_pred": final
        })

out = pd.DataFrame(rows)
out.to_csv("lstm_monthly_corrected_predictions.csv", index=False)

print("Saved predictions → lstm_monthly_corrected_predictions.csv")
print("Saved monthly correction coefficients → monthly_corrections.csv")
