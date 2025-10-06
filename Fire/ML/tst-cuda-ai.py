# tst-cuda-ensemble.py
from pickle import load
import os, time, csv,numpy as np, pandas as pd, sqlite3, tensorflow as tf
from tensorflow.keras import mixed_precision
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Input
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import MinMaxScaler

# ---------------- GPU / Mixed Precision ----------------
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
mixed_precision.set_global_policy("mixed_float16")     # Tensor Cores on RTX 3080
tf.config.optimizer.set_jit(True)                      # try XLA; disable if it regresses

gpus = tf.config.list_physical_devices("GPU")
if gpus:
    try:
        tf.config.set_visible_devices(gpus[0], "GPU")
        tf.config.experimental.set_memory_growth(gpus[0], True)
        print("Using GPU:", gpus[0])
    except Exception as e:
        print("GPU config warning:", e)
else:
    print("No GPU found. Running on CPU.")

# ---------------- Data helpers (trimmed) ----------------
def readWxData(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("select * from MEANS_TTdRHVPD", conn)
    conn.close()
    return df

def selectWxData(df, point, var="VPD"):
    sub = df.loc[df["Point"] == point].copy()
    yrmos = sub["Yrmo"].astype(int).values
    mos   = sub["Yrmo"].str[4:6].astype(int).values
    target = sub[[var]].astype(float).values   # (N,1)
    return target, yrmos, mos

def getClimateIndices(directory):
    features = {}
    with os.scandir(directory) as entries:
        for entry in entries:
            if not entry.is_file(): continue
            file = entry.name.rstrip("\n")
            if "Zone.Identifier" in file: continue
            path = f"{directory}/{file}"
            # quick validation
            ok = True
            with open(path, "r") as fin:
                spl = fin.readline().split()
                start, end = int(spl[0]), int(spl[1])
                for _ in range(start, end + 1):
                    spl = fin.readline().split()
                    if not spl: break
                    year = int(spl[0])
                    if 1949 < year < 2024:
                        for mon in range(1, 13):
                            if float(spl[mon]) < -30:
                                ok = False; break
                    if not ok: break
            if not ok: 
                print("SKIP outlier file:", file); 
                continue
            # ingest
            name = ".".join(file.split(".")[:-1])
            with open(path, "r") as fin:
                spl = fin.readline().split()
                start, end = int(spl[0]), int(spl[1])
                for _ in range(start, end + 1):
                    spl = fin.readline().split()
                    if not spl: break
                    year = int(spl[0]); features.setdefault(year, {})
                    for mon in range(1, 13):
                        features[year].setdefault(mon, {})
                        features[year][mon][name] = float(spl[mon])
    return features

def getIndices(climate, start, end, indices=["all"]):
    features, features4Pbi, noUse, indicesToUse = [], [], {}, {}
    # mark bad indices in 1990-2024
    for year, dct in climate.items():
        if 1989 < year < 2025:
            for _, dct2 in dct.items():
                for ds, val in dct2.items():
                    if val < -30:
                        noUse[ds] = noUse.get(ds, 0) + 1
    for year in range(start, end + 1):
        dct = climate[year]
        for month, dct2 in dct.items():
            row_vals, row_all = [], [year, month, f"{year}{str(month).zfill(2)}01"]
            for name, val in sorted(dct2.items()):
                if (indices[0]=="all" or name in indices) and (name not in noUse):
                    row_vals.append(val); row_all.append(val)
                    indicesToUse[name] = indicesToUse.get(name, 0) + 1
            features.append(row_vals); features4Pbi.append(row_all)
    return features, indicesToUse, features4Pbi

# ---------------- Supervised windows ----------------
def build_windows(features, target, timesteps=24, forecast_horizon=8):
    F = np.asarray(features, dtype=np.float32)
    y = np.asarray(target, dtype=np.float32).reshape(-1,1)
    F_shift, y_shift = F[forecast_horizon:], y[:-forecast_horizon]
    X, Y = [], []
    for i in range(timesteps, len(F_shift)):
        X.append(F_shift[i - timesteps:i]); Y.append(y_shift[i])
    return np.stack(X,0), np.stack(Y,0)  # X:(M,T,F), Y:(M,1)

# ---------------- Scaling ----------------
def scale_featurewise(X, y):
    S, T, F = X.shape
    x_scaler = MinMaxScaler()
    y_scaler = MinMaxScaler()
    Xs = x_scaler.fit_transform(X.reshape(-1, F)).reshape(S, T, F)
    ys = y_scaler.fit_transform(y)
    return Xs, ys, x_scaler, y_scaler

# ---------------- Datasets ----------------
def make_ds(X, y, bs, stateful=False, shuffle=True):
    ds = tf.data.Dataset.from_tensor_slices((X, y))
    if shuffle: ds = ds.shuffle(min(8192, len(X)))
    return ds.batch(bs, drop_remainder=stateful).cache().prefetch(tf.data.AUTOTUNE)

# ---------------- Models ----------------
def build_model_stateless(timesteps, nfeatures, units=150, lr=2e-3, seed=None):
    if seed is not None:
        tf.keras.utils.set_random_seed(seed)
    m = Sequential([
        Input(shape=(timesteps, nfeatures)),
        LSTM(units, stateful=False),                 # cuDNN path (defaults)
        Dense(1, dtype="float32")                    # stable fp32 loss under mixed precision
    ])
    m.compile(optimizer=tf.keras.optimizers.Adam(lr), loss="mse")
    return m

def build_model_stateful(batch_size, timesteps, nfeatures, units=150, lr=2e-3, seed=None):
    if seed is not None:
        tf.keras.utils.set_random_seed(seed)
    m = Sequential([
        Input(batch_shape=(batch_size, timesteps, nfeatures)),
        LSTM(units, stateful=True),
        Dense(1, dtype="float32")
    ])
    m.compile(optimizer=tf.keras.optimizers.Adam(lr), loss="mse")
    return m

# ---------------- Main ----------------
def main():
    # 1) Load & features
    climate = getClimateIndices("Data/Climate-Indices")
    feats, _, _ = getIndices(climate, 1990, 2024, ["all"])
    df = readWxData("Data/DB/era5DataMeans.db")
    target, yrmos, mos = selectWxData(df, point=500, var="VPD")
 #   load = "best_run4.keras"
    load = None
   # feats.to_csv("feats.csv")
   
    # with open("feats.csv", "w", newline="", encoding="utf-8") as f:
    #      writer = csv.writer(f)
    #      writer.writerows(feats)
    tmpdf = df.loc[df["Point"] == 500]
    tmpdf.reset_index(drop=True, inplace=True)
    featdDf = pd.DataFrame(feats,columns=["F1","F2","F3","F4","F5","F6"])
    tmpdf = tmpdf.join(featdDf)
    tmpdf.to_csv("full_data.csv",index=False)
    # 2) Windows
    TIMESTEPS, HZ = 24, 8
    X, y = build_windows(feats, target, timesteps=TIMESTEPS, forecast_horizon=HZ)
    print("X shape:", X.shape, " y shape:", y.shape)
    nfeatures = X.shape[-1]

    # 3) Scale once
    Xs, ys, xsc, ysc = scale_featurewise(X, y)

    # 4) Split
    n = len(Xs); n_train = int(0.8 * n)
    X_train, X_val = Xs[:n_train], Xs[n_train:]
    y_train, y_val = ys[:n_train], ys[n_train:]

    # 5) Config (stateful or stateless)
    STATEFUL = False
    BATCH = 64 if not STATEFUL else 48

    if STATEFUL:
        def trim(a, b): return a[: (len(a)//b)*b]
        X_train, y_train = trim(X_train, BATCH), trim(y_train, BATCH)
        X_val,   y_val   = trim(X_val,   BATCH), trim(y_val,   BATCH)
        train_ds = make_ds(X_train, y_train, BATCH, stateful=True, shuffle=False)
        val_ds   = make_ds(X_val,   y_val,   BATCH, stateful=True, shuffle=False)
    else:
        train_ds = make_ds(X_train, y_train, BATCH, stateful=False, shuffle=True)
        val_ds   = make_ds(X_val,   y_val,   BATCH, stateful=False, shuffle=False)

    # 6) Callbacks template
    def callbacks_for(run_id):
        return [
            ModelCheckpoint(f"best_run{run_id}.keras", save_best_only=True,
                            monitor="val_loss", mode="min", verbose=0),
            EarlyStopping(patience=20, restore_best_weights=True,
                          monitor="val_loss", mode="min"),
            ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                              patience=8, min_lr=1e-5, verbose=0)
        ]

    # 7) Ensemble runs (sequential on the same GPU)
    N_RUNS = 10
    UNITS  = 250
    LR     = 2e-3

    run_times = []
    run_maes  = []
    preds_val = []   # store inverse-transformed predictions per run

    print(f"\nStarting {N_RUNS}-member ensemble on GPU...")
    t_ens0 = time.perf_counter()
    print("TRAIN dS ",train_ds)
    for run_id in range(N_RUNS):
        seed = 1234 + run_id
        if not load: 
            if STATEFUL:
                model = build_model_stateful(BATCH, TIMESTEPS, nfeatures, units=UNITS, lr=LR, seed=seed)
            else:
                model = build_model_stateless(TIMESTEPS, nfeatures, units=UNITS, lr=LR, seed=seed)
        else:
            model = tf.keras.models.load_model(load, compile=True)
        # Warmup (stabilizes timing)
        model.fit(train_ds.take(1), epochs=1, verbose=0)

        t0 = time.perf_counter()
        history = model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=300,
            callbacks=callbacks_for(run_id),
            verbose=0
        )
        t1 = time.perf_counter()
        run_times.append(t1 - t0)

        # Load best weights and predict
        best = tf.keras.models.load_model(f"best_run{run_id}.keras", compile=False)
        best.compile(optimizer=tf.keras.optimizers.Adam(LR), loss="mse")
        yhat = best.predict(val_ds, verbose=0)

        # inverse-transform for reporting
        y_val_inv  = ysc.inverse_transform(y_val)
        yhat_inv   = ysc.inverse_transform(yhat)
        mae = float(np.mean(np.abs(y_val_inv - yhat_inv)))
        run_maes.append(mae)
        preds_val.append(yhat_inv)  # shape (M,1)

        print(f"Run {run_id+1:02d}/{N_RUNS}: fit_time={run_times[-1]:.2f}s  VAL_MAE={mae:.4f}")

    t_ens1 = time.perf_counter()
    print(f"\nEnsemble total fit time: {t_ens1 - t_ens0:.2f}s "
          f"(avg/run {np.mean(run_times):.2f}s)")

    # 8) Ensemble aggregation (mean & median)
    P = np.stack(preds_val, axis=2)          # (M, 1, N_RUNS)
    ens_mean = np.mean(P, axis=2)            # (M, 1)
    ens_median = np.median(P, axis=2)        # (M, 1)

    ens_mean_mae   = float(np.mean(np.abs(y_val_inv - ens_mean)))
    ens_median_mae = float(np.mean(np.abs(y_val_inv - ens_median)))

    print(f"Ensemble MEAN  MAE: {ens_mean_mae:.4f}")
    print(f"Ensemble MEDIAN MAE: {ens_median_mae:.4f}")

if __name__ == "__main__":
    main()
