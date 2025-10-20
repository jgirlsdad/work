
import argparse
import json
import datetime as dt
import os
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

def asymmetric_mae(y_true, y_pred):
    diff = y_true - y_pred
    return tf.reduce_mean(tf.where(diff > 0, 2.0 * tf.abs(diff), tf.abs(diff)))

def huber_loss(y_true, y_pred):
    error = y_true - y_pred
    delta = 1.0
    is_small = tf.abs(error) <= delta
    small = 0.5 * tf.square(error)
    large = delta * (tf.abs(error) - 0.5 * delta)
    return tf.reduce_mean(tf.where(is_small, small, large))

def create_dataset(X, y, lookback=24):
    Xs, ys = [], []
    for i in range(len(X) - lookback):
        Xs.append(X[i:(i + lookback)])
        ys.append(y[i + lookback])
    return np.array(Xs), np.array(ys)

def build_model(input_shape, units=96):
    model = Sequential([
        LSTM(units, activation='tanh', return_sequences=False, input_shape=input_shape),
        Dropout(0.2),
        Dense(1)
    ])
    return model

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Input CSV with Yrmo, target, and features")
    parser.add_argument("--regime", required=True, help="Name of the regime, e.g. peak_july")
    parser.add_argument("--target", default="VPD", help="Target variable name")
    parser.add_argument("--loss", choices=["mae", "mse", "asymmetric", "huber"], default="mae")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--units", type=int, default=96)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    df = df.dropna()
    features = [c for c in df.columns if c not in [args.target, "Yrmo"]]
    X = df[features].values
    y = df[args.target].values

    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    X_scaled = scaler_X.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y.reshape(-1, 1)).flatten()

    lookback = 24
    X_seq, y_seq = create_dataset(X_scaled, y_scaled, lookback)
    X_train, X_val, y_train, y_val = train_test_split(X_seq, y_seq, test_size=0.2, shuffle=False)

    model = build_model((X_train.shape[1], X_train.shape[2]), args.units)

    loss_map = {
        "mae": "mae",
        "mse": "mse",
        "asymmetric": asymmetric_mae,
        "huber": huber_loss,
    }
    loss_fn = loss_map.get(args.loss, "mae")

    model.compile(optimizer=Adam(learning_rate=args.lr), loss=loss_fn, metrics=["mae"])

    early_stop = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True, min_delta=0.0005, verbose=1)

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=args.epochs,
        batch_size=16,
        callbacks=[early_stop],
        verbose=1
    )

    model_name = f"model_{args.regime}.h5"
    model.save(model_name)

    best_val_mae = min(history.history["val_mae"])
    log_row = {
        "timestamp": dt.datetime.now().isoformat(),
        "regime": args.regime,
        "loss_fn": args.loss,
        "epochs": args.epochs,
        "lookback": lookback,
        "units": args.units,
        "lr": args.lr,
        "best_val_mae": float(best_val_mae)
    }

    log_path = "regime_training_log.csv"
    log_exists = os.path.isfile(log_path)
    with open(log_path, "a") as f:
        if not log_exists:
            f.write(",".join(log_row.keys()) + "\n")
        f.write(",".join(map(str, log_row.values())) + "\n")

    print(json.dumps({"status": "success", "best_val_mae": best_val_mae, "model_path": model_name}, indent=2))

if __name__ == "__main__":
    main()
