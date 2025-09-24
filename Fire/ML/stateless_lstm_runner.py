
#!/usr/bin/env python3
# stateless_lstm_runner.py
"""
Train a stateless LSTM for VPD forecasting with climate-index features.
- Uses mixed precision (Tensor Cores) and cuDNN LSTM fast path
- Proper feature-wise scaling and separate y-scaler
- EarlyStopping + ReduceLROnPlateau
- Times the training step and reports inverse-scaled VAL MAE
"""

import os, time, argparse, sqlite3
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import mixed_precision
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler

# ---------------- GPU / mixed precision ----------------
def setup_gpu(use_xla=True):
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
    mixed_precision.set_global_policy("mixed_float16")
    if use_xla:
        tf.config.optimizer.set_jit(True)
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        try:
            tf.config.set_visible_devices(gpus[0], "GPU")
            tf.config.experimental.set_memory_growth(gpus[0], True)
            print("Using GPU:", gpus[0])
        except Exception as e:
            print("GPU config warning:", e)
    else:
        print("No GPU found; running on CPU.")

# ---------------- Data helpers ----------------
def read_wx_data(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("select * from MEANS_TTdRHVPD", conn)
    conn.close()
    return df

def select_wx_data(df, point, var="VPD"):
    sub = df.loc[df["Point"] == point].copy()
    if sub.empty:
        raise ValueError(f"No rows for Point={point}.")
    yrmos = sub["Yrmo"].astype(int).values
    mos   = sub["Yrmo"].str[4:6].astype(int).values
    target = sub[[var]].astype(float).values  # (N,1)
    return target, yrmos, mos

def get_climate_indices(directory):
    features = {}
    with os.scandir(directory) as entries:
        for entry in entries:
            if not entry.is_file():
                continue
            file = entry.name
            if "Zone.Identifier" in file:
                continue
            path = os.path.join(directory, file)
            # quick validation
            ok = True
            with open(path, "r") as fin:
                spl = fin.readline().split()
                if not spl:
                    continue
                start, end = int(spl[0]), int(spl[1])
                for _ in range(start, end + 1):
                    spl = fin.readline().split()
                    if not spl:
                        break
                    y = int(spl[0])
                    if 1949 < y < 2024:
                        for m in range(1, 13):
                            if float(spl[m]) < -30:
                                ok = False; break
                    if not ok: break
            if not ok:
                print("Skip outlier file:", file); 
                continue
            # ingest
            name = ".".join(file.split(".")[:-1])
            with open(path, "r") as fin:
                spl = fin.readline().split()
                if not spl:
                    continue
                start, end = int(spl[0]), int(spl[1])
                for _ in range(start, end + 1):
                    spl = fin.readline().split()
                    if not spl:
                        break
                    y = int(spl[0]); features.setdefault(y, {})
                    for m in range(1, 13):
                        features[y].setdefault(m, {})
                        features[y][m][name] = float(spl[m])
    return features

def build_feature_matrix(climate, start, end, indices=("all",)):
    feats = []
    # screen out any index that dips < -30 within 1990-2024
    banned = {}
    for y, d in climate.items():
        if 1989 < y < 2025:
            for _, d2 in d.items():
                for nm, v in d2.items():
                    if v < -30:
                        banned[nm] = True
    for y in range(start, end + 1):
        d = climate[y]
        for m, d2 in d.items():
            row = []
            for nm, v in sorted(d2.items()):
                if (indices[0] == "all" or nm in indices) and (nm not in banned):
                    row.append(v)
            feats.append(row)
    return np.array(feats, dtype=np.float32)

# ---------------- Windows, scaling, datasets ----------------
def build_windows(features, target, timesteps=24, horizon=8):
    F = np.asarray(features, dtype=np.float32)
    Y = np.asarray(target,  dtype=np.float32).reshape(-1, 1)
    F_shift, Y_shift = F[horizon:], Y[:-horizon]
    X, y = [], []
    for i in range(timesteps, len(F_shift)):
        X.append(F_shift[i - timesteps:i])
        y.append(Y_shift[i])
    X = np.stack(X, 0); y = np.stack(y, 0)
    return X, y  # (M,T,F), (M,1)

def scale_featurewise(X, y):
    S, T, F = X.shape
    xsc = MinMaxScaler()
    ysc = MinMaxScaler()
    Xs = xsc.fit_transform(X.reshape(-1, F)).reshape(S, T, F)
    ys = ysc.fit_transform(y)
    return Xs, ys, xsc, ysc

def make_ds(X, y, bs, shuffle=True):
    ds = tf.data.Dataset.from_tensor_slices((X, y))
    if shuffle:
        ds = ds.shuffle(min(8192, len(X)))
    return ds.batch(bs, drop_remainder=False).cache().prefetch(tf.data.AUTOTUNE)

# ---------------- Model ----------------
def build_model(timesteps, nfeatures, units=256, layers=1, dropout=0.0, lr=2e-3, seed=None):
    if seed is not None:
        tf.keras.utils.set_random_seed(seed)
    layers_list = [Input(shape=(timesteps, nfeatures))]
    if layers == 1:
        layers_list += [LSTM(units)]
    else:
        layers_list += [LSTM(units, return_sequences=True),
                        LSTM(units)]
    if dropout and dropout > 0.0:
        layers_list += [Dropout(float(dropout))]
    layers_list += [Dense(1, dtype="float32")]  # stable loss under mixed precision
    model = Sequential(layers_list)
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss="mse")
    return model

# ---------------- Runner ----------------
def run(args):
    setup_gpu(use_xla=not args.no_xla)

    # Load data
    climate = get_climate_indices(args.climate_dir)
    feats   = build_feature_matrix(climate, 1990, 2024, indices=("all",))
    df      = read_wx_data(args.db_path)
    target, yrmos, mos = select_wx_data(df, point=args.point, var=args.var)

    # Windows & scaling
    X, y   = build_windows(feats, target, timesteps=args.timesteps, horizon=args.horizon)
    nfeat  = X.shape[-1]
    Xs, ys, xsc, ysc = scale_featurewise(X, y)

    # Split
    n = len(Xs); n_train = int(0.8 * n)
    X_train, X_val = Xs[:n_train], Xs[n_train:]
    y_train, y_val = ys[:n_train], ys[n_train:]
    y_val_inv = ysc.inverse_transform(y_val)

    # Datasets
    train_ds = make_ds(X_train, y_train, args.batch, shuffle=True)
    val_ds   = make_ds(X_val,   y_val,   args.batch, shuffle=False)

    # Model & callbacks
    model = build_model(args.timesteps, nfeat, units=args.units, layers=args.layers,
                        dropout=args.dropout, lr=args.lr, seed=args.seed)
    cbs = [
        ModelCheckpoint("best_stateless.keras", save_best_only=True, monitor="val_loss", mode="min", verbose=0),
        EarlyStopping(monitor="val_loss", mode="min", patience=args.patience, min_delta=1e-4, restore_best_weights=True),
        ReduceLROnPlateau(monitor="val_loss", mode="min", factor=0.5, patience=8, min_lr=1e-5, verbose=0)
    ]

    # Warmup
    model.fit(train_ds.take(1), epochs=1, verbose=0)

    # Train and time
    t0 = time.perf_counter()
    hist = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=cbs, verbose=1)
    t1 = time.perf_counter()
    print(f"\nTRAIN seconds (fit only): {t1 - t0:.2f}")

    # Evaluate
    yhat = model.predict(val_ds, verbose=0)
    yhat_inv = ysc.inverse_transform(yhat)
    mae = float(np.mean(np.abs(y_val_inv - yhat_inv)))
    print(f"VAL MAE: {mae:.4f}")
    print("Saved best model → best_stateless.keras")

# ---------------- CLI ----------------
def build_argparser():
    p = argparse.ArgumentParser(description="Stateless LSTM VPD forecaster (GPU, mixed precision).")
    p.add_argument("--climate_dir", type=str, default="data/Climate-Indices", help="Directory of climate index files")
    p.add_argument("--db_path",     type=str, default="/home/joe/Fire/Data/DB/era5DataMeans.db", help="SQLite DB path")
    p.add_argument("--point",       type=int, default=500, help="Point id from the DB")
    p.add_argument("--var",         type=str, default="VPD", help="Target variable column in DB")

    p.add_argument("--timesteps",   type=int, default=24, choices=[12, 24, 36, 48, 60], help="History window length")
    p.add_argument("--horizon",     type=int, default=8, help="Forecast horizon (steps ahead)")
    p.add_argument("--units",       type=int, default=256, choices=[64, 128, 192, 256, 384, 512], help="LSTM units")
    p.add_argument("--layers",      type=int, default=1, choices=[1, 2], help="Number of LSTM layers")
    p.add_argument("--dropout",     type=float, default=0.0, help="Post-LSTM dropout (0.0–0.3)")
    p.add_argument("--batch",       type=int, default=64, choices=[32, 48, 64, 96, 128], help="Batch size")
    p.add_argument("--epochs",      type=int, default=200, help="Max epochs")
    p.add_argument("--lr",          type=float, default=2e-3, help="Adam learning rate")
    p.add_argument("--patience",    type=int, default=20, help="Early stopping patience")
    p.add_argument("--seed",        type=int, default=2025, help="Random seed for reproducibility")
    p.add_argument("--no_xla",      action="store_true", help="Disable XLA JIT")
    return p

if __name__ == "__main__":
    args = build_argparser().parse_args()
    run(args)
