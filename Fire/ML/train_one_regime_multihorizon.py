import argparse
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
import os
from pathlib import Path

# -------------------------------
# Asymmetric Loss with Threshold
# -------------------------------
def asymmetric_mae_threshold(y_true, y_pred, under_penalty=2.0, threshold=None):
    diff = y_pred - y_true
    if threshold is not None:
        cond = tf.logical_and(diff < 0, y_true > threshold)
    else:
        cond = diff < 0
    weight = tf.where(cond, under_penalty, 1.0)
    return tf.reduce_mean(tf.abs(diff) * weight)

# -------------------------------
# Data Processing
# -------------------------------
def deseasonalize(df, target):
    df = df.copy()
    df["month"] = pd.to_datetime(df["Yrmo"], format="%Y%m").dt.month
    monthly_means = df.groupby("month")[target].transform("mean")
    df["anomaly"] = df[target] - monthly_means
    return df, monthly_means

def prepare_sequences(data, lookback=24):
    X, y = [], []
    for i in range(len(data) - lookback):
        X.append(data[i:i+lookback])
        y.append(data[i+lookback])
    return np.array(X), np.array(y)

# -------------------------------
# Train and Forecast Function
# -------------------------------
def train_and_forecast(df, target, lookback, horizons, loss_type, under_penalty, threshold,
                       deseasonalize_flag, output_dir):

    if deseasonalize_flag:
        df, monthly_means = deseasonalize(df, target)
        target_col = "anomaly"
    else:
        target_col = target

    data = df[target_col].values.reshape(-1, 1)
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(data)

    split = int(len(scaled_data) * 0.8)
    train, test = scaled_data[:split], scaled_data[split - lookback:]

    X_train, y_train = prepare_sequences(train, lookback)
    X_test, y_test = prepare_sequences(test, lookback)

    results = []
#    months = pd.to_datetime(df["Yrmo"], format="%Y%m").dt.month[split + lookback:].values
    months = pd.to_datetime(df["Yrmo"], format="%Y%m").dt.month[split:].values

    actuals = scaler.inverse_transform(y_test)
    
    for horizon in range(1, horizons + 1):
        model = Sequential([
            LSTM(64, input_shape=(lookback, 1), return_sequences=False),
            Dropout(0.2),
            Dense(1)
        ])

        # Select Loss
        if loss_type == "asymmetric":
            loss_fn = lambda y_true, y_pred: asymmetric_mae_threshold(
                y_true, y_pred, under_penalty=under_penalty, threshold=threshold
            )
        elif loss_type == "mse":
            loss_fn = "mse"
        else:
            loss_fn = "mae"

        model.compile(optimizer="adam", loss=loss_fn)
        es = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)
        ckpt = ModelCheckpoint(os.path.join(output_dir, f"model_h{horizon}.h5"),
                               monitor="val_loss", save_best_only=True, verbose=0)

        model.fit(X_train, y_train, epochs=100, batch_size=16,
                  validation_split=0.2, verbose=0, callbacks=[es, ckpt])

        preds = model.predict(X_test, verbose=0)
        preds_inv = scaler.inverse_transform(preds)

        # Add back monthly mean if deseasonalized
        if deseasonalize_flag:
            preds_inv = preds_inv.flatten() + monthly_means.iloc[-len(preds_inv):].values
            actuals = actuals.flatten() + monthly_means.iloc[-len(actuals):].values
        else:
            preds_inv = preds_inv.flatten()
            actuals = actuals.flatten()

        print("df ",df["Yrmo"].iloc[-len(preds_inv.flatten()):].shape)
        print("months ",len(months))
        print("actuals ",len(actuals))
        print("preds_inv ",len(preds_inv))
        df_results = pd.DataFrame({
            "Yrmo": df["Yrmo"].iloc[-len(preds_inv.flatten()):].values,
            "Month": months,
            "Observed": actuals,
            "Predicted": preds_inv,
            "Horizon": horizon
        })
        results.append(df_results)

    all_results = pd.concat(results)
    mae_summary = all_results.groupby(["Month", "Horizon"]).apply(
        lambda x: np.mean(np.abs(x["Observed"] - x["Predicted"]))
    ).reset_index(name="Mean_MAE")

    all_results.to_csv(os.path.join(output_dir, "forecast_results.csv"), index=False)
    mae_summary.to_csv(os.path.join(output_dir, "monthly_mae.csv"), index=False)

    print(f"✅ Forecast and MAE outputs saved in {output_dir}")

# -------------------------------
# CLI
# -------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--target", required=True)
    ap.add_argument("--lookback", type=int, default=24)
    ap.add_argument("--horizons", type=int, default=12)
    ap.add_argument("--loss", choices=["mae", "mse", "asymmetric"], default="asymmetric")
    ap.add_argument("--under_penalty", type=float, default=2.0)
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--deseasonalize", action="store_true")
    ap.add_argument("--output_dir", type=str, default="output")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    os.makedirs(args.output_dir, exist_ok=True)

    train_and_forecast(df, args.target, args.lookback, args.horizons, args.loss,
                       args.under_penalty, args.threshold, args.deseasonalize, args.output_dir)

if __name__ == "__main__":
    main()
