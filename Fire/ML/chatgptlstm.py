# lstm_vpd_best.py
import os, csv, pickle, math, warnings
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error

# ---------------- TF / Keras ----------------
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

# ---------------- Config ----------------
DATA_PATH = "full_data.csv"          # <- ensure this exists
TARGET = "VPD"
FEATURES = ["F1","F2","F3","F4","F5","F6"]
TEST_FRACTION = 0.20                  # last 20% for test (time-respecting)
GRID_T = [3, 6, 9, 12]                # window sizes (months)
GRID_UNITS = [32, 64]
GRID_LAYERS = [1, 2]
EPOCHS = 120
BATCH_SIZE = 16
SEED = 42
PLOT_PATH = "lstm_best_plot.png"
PRED_CSV = "lstm_best_predictions.csv"
MODEL_PATH = "lstm_best_model.keras"
SCALER_X_PATH = "scaler_X.pkl"
SCALER_Y_PATH = "scaler_y.pkl"

tf.keras.utils.set_random_seed(SEED)
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------- Helpers ----------------
def load_csv(path: str) -> pd.DataFrame:
    # Light delimiter/encoding sniffing (robust enough for common cases)
    import chardet
    with open(path, "rb") as f:
        raw = f.read(4096)
    enc = chardet.detect(raw)["encoding"] or "utf-8"
    try:
        sample = raw.decode(enc, errors="ignore")
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delim = dialect.delimiter
    except Exception:
        delim = ","
    df = pd.read_csv(path, sep=delim, encoding=enc, engine="python")
    df = df[FEATURES + [TARGET]].apply(pd.to_numeric, errors="coerce").dropna()
    return df

def make_sequences(df_num: pd.DataFrame, T: int):
    X_list, y_list = [], []
    for t in range(T, len(df_num)):
        X_list.append(df_num[FEATURES].iloc[t-T:t].values)  # (T, 6)
        y_list.append(df_num[TARGET].iloc[t])
    X_seq = np.array(X_list)           # (N, T, 6)
    y = np.array(y_list).reshape(-1,1) # (N, 1)
    return X_seq, y

def build_lstm(input_shape, units: int, layers: int, dropout: float = 0.2) -> Sequential:
    model = Sequential()
    if layers == 1:
        model.add(LSTM(units, input_shape=input_shape))
        model.add(Dropout(dropout))
    else:
        model.add(LSTM(units, return_sequences=True, input_shape=input_shape))
        model.add(Dropout(dropout))
        model.add(LSTM(max(units//2, 16)))
        model.add(Dropout(dropout))
    model.add(Dense(32, activation="relu"))
    model.add(Dense(1))
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mse")
    return model

def train_eval(X_seq, y, units: int, layers: int):
    # Time-respecting split
    split_idx = int((1 - TEST_FRACTION) * len(X_seq))
    X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # Fit scalers on train only
    scaler_X = StandardScaler()
    X_train_2d = X_train.reshape(-1, X_train.shape[2])
    X_test_2d  = X_test.reshape(-1, X_test.shape[2])
    scaler_X.fit(X_train_2d)
    X_train_s = scaler_X.transform(X_train_2d).reshape(X_train.shape)
    X_test_s  = scaler_X.transform(X_test_2d).reshape(X_test.shape)

    scaler_y = StandardScaler()
    scaler_y.fit(y_train)
    y_train_s = scaler_y.transform(y_train)
    y_test_s  = scaler_y.transform(y_test)

    # Model + callbacks
    model = build_lstm((X_train_s.shape[1], X_train_s.shape[2]), units, layers)
    early = EarlyStopping(monitor="val_loss", patience=12, restore_best_weights=True)
    reduce = ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=6, min_lr=1e-5)

    model.fit(
        X_train_s, y_train_s,
        validation_split=0.15,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=[early, reduce],
        verbose=0
    )

    # Evaluate
    y_pred_s = model.predict(X_test_s, verbose=0)
    y_pred = scaler_y.inverse_transform(y_pred_s)
    r2 = r2_score(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred)

    return r2, rmse, model, (X_test_s, y_test, y_pred), scaler_X, scaler_y

# ---------------- Main ----------------
def main():
    df = load_csv(DATA_PATH)
    if len(df) < 50:
        raise SystemExit("Not enough rows after cleaning to train.")

    # Sweep grid
    results = []
    best = {"r2": -1e9}
    for T in GRID_T:
        X_seq, y = make_sequences(df, T)
        if len(X_seq) < 50:
            continue
        for units in GRID_UNITS:
            for layers in GRID_LAYERS:
                tf.keras.utils.set_random_seed(SEED)
                r2, rmse, model, eval_pack, scX, scY = train_eval(X_seq, y, units, layers)
                results.append({"T": T, "units": units, "layers": layers, "r2": r2, "rmse": rmse})
                if r2 > best["r2"]:
                    best = {
                        "T": T, "units": units, "layers": layers,
                        "r2": r2, "rmse": rmse,
                        "model": model, "eval": eval_pack,
                        "scaler_X": scX, "scaler_y": scY
                    }
                print(f"T={T:>2}, units={units:>2}, layers={layers}  ->  R2={r2:.3f}, RMSE={rmse:.3f}")

    # Report best combo
    print("\nBest LSTM configuration:")
    print(f"T={best['T']}, units={best['units']}, layers={best['layers']}, "
          f"R2={best['r2']:.3f}, RMSE={best['rmse']:.3f}")

    # Save scalers + model
    with open(SCALER_X_PATH, "wb") as f: pickle.dump(best["scaler_X"], f)
    with open(SCALER_Y_PATH, "wb") as f: pickle.dump(best["scaler_y"], f)
    best["model"].save(MODEL_PATH)

    # Save predictions CSV and plot
    X_test_s, y_test, y_pred = best["eval"]
    pred_df = pd.DataFrame({"actual": y_test.flatten(), "predicted": y_pred.flatten()})
    pred_df.to_csv(PRED_CSV, index=False)

    # Plot
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(y_test, label="Actual VPD")
    ax.plot(y_pred, label="Predicted VPD", alpha=0.85)
    ax.set_title(f"Best LSTM — T={best['T']}, units={best['units']}, layers={best['layers']}  "
                 f"(R2={best['r2']:.3f}, RMSE={best['rmse']:.3f})")
    ax.set_xlabel("Test sample index (time order)")
    ax.set_ylabel("VPD")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(PLOT_PATH, dpi=150)
    plt.close(fig)

    # Also print a compact leaderboard
    res_df = pd.DataFrame(results).sort_values("r2", ascending=False)
    print("\nLeaderboard (top 10 by R²):")
    print(res_df.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
