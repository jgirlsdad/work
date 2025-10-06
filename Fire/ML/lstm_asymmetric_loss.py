import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
import os

# ------------------ Custom Loss ------------------
def asymmetric_mae(y_true, y_pred, w_under=2.0, w_over=1.0):
    diff = y_true - y_pred
    under = tf.where(diff > 0, diff, 0.0)   # underprediction
    over  = tf.where(diff < 0, -diff, 0.0)  # overprediction
    return w_under * tf.reduce_mean(under) + w_over * tf.reduce_mean(over)

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

    return np.array(X), np.array(y), np.array(dates), scaler

# ------------------ Model ------------------
def build_lstm(input_shape):
    model = Sequential([
        LSTM(64, activation="tanh", input_shape=input_shape),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss=asymmetric_mae)
    return model

# ------------------ Training & Forecast ------------------
def run_training():
    X, y, dates, scaler = load_data()

    # Split 60/20/20
    n = len(X)
    train, val, test = int(0.6*n), int(0.8*n), n
    X_train, y_train = X[:train], y[:train]
    X_val, y_val = X[train:val], y[train:val]
    X_test, y_test, test_dates = X[val:], y[val:], dates[val:]

    model = build_lstm((X.shape[1], X.shape[2]))

    # Callbacks
    checkpoint_path = "best_lstm_asym.h5"
    callbacks = [
        EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True, min_delta=1e-4),
        ModelCheckpoint(checkpoint_path, monitor="val_loss", save_best_only=True, verbose=1)
    ]

    # Train
    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=100,  # upper limit, early stopping will stop earlier
        batch_size=16,
        callbacks=callbacks,
        verbose=2
    )

    # Load best weights
    if os.path.exists(checkpoint_path):
        model.load_weights(checkpoint_path)

    # Predict
    preds = model.predict(X_test)
    preds = scaler.inverse_transform(preds)
    y_test_inv = scaler.inverse_transform(y_test)

    # Save results
    out = pd.DataFrame({
        "date": test_dates,
        "observed": y_test_inv.flatten(),
        "predicted": preds.flatten()
    })
    out["mae"] = np.abs(out["observed"] - out["predicted"])
    out.to_csv("forecast_results_asym.csv", index=False)
    print("\nSaved forecast_results_asym.csv")
    print("Mean MAE:", out["mae"].mean())

if __name__ == "__main__":
    run_training()
