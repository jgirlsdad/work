"""
lstm_deseasonalized_forecast.py

Pipeline:
- Load data from full_data.csv with Yrmo (YYYYMM) and target column VPD
- Deseasonalize by subtracting monthly mean
- Train/test split (60/20/20)
- Train LSTM on anomalies
- Forecast out to horizon=12
- Add monthly means back in
- Save results with observed, predicted, MAE per horizon
- Also save monthly aggregated MAE table
"""

import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.metrics import mean_absolute_error
from pathlib import Path

# ---------------- Config ----------------
DATA_FILE = "full_data.csv"   # input file
DATE_COL = "Yrmo"             # YYYYMM format
TARGET_COL = "VPD"            # target variable
OUT_FILE = "forecast_results.csv"
MONTHLY_MAE_FILE = "monthly_mae.csv"

HORIZON = 12
LOOKBACK = 12   # how many past steps to use as input

# ---------------- Helpers ----------------
def prepare_data(df, lookback=12):
    X, y, dates = [], [], []
    values = df[TARGET_COL + "_anom"].values
    for i in range(lookback, len(values)-HORIZON+1):
        X.append(values[i-lookback:i])
        y.append(values[i:i+HORIZON])
        dates.append(df["date"].iloc[i:i+HORIZON].values)
    return np.array(X), np.array(y), np.array(dates)

# ---------------- Main ----------------
def main():
    # Load
    df = pd.read_csv(DATA_FILE)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL].astype(str) + "01", format="%Y%m%d")
    df = df.sort_values(DATE_COL).reset_index(drop=True)
    df = df.rename(columns={DATE_COL:"date"})

    # Deseasonalize
    df["month"] = df["date"].dt.month
    monthly_means = df.groupby("month")[TARGET_COL].mean()
    df[TARGET_COL + "_anom"] = df.apply(lambda r: r[TARGET_COL] - monthly_means.loc[r["month"]], axis=1)

    # Train/val/test split
    n = len(df)
    train_end = int(0.6*n)
    val_end = int(0.8*n)
    train, val, test = df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]

    # Prepare data
    X_train, y_train, _ = prepare_data(train, LOOKBACK)
    X_val, y_val, _ = prepare_data(val, LOOKBACK)
    X_test, y_test, test_dates = prepare_data(test, LOOKBACK)

    X_train = X_train[..., np.newaxis]
    X_val = X_val[..., np.newaxis]
    X_test = X_test[..., np.newaxis]

    # Build LSTM
    model = keras.Sequential([
        layers.Input(shape=(LOOKBACK,1)),
        layers.LSTM(64, activation="tanh"),
        layers.Dense(HORIZON)
    ])
    model.compile(optimizer="adam", loss="mae")
    model.fit(X_train, y_train, epochs=30, batch_size=16,
              validation_data=(X_val,y_val), verbose=1)

    # Forecast
    preds = model.predict(X_test)
    results = []
    for i in range(len(preds)):
        for h in range(HORIZON):
            date = pd.to_datetime(test_dates[i,h])
            month = date.month
            obs = y_test[i,h] + monthly_means.loc[month]
            pred = preds[i,h] + monthly_means.loc[month]
            mae = abs(obs - pred)
            results.append([date, h+1, obs, pred, mae])

    res_df = pd.DataFrame(results, columns=["date","horizon","observed","predicted","mae"])
    res_df.to_csv(OUT_FILE,index=False)

    # Monthly MAE table
    monthly = res_df.groupby([res_df["date"].dt.month,"horizon"])["mae"].mean().reset_index()
    monthly = monthly.rename(columns={"date":"month","mae":"mean_mae"})
    monthly.to_csv(MONTHLY_MAE_FILE,index=False)

    print("Saved:", OUT_FILE, MONTHLY_MAE_FILE)

if __name__ == "__main__":
    main()
