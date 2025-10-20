import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
import os

# ------------------ Adaptive Asymmetric Loss ------------------
def adaptive_asymmetric_mae(y_true, y_pred, base_under=1.0, base_over=1.0, scale=0.5):
    diff = y_true - y_pred
    weight = 1.0 + scale * tf.abs(y_true)   # larger values -> higher penalty
    under = tf.where(diff > 0, diff * weight, 0.0)
    over  = tf.where(diff < 0, -diff, 0.0)
    return base_under * tf.reduce_mean(under) + base_over * tf.reduce_mean(over)

# ------------------ Data Loader ------------------
def load_data(csv_path="full_data.csv", target_col="VPD", date_col="Yrmo", lookback=12):
    df = pd.read_csv(csv_path)
    df[date_col] = pd.to_datetime(df[date_col].astype(str) + "01", format="%Y%m%d")

    values = df[target_col].values.reshape(-1,1)
    scaler = MinMaxScaler()
    values_scaled = scaler.fit_transform(values)

    X, y, dates = [], [], []
    for i in range(lookback, len(values_scaled)):
        X.append(values_scaled[i-lookback:i])
        y.append(values_scaled[i])
        dates.append(df[date_col].iloc[i])

    return np.array(X), np.array(y), np.array(dates), scaler, df

# ------------------ Model ------------------
def build_lstm(input_shape):
    model = Sequential([
        LSTM(64, activation="tanh", input_shape=input_shape),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss=adaptive_asymmetric_mae)
    return model

# ------------------ Multi-horizon Forecast ------------------
def multi_horizon_forecast(model, X_test, lookback, scaler, horizons=12):
    preds, obs, dates, horizons_list = [], [], [], []
    for i in range(len(X_test)):
        history = X_test[i].copy()
        for h in range(1, horizons+1):
            pred = model.predict(history[np.newaxis, :, :], verbose=0)
            history = np.vstack([history[1:], pred])  # roll forward
            preds.append(pred[0,0])
            obs.append(y_test[i+h-1,0] if i+h-1 < len(y_test) else np.nan)
            dates.append(test_dates[i+h-1] if i+h-1 < len(test_dates) else pd.NaT)
            horizons_list.append(h)

    preds = scaler.inverse_transform(np.array(preds).reshape(-1,1)).flatten()
    obs = scaler.inverse_transform(np.array(obs).reshape(-1,1)).flatten()

    return pd.DataFrame({
        "date": dates,
        "horizon": horizons_list,
        "observed": obs,
        "predicted": preds
    }).dropna()

# ------------------ Training & Forecast ------------------
def run_training():
    X, y, dates, scaler, df = load_data()

    # Split 60/20/20
    n = len(X)
    train, val, test = int(0.6*n), int(0.8*n), n
    X_train, y_train = X[:train], y[:train]
    X_val, y_val = X[train:val], y[train:val]
    global X_test, y_test, test_dates
    X_test, y_test, test_dates = X[val:], y[val:], dates[val:]

    model = build_lstm((X.shape[1], X.shape[2]))

    checkpoint_path = "best_lstm_adaptive_multi.h5"
    callbacks = [
        EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True, min_delta=1e-4),
        ModelCheckpoint(checkpoint_path, monitor="val_loss", save_best_only=True, verbose=1)
    ]

    # Train
    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=100,
        batch_size=16,
        callbacks=callbacks,
        verbose=2
    )

    if os.path.exists(checkpoint_path):
        model.load_weights(checkpoint_path)

    # Multi-horizon forecast
    results = multi_horizon_forecast(model, X_test, lookback=12, scaler=scaler, horizons=12)

    # Add MAE
    results["mae"] = np.abs(results["observed"] - results["predicted"])

    # Save forecasts
    results.to_csv("forecast_results_adaptive_multi.csv", index=False)

    # Monthly MAE
    results["month"] = pd.to_datetime(results["date"]).dt.month
    monthly_mae = results.groupby(["month","horizon"])["mae"].mean().reset_index()
    monthly_mae.to_csv("monthly_mae_adaptive.csv", index=False)

    print("\nSaved forecast_results_adaptive_multi.csv and monthly_mae_adaptive.csv")

if __name__ == "__main__":
    run_training()
