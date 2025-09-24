#!/usr/bin/env python3
# sarima_vs_lstm.py
"""
Fit SARIMA/SARIMAX baselines for one or more forecast horizons (H) on your VPD series.
- Uses same data sources as your LSTM scripts.
- Supports exogenous climate indices (contemporaneous with t) via SARIMAX.
- Train-only scaling for exog (no leakage).
- Outputs a CSV with MAE per horizon and (optionally) a side-by-side with LSTM results if present.
"""

import os, argparse, sqlite3, warnings
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
warnings.filterwarnings("ignore")
import statsmodels.api as sm

def read_wx_data(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("select * from MEANS_TTdRHVPD", conn)
    conn.close()
    return df

def select_wx_data(df, point, var="VPD"):
    sub = df.loc[df["Point"] == point].copy()
    if sub.empty:
        raise ValueError(f"No rows for Point={point}.")
    yrmo = sub["Yrmo"].astype(str).str[:6]
    idx = pd.PeriodIndex(yrmo, freq="M").to_timestamp()
    y = sub[[var]].astype(float).set_index(idx).sort_index()
    y = y.rename(columns={var: "y"})
    return y

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
            ok = True
            with open(path, "r") as fin:
                spl = fin.readline().split()
                if not spl: continue
                start, end = int(spl[0]), int(spl[1])
                for _ in range(start, end + 1):
                    spl = fin.readline().split()
                    if not spl: break
                    y = int(spl[0])
                    if 1949 < y < 2024:
                        for m in range(1, 13):
                            if float(spl[m]) < -30:
                                ok = False; break
                    if not ok: break
            if not ok:
                continue
            name = ".".join(file.split(".")[:-1])
            with open(path, "r") as fin:
                spl = fin.readline().split()
                if not spl: continue
                start, end = int(spl[0]), int(spl[1])
                for _ in range(start, end + 1):
                    spl = fin.readline().split()
                    if not spl: break
                    year = int(spl[0])
                    for mon in range(1, 13):
                        val = float(spl[mon])
                        features.setdefault(year, {}).setdefault(mon, {})[name] = val
    rows = []
    for y, d in features.items():
        for m, d2 in d.items():
            ts = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)
            row = {"date": ts}
            row.update(d2)
            rows.append(row)
    feats = pd.DataFrame(rows).set_index("date").sort_index()
    return feats

def align_exog(features_df, target_df):
    df = target_df.join(features_df, how="left")
    df = df.dropna()
    y = df[["y"]].copy()
    X = df.drop(columns=["y"]).copy()
    return y, X

def make_shifted_target(y: pd.DataFrame, H: int):
    yH = y.shift(-H).dropna()
    yH = yH.rename(columns={"y": f"y_H{H}"})
    return yH

def train_val_split(y: pd.DataFrame, X: pd.DataFrame = None, frac=0.8):
    n = len(y); n_tr = int(n * frac)
    y_tr, y_va = y.iloc[:n_tr], y.iloc[n_tr:]
    if X is None: return y_tr, y_va, None, None
    X = X.loc[y.index]
    X_tr, X_va = X.iloc[:n_tr], X.iloc[n_tr:]
    return y_tr, y_va, X_tr, X_va

def scale_exog_train_only(X_tr: pd.DataFrame, X_va: pd.DataFrame):
    xsc = MinMaxScaler().fit(X_tr.values)
    Xtr_s = pd.DataFrame(xsc.transform(X_tr.values), index=X_tr.index, columns=X_tr.columns)
    Xva_s = pd.DataFrame(xsc.transform(X_va.values), index=X_va.index, columns=X_va.columns)
    return Xtr_s, Xva_s, xsc

def fit_sarimax(y_tr: pd.DataFrame, X_tr: pd.DataFrame, order, sorder, m, enforce=False):
    model = sm.tsa.statespace.SARIMAX(
        endog=y_tr.squeeze(),
        exog=X_tr if X_tr is not None else None,
        order=order,
        seasonal_order=(sorder[0], sorder[1], sorder[2], m),
        enforce_stationarity=enforce,
        enforce_invertibility=enforce
    )
    res = model.fit(disp=False)
    return res

def forecast_mae(model_res, y_va: pd.DataFrame, X_va: pd.DataFrame):
    pred = model_res.get_prediction(start=y_va.index[0], end=y_va.index[-1], exog=X_va if X_va is not None else None)
    yhat = pred.predicted_mean.reindex(y_va.index)
    mae = float(np.mean(np.abs(y_va.squeeze() - yhat)))
    return mae, yhat

def main():
    p = argparse.ArgumentParser(description="SARIMA/SARIMAX comparison for multiple horizons.")
    p.add_argument("--climate_dir", type=str, default="data/Climate-Indices")
    p.add_argument("--db_path",     type=str, default="/home/joe/Fire/Data/DB/era5DataMeans.db")
    p.add_argument("--point",       type=int, default=500)
    p.add_argument("--var",         type=str, default="VPD")
    p.add_argument("--H",           type=str, default="8")
    p.add_argument("--orders",      type=str, default="1,1,1")
    p.add_argument("--sorders",     type=str, default="1,1,1")
    p.add_argument("--m",           type=int, default=12)
    p.add_argument("--exog",        type=str, default="none", choices=["none", "climate"])
    p.add_argument("--train_frac",  type=float, default=0.8)
    p.add_argument("--out_csv",     type=str, default="sarima_results.csv")
    p.add_argument("--lstm_csv",    type=str, default="")
    args = p.parse_args()

    H_list = [int(x) for x in args.H.split(",")]
    order = tuple(int(x) for x in args.orders.split(","))
    sorder = tuple(int(x) for x in args.sorders.split(","))

    df = read_wx_data(args.db_path)
    y = select_wx_data(df, point=args.point, var=args.var)

    X_full = None
    if args.exog == "climate":
        feats = get_climate_indices(args.climate_dir)
        y, X_full = align_exog(feats, y)

    rows = []
    for H in H_list:
        yH = make_shifted_target(y, H)
        XH = X_full.loc[yH.index] if X_full is not None else None
        y_tr, y_va, X_tr, X_va = train_val_split(yH, XH, frac=args.train_frac)
        if X_tr is not None:
            X_tr_s, X_va_s, _ = scale_exog_train_only(X_tr, X_va)
        else:
            X_tr_s = X_va_s = None

        try:
            res = fit_sarimax(y_tr, X_tr_s, order=order, sorder=sorder, m=args.m, enforce=False)
            mae, yhat = forecast_mae(res, y_va, X_va_s)
            aic = float(res.aic)
            rows.append({"H": H, "order": order, "sorder": sorder, "m": args.m,
                         "exog": args.exog, "val_mae": mae, "aic": aic})
            print(f"H={H:2d}  SARIMA{order}x{sorder}{args.m}  exog={args.exog:<7}  → VAL_MAE={mae:.4f}  AIC={aic:.1f}")
        except Exception as e:
            rows.append({"H": H, "order": order, "sorder": sorder, "m": args.m,
                         "exog": args.exog, "val_mae": np.nan, "aic": np.nan, "error": str(e)})
            print(f"H={H:2d} failed: {e}")

    sarima_df = pd.DataFrame(rows).sort_values(["H", "val_mae"]).reset_index(drop=True)
    sarima_df.to_csv(args.out_csv, index=False)
    print(f"\nSaved SARIMA results → {args.out_csv}")

    if args.lstm_csv and os.path.exists(args.lstm_csv):
        try:
            lstm = pd.read_csv(args.lstm_csv)
            if "H" in lstm.columns and "val_mae" in lstm.columns:
                lstm_best = lstm.sort_values(["H", "val_mae"]).groupby("H", as_index=False).first()[["H", "val_mae"]]
                lstm_best = lstm_best.rename(columns={"val_mae": "lstm_val_mae"})
                comp = sarima_df.merge(lstm_best, on="H", how="left")
                comp["lstm_vs_sarima_delta"] = comp["lstm_val_mae"] - comp["val_mae"]
                comp.to_csv("sarima_vs_lstm.csv", index=False)
                print("Saved side-by-side → sarima_vs_lstm.csv")
        except Exception as e:
            print(f"Could not build LSTM comparison: {e}")
    else:
        if args.lstm_csv:
            print(f"LSTM CSV '{args.lstm_csv}' not found; skipping comparison.")

if __name__ == "__main__":
    main()
