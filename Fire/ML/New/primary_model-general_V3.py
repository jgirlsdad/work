import sqlite3
import pandas as pd
import duckdb
import numpy as np

import numpy as np
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from tensorflow.keras import layers, regularizers
from tensorflow.keras.callbacks import EarlyStopping
import pandas as pd
import pickle
# ============================================================
# CONFIG
# ============================================================
path = "/home/joe/work/Fire/ML/Data"
path_clim = "/home/joe/work/Fire/ML/Data/Climate-Indices/New"

ERA_DB = f"{path}/DB/era5MonthlyMeansFinal.sqlite"
ERA_TABLE = "monthly_means"

CLIMATE_DB = f"{path_clim}/climate_indices.db"
CLIMATE_TABLE = "indices"

POINT_META_CSV = f"{path}/latlon_elevation.csv"
#T_VAR = "T"
#T_VAR = "Td"
T_VAR = "RH"
#T_VAR = "VPD"

columns = {"T":"t_mean", "Td":"td_mean", "RH":"rh_mean", "VPD":"vpd_mean"}

TARGET_VAR = columns[T_VAR]
TRAIN_CLIMO_START_YM = 1990 * 12 + 1
TRAIN_CLIMO_END_YM   = 2015 * 12 + 12

# Leads
LEADS = list(range(1, 13))

# Lags applied to ALL dynamic predictors
LAG_MONTHS = [0,1,2,3,6,24]
# LAG_MONTHS = list(range(0, 7))

# Train / test split
TEST_START_YM = 2016 * 12 + 1


## Define Grid
GRID_RADIUS_DEG = 0.21
LATT = 41.0
LATB = 37.0
LONL = -109.0+360
LONR = -102.0+360
R = .1
STEP = 5

# ============================================================
# GLOBAL LOADERS
# ============================================================
def load_era_global():
    con = duckdb.connect(ERA_DB)
    df = con.execute(f"SELECT * FROM {ERA_TABLE}").df()
    con.close()

    df["year_month"] = df["year_month"].astype(int)
    df["year"] = df["year_month"] // 100
    df["month"] = df["year_month"] % 100
    df["ym_index"] = df["year"] * 12 + df["month"]

    return df


def load_indices_global():
    conn = sqlite3.connect(CLIMATE_DB)
    idx = pd.read_sql(f"SELECT * FROM {CLIMATE_TABLE}", conn)
    conn.close()
    return idx


def load_metadata_global():
    meta = pd.read_csv(POINT_META_CSV)
    meta = meta.rename(columns={
        "point": "point_id",
        "latitude": "lat",
        "longitude": "lon",
        "elevation_m": "elevation"
    })
    return meta


def extract_mesh(df_full, center_lat, center_lon, spacing=0.1, radius=2):

    delta = spacing * radius + .01

    df_mesh = df_full[
        (df_full["lat"] >= center_lat - delta) &
        (df_full["lat"] <= center_lat + delta) &
        (df_full["lon"] >= center_lon - delta) &
        (df_full["lon"] <= center_lon + delta)
    ].copy()
    print(f"Extracted mesh around ({center_lat}, {center_lon}) with {len(df_mesh['point_id'].unique())} unique points." )
    return df_mesh


def getCenterPoints(R, latT,latB,lonL,lonR,STEP=5):
    # Grid definition
    lat_vals = np.round(np.arange(latT, latB -R, -R), 1)
    lon_vals = np.round(np.arange(lonL, lonR + R, R), 1)

    lat_core = lat_vals[2:-2]   # drop top 2 + bottom 2
    lon_core = lon_vals[2:-2]   # drop left 2 + right 2

    lat_centers = lat_core[::STEP]
    lon_centers = lon_core[::STEP]

    mesh_centers = []

    for lat in lat_centers:
        for lon in lon_centers:
            mesh_centers.append((lat, lon))

    return mesh_centers

def add_seasonality(df):
    df["sin_month"] = np.sin(2 * np.pi * df["month"] / 12)
    df["cos_month"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


def add_lags(df,DYNAMIC_FEATURES):
    print("Adding lags for features:", DYNAMIC_FEATURES)
    print(df.head())
    df.rename(columns={"point_id_x": "point_id"}, inplace=True)
    df = df.sort_values(["point_id", "ym_index"])

    for feature in DYNAMIC_FEATURES:
        for lag in LAG_MONTHS:
            df[f"{feature}_lag{lag}"] = (
                df.groupby("point_id")[feature].shift(lag)
            )

    print("Laggs Finished")
    return df


def build_forecast(df, DYNAMIC_FEATURES):

    print("Building forecast table (vectorized)...")
    print("SHAPE ", df.shape)

    # Lagged columns (same as before)
    lagged_cols = [
        f"{feat}_lag{lag}"
        for feat in DYNAMIC_FEATURES
        for lag in LAG_MONTHS
    ]

    # Sort once
    df = df.sort_values(["point_id", "ym_index"]).copy()

    all_leads = []

    for lead in LEADS:

        df_shift = df.copy()

        # 🔥 FIX: groupby on df_shift, NOT df
        g = df_shift.groupby("point_id")

        df_shift["target_ym"] = g["ym_index"].shift(-lead)
        df_shift["y"] = g["T_anom"].shift(-lead)
        df_shift["target_year"] = g["year"].shift(-lead)
        df_shift["target_month"] = g["month"].shift(-lead)

        df_shift["lead"] = lead

        all_leads.append(df_shift)

    # Stack all leads
    forecast_df = pd.concat(all_leads, ignore_index=True)

    # Issue fields
    forecast_df["issue_ym"] = forecast_df["ym_index"]
    forecast_df["issue_year"] = forecast_df["year"]
    forecast_df["issue_month"] = forecast_df["month"]

    # Final column structure (unchanged)
    base_cols = [
        "point_id",
        "issue_ym",
        "lead",
        "target_ym",
        "y",
        "lat",
        "lon",
        "elevation",
        "sin_month",
        "cos_month",
        "issue_year",
        "issue_month",
        "target_year",
        "target_month",
    ]

    forecast_df = forecast_df[base_cols + lagged_cols]

    # Drop rows with missing targets or lag features
    forecast_df = forecast_df.dropna(subset=["y"] + lagged_cols).reset_index(drop=True)

    print("Forecast table built with shape:", forecast_df.shape)

    return forecast_df, lagged_cols


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

def train_test_split(forecast_df, lagged_cols):

    feature_cols = (
        lagged_cols +
        ["lead", "lat", "lon", "elevation", "sin_month", "cos_month"]
    )

    train_df = forecast_df[forecast_df.issue_ym < TEST_START_YM].copy()
    test_df  = forecast_df[forecast_df.issue_ym >= TEST_START_YM].copy()

    X_train = train_df[feature_cols].copy()
    y_train = train_df["y"].copy()

    X_test  = test_df[feature_cols].copy()
    y_test  = test_df["y"].copy()

    return X_train, X_test, y_train, y_test, train_df, test_df


def prepare_mesh_dataset(df_full, index_cols, center_lat, center_lon, target_var):
    df = extract_mesh(df_full, center_lat, center_lon, spacing=R, radius=2)

    DYNAMIC_FEATURES = ["T_anom"] + list(index_cols)
    print("DF DF DF ",df.head())
    por_stats = df.groupby(["point_id","month"])[target_var].agg(["mean", "std"]).reset_index()

    #climo = compute_climatology(df)
   
    df = df.merge(por_stats, on=["point_id","month"], how="left")
    df["T_anom"] = df[TARGET_VAR] - df["mean"]
    df = add_seasonality(df)
    df = add_lags(df, DYNAMIC_FEATURES)

    forecast_df, lagged_cols = build_forecast(df, DYNAMIC_FEATURES)

    return train_test_split(forecast_df, lagged_cols), por_stats, df, forecast_df, DYNAMIC_FEATURES


# ============================================================
# GLOBAL PREP
# ============================================================
def prepare_global_data():
    era = load_era_global()
    idx = load_indices_global()
    meta = load_metadata_global()

    index_cols = idx.drop(columns=["yrmo"]).columns.tolist()

    df_full = era.merge(idx, left_on="year_month", right_on="yrmo", how="left")
    df_full = df_full.drop(columns=["yrmo"])

    df_full = df_full.merge(meta, on="point_id", how="left")

    return df_full, index_cols

####################################################################

# NEURAL NETOWRK MODEL

#####################################################################



def run_nn_single_model(
    X_train, y_train,
    X_test, y_test,
    por_std_by_month,
    test_df
):

    # =========================
    # SCALE
    # =========================
    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_train.values)
    X_te = scaler.transform(X_test.values)

    y_tr = y_train.values
    y_te = y_test.values

    # =========================
    # MODEL (UNCHANGED)
    # =========================
    model = tf.keras.Sequential([
        layers.Dense(
            128,
            activation="relu",
            kernel_regularizer=regularizers.l2(0.0005),
            input_shape=(X_tr.shape[1],)
        ),
        layers.Dense(
            64,
            activation="relu",
            kernel_regularizer=regularizers.l2(0.0005)
        ),
        layers.Dense(1)
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0005),
        loss="mae"
    )

    # =========================
    # TRAIN (THIS WAS MISSING)
    # =========================
    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=5,
        restore_best_weights=True
    )

    model.fit(
        X_tr, y_tr,
        validation_data=(X_te, y_te),
        epochs=50,
        batch_size=256,
        callbacks=[early_stop],
        verbose=1
    )

    # =========================
    # PREDICT
    # =========================
    preds = model.predict(X_te, verbose=0).flatten()

    # =========================
    # OVERALL METRIC
    # =========================
    mae = np.mean(np.abs(preds - y_te))
    print(f"\nOverall MAE: {mae:.3f}")

    # =========================
    # MONTHLY BREAKDOWN (UNCHANGED LOGIC)
    # =========================
    results = {}

    for month in range(1, 13):

        mask = test_df["target_month"] == month

        if mask.sum() < 50:
            continue

        y_m = y_te[mask]
        p_m = preds[mask]

        mae_m = np.mean(np.abs(p_m - y_m))
        mae_norm_std = mae_m / por_std_by_month[month]['std']

        results[month] = {
            "mae": float(mae_m),
            "mae_norm_std": float(mae_norm_std),
            "n": int(len(y_m))
        }

        print(
            f"Month {month:02d} | "
            f"MAE {mae_m:.3f} | "
            f"MAE/STD {mae_norm_std:.3f}"
        )

    return results, model, scaler

#####################################################################

# RUNNING THE MESH FORECAST

######################################################################


# ============================================================
# RUN
# ============================================================
import pickle as pkl


df_full, index_cols = prepare_global_data()
centerPoints = getCenterPoints(R,LATT,LATB,LONL,LONR,STEP)
print(df_full.shape)
print(index_cols)
print(df_full.columns.tolist())
print(df_full.head())

ncenter=0
mesh_predictions = []


for center_lat, center_lon in centerPoints:
    ncenter+=1
    print(f"\n\n=== Processing mesh centered at lat {center_lat}, lon {center_lon} (Mesh {ncenter}/{len(centerPoints)}) ===")
    (X_train, X_test, y_train, y_test, train_df, test_df), por_stats, df_mesh, forecast_df, DYNAMIC_FEATURES = \
        prepare_mesh_dataset(df_full, index_cols, center_lat, center_lon, TARGET_VAR)
    por_stats_dict = {
        int(row['month']): {'mean': row['mean'], 'std': row['std']}
        for _, row in por_stats.iterrows()
    }

    print("X_train shape:", X_train.shape)
    print("TRAINING MODEL FOR THIS MESH...")
    nn_results, model, scaler = run_nn_single_model(
        X_train, y_train,
        X_test, y_test,
        por_stats_dict,
        test_df
    )
    print("MODEL TRAINING COMPLETED FOR THIS MESH.")
    # ---------------------------------------
# FORECAST STEP (per mesh)
# ---------------------------------------

    latest_issue = test_df["issue_ym"].max()

    # ---------------------------------------
# FORECAST STEP (REAL FIX)
# ---------------------------------------

    ISSUE_YM = df_mesh["ym_index"].max()

    model.save(f"Models/nn_model_{T_VAR}_{center_lat:4.1f}_{center_lon:4.1f}.h5")
    with open(f"scaler_{T_VAR}_{center_lat:4.1f}_{center_lon:4.1f}.pkl", "wb") as f:
        pkl.dump(scaler, f)

    # Precompute feature columns (same as training)
    feature_cols = (
        [f"{feat}_lag{lag}" for feat in DYNAMIC_FEATURES for lag in LAG_MONTHS]
        + ["lead", "lat", "lon", "elevation", "sin_month", "cos_month"]
    )

    for pid in df_mesh["point_id"].unique():

        print(f"Predicting for point_id {pid} at center ({center_lat}, {center_lon})")

        # 1. Get latest row for this point (March 2026)
        df_point = df_mesh[
            (df_mesh["point_id"] == pid) &
            (df_mesh["ym_index"] == ISSUE_YM)
        ].copy()

        if df_point.empty:
            continue

        # 2. Expand to 12 leads
        rows = []
        for lead in LEADS:
            tmp = df_point.copy()
            tmp["lead"] = lead
            rows.append(tmp)

        df_pred = pd.concat(rows, ignore_index=True)

        # 3. Build feature matrix
        X_pred = df_pred[feature_cols]

        # 4. Predict
        preds = model.predict(scaler.transform(X_pred), verbose=0).flatten()

        df_pred["prediction"] = preds
        df_pred["issue_ym"] = ISSUE_YM
        df_pred["target_ym"] = df_pred["issue_ym"] + df_pred["lead"]

        # Convert internal ym_index to calendar year/month for forecast validity period.
        target_ym_zero = df_pred["target_ym"] - 1
        df_pred["target_year"] = (target_ym_zero // 12).astype(int)
        df_pred["target_month"] = ((target_ym_zero % 12) + 1).astype(int)
        df_pred["year_month"] = (
            df_pred["target_year"] * 100 + df_pred["target_month"]
        ).astype(int)

        mesh_predictions.append(df_pred)

    # Combine all 25 points
#    df_mesh_forecast = pd.concat(mesh_predictions, ignore_index=True)

    # if ncenter > 3:
    #     break

df_mesh_forecast = pd.concat(mesh_predictions, ignore_index=True)
df_mesh_forecast['VAR'] = T_VAR
df_mesh_forecast.to_csv(f"mesh_forecast_{T_VAR}.csv", index=False)
