
#!/usr/bin/env python3
# grid_lstm_gpu_runner_horizons.py
"""
Grid search for stateless LSTM VPD forecasting with climate-index features.
Now supports a grid of forecast horizons (H).

- Mixed precision (Tensor Cores) + cuDNN LSTM fast path
- Train-only scaling (fit scalers on train, transform val) to avoid leakage
- tf.data with cache/prefetch; warmup uses no-cache to avoid warnings
- EarlyStopping + ReduceLROnPlateau
- Saves results to CSV and prints Top 10 by inverse-scaled VAL MAE

Default grids (edit via CLI):
  H ∈ {8}
  T ∈ {24,36,48}
  units ∈ {128,256,384}
  layers ∈ {1,2}
  batch ∈ {64,96,128}
"""

import os, time, argparse, itertools, sqlite3, datetime
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
                print("Skip outlier file:", file)
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
    """Predict t+H from data up to t. No leakage by itself; leakage depends on scaling stage."""
    F = np.asarray(features, dtype=np.float32)
    Y = np.asarray(target,  dtype=np.float32).reshape(-1, 1)
    F_shift, Y_shift = F[horizon:], Y[:-horizon]
    X, y = [], []
    for i in range(timesteps, len(F_shift)):
        X.append(F_shift[i - timesteps:i])
        y.append(Y_shift[i])
    X = np.stack(X, 0); y = np.stack(y, 0)
    return X, y  # (M,T,F), (M,1)

def make_ds(X, y, bs, shuffle=True, cache=True):
    ds = tf.data.Dataset.from_tensor_slices((X, y))
    if shuffle:
        ds = ds.shuffle(min(8192, len(X)))
    ds = ds.batch(bs, drop_remainder=False)
    if cache:
        ds = ds.cache()
    ds = ds.prefetch(tf.data.AUTOTUNE)
    return ds

# ---------------- Model ----------------
def build_model(timesteps, nfeatures, units=256, layers=1, dropout=0.0, lr=2e-3, huber=False, seed=None):
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
    loss = tf.keras.losses.Huber(delta=1.0) if huber else "mse"
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss=loss)
    return model

# ---------------- Grid runner ----------------
def run_grid(args, features, target):
    # Parse grids
    H_grid      = [int(x) for x in args.H.split(",")]
    T_grid      = [int(x) for x in args.T.split(",")]
    UNITS_grid  = [int(x) for x in args.units.split(",")]
    LAYERS_grid = [int(x) for x in args.layers.split(",")]
    BATCH_grid  = [int(x) for x in args.batch.split(",")]

    combos = list(itertools.product(H_grid, T_grid, UNITS_grid, LAYERS_grid, BATCH_grid))
    if args.max_runs and args.max_runs > 0:
        combos = combos[:args.max_runs]
    print(f"Running {len(combos)} configurations...")

    results = []
    total_start = time.perf_counter()

    for H, T, units, layers, batch in combos:
        # Build windows for this (H, T)
        X, y = build_windows(features, target, timesteps=T, horizon=H)
        nfeatures = X.shape[-1]

        # Split (train-only scaling to avoid leakage)
        n = len(X); n_train = int(0.8 * n)
        X_tr, X_va = X[:n_train], X[n_train:]
        y_tr, y_va = y[:n_train], y[n_train:]

        xsc = MinMaxScaler().fit(X_tr.reshape(-1, X_tr.shape[-1]))
        ysc = MinMaxScaler().fit(y_tr)

        def transform_with_scalers(X_, y_):
            S, TT, F = X_.shape
            Xs_ = xsc.transform(X_.reshape(-1, F)).reshape(S, TT, F)
            ys_ = ysc.transform(y_)
            return Xs_, ys_

        X_train, y_train = transform_with_scalers(X_tr, y_tr)
        X_val,   y_val   = transform_with_scalers(X_va, y_va)
        y_val_inv = ysc.inverse_transform(y_val)

        # Data pipeline
        train_ds = make_ds(X_train, y_train, batch, shuffle=True, cache=True)
        val_ds   = make_ds(X_val,   y_val,   batch, shuffle=False, cache=True)

        # Model & callbacks
        seed = args.seed + H + T + units + layers + batch
        model = build_model(T, nfeatures, units=units, layers=layers,
                            dropout=args.dropout, lr=args.lr, huber=args.huber, seed=seed)

        cbs = [
            EarlyStopping(monitor="val_loss", mode="min",
                          patience=args.patience, min_delta=1e-4, restore_best_weights=True),
            ReduceLROnPlateau(monitor="val_loss", mode="min",
                              factor=0.5, patience=8, min_lr=1e-5, verbose=0)
        ]

        ckpt_path = ""
        if args.save_models:
            ckpt_path = f"best_H{H}_T{T}_U{units}_L{layers}_B{batch}.keras"
            cbs.insert(0, ModelCheckpoint(ckpt_path, save_best_only=True,
                                          monitor="val_loss", mode="min", verbose=0))

        # Warmup on a one-batch, no-cache dataset to avoid cache warning
        warmup_ds = make_ds(X_train[:batch], y_train[:batch], batch, shuffle=False, cache=False)
        model.fit(warmup_ds, epochs=1, verbose=0)

        # Train & time
        t0 = time.perf_counter()
        hist = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=cbs, verbose=args.verbose)
        t1 = time.perf_counter()

        # Predict & MAE (inverse-scaled)
        yhat = model.predict(val_ds, verbose=0)
        yhat_inv = ysc.inverse_transform(yhat)
        mae = float(np.mean(np.abs(y_val_inv - yhat_inv)))

        rec = {
            "H": H, "T": T, "units": units, "layers": layers, "batch": batch,
            "val_mae": mae,
            "epochs_ran": len(hist.history["loss"]),
            "train_time_sec": t1 - t0,
            "saved_model": ckpt_path
        }
        results.append(rec)
        print(f"H={H:2d} T={T:2d} U={units:3d} L={layers} B={batch:3d} "
              f"→ VAL_MAE={mae:.4f}  epochs={rec['epochs_ran']:3d}  time={rec['train_time_sec']:.1f}s")

    total_time = time.perf_counter() - total_start
    print(f"\nGrid complete in {total_time/60:.1f} minutes for {len(results)} runs.")

    df = pd.DataFrame(results).sort_values("val_mae", ascending=True).reset_index(drop=True)
    return df

# ---------------- Main ----------------
def main():
    p = argparse.ArgumentParser(description="Grid runner for stateless LSTM (GPU, mixed precision) with horizon grid.")
    p.add_argument("--climate_dir", type=str, default="data/Climate-Indices", help="Directory of climate index files")
    p.add_argument("--db_path",     type=str, default="/home/joe/Fire/Data/DB/era5DataMeans.db", help="SQLite DB path")
    p.add_argument("--point",       type=int, default=500, help="Point id from the DB")
    p.add_argument("--var",         type=str, default="VPD", help="Target variable column in DB")

    # Grids
    p.add_argument("--H",      type=str, default="8", help="Comma-sep horizons grid, e.g. '1,3,6,8,12'")
    p.add_argument("--T",      type=str, default="24,36,48", help="Comma-sep timesteps grid")
    p.add_argument("--units",  type=str, default="128,256,384", help="Comma-sep units grid")
    p.add_argument("--layers", type=str, default="1,2", help="Comma-sep layers grid")
    p.add_argument("--batch",  type=str, default="64,96,128", help="Comma-sep batch sizes grid")

    # Training knobs
    p.add_argument("--epochs",   type=int,   default=200, help="Max epochs")
    p.add_argument("--patience", type=int,   default=20,  help="Early stopping patience")
    p.add_argument("--lr",       type=float, default=2e-3, help="Adam learning rate")
    p.add_argument("--dropout",  type=float, default=0.0, help="Post-LSTM dropout (0.0–0.3)")
    p.add_argument("--huber",    action="store_true", help="Use Huber loss instead of MSE")
    p.add_argument("--seed",     type=int,   default=2025, help="Base random seed")
    p.add_argument("--verbose",  type=int,   default=0, help="Keras fit() verbosity (0/1/2)")

    # System / execution
    p.add_argument("--no_xla",     action="store_true", help="Disable XLA JIT")
    p.add_argument("--max_runs",   type=int, default=0, help="Limit number of runs from the grid (0 = no limit)")
    p.add_argument("--save_models", action="store_true", help="Save best model for each configuration")
    p.add_argument("--out_csv",    type=str, default="grid_results_horizons.csv", help="CSV file to write results")

    args = p.parse_args()

    setup_gpu(use_xla=not args.no_xla)

    # Load data
    climate = get_climate_indices(args.climate_dir)
    feats   = build_feature_matrix(climate, 1990, 2024, indices=("all",))
    df      = read_wx_data(args.db_path)
    target, yrmos, mos = select_wx_data(df, point=args.point, var=args.var)

    df_results = run_grid(args, feats, target)
    df_results.to_csv(args.out_csv, index=False)
    print(f"\nSaved: {args.out_csv}")
    print("\nTop 10 by VAL MAE:")
    print(df_results.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
