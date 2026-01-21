import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path

# ---------- helpers ----------
def make_shifted_target(y, horizon):
    return y.shift(-horizon).dropna()

def train_val_split(y, X=None, frac=0.8):
    split = int(len(y) * frac)
    y_tr, y_va = y.iloc[:split], y.iloc[split:]
    if X is not None:
        X_tr, X_va = X.iloc[:split], X.iloc[split:]
        return y_tr, y_va, X_tr, X_va
    return y_tr, y_va, None, None

def scale_exog_train_only(X_tr, X_va):
    mean, std = X_tr.mean(), X_tr.std().replace(0, 1.0)
    X_tr_s = (X_tr - mean) / std
    X_va_s = (X_va - mean) / std
    return X_tr_s, X_va_s

def fit_sarimax(y_tr, X_tr, order, sorder, m=12, enforce=False):
    model = sm.tsa.statespace.SARIMAX(
        y_tr,
        exog=X_tr,
        order=order,
        seasonal_order=sorder + (m,),
        enforce_stationarity=enforce,
        enforce_invertibility=enforce,
    )
    return model.fit(disp=False)

# ---------- main ----------
def main():
    # config
    csv_path = Path("full_data.csv")   # <-- your file
    target_col = "VPD"
    exog_cols = ["F1","F2","F3","F4","F5","F6"]  # if missing, we'll run without exog
    order  = (1, 0, 1)
    sorder = (1, 1, 1)
    m = 12
    train_frac = 0.8
    H_list = list(range(1, 13))  # horizons

    # data
    df = pd.read_csv(csv_path)
    # parse Yrmo robustly: 'YYYYMM' or 'YYYY-MM'
    df["Yrmo"] = pd.to_datetime(df["Yrmo"].astype(str).str.replace(r"\D", "", regex=True) + "01",
                                format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["Yrmo"]).set_index("Yrmo").sort_index()

    y = df[target_col].astype(float)
    # optional exog
    X_full = None
    if all(c in df.columns for c in exog_cols):
        X_full = df[exog_cols].astype(float)

    # fit/forecast per horizon
    all_forecasts = []
    for H in H_list:
        yH = make_shifted_target(y, H)
        if len(yH) < 24 + 12:  # minimal safety: need enough data
            continue
        if X_full is not None:
            XH = X_full.loc[yH.index]
        else:
            XH = None

        y_tr, y_va, X_tr, X_va = train_val_split(yH, XH, frac=train_frac)

        if X_tr is not None:
            X_tr_s, X_va_s = scale_exog_train_only(X_tr, X_va)
        else:
            X_tr_s, X_va_s = None, None

        res = fit_sarimax(y_tr, X_tr_s, order, sorder, m)

        pred = res.get_prediction(start=y_va.index[0], end=y_va.index[-1], exog=X_va_s)
        yhat = pred.predicted_mean.reindex(y_va.index)

        df_h = pd.DataFrame({
            "Yrmo": y_va.index.strftime("%Y-%m"),
            "Observed": y_va.values.astype(float),
            "Forecast": yhat.values.astype(float),
            "Horizon": H
        })
        all_forecasts.append(df_h)

    if not all_forecasts:
        raise RuntimeError("No forecasts produced (insufficient data or configuration).")

    out = pd.concat(all_forecasts, ignore_index=True)
    out.to_csv("forecast_results_sarima_test.csv", index=False)
    print("✅ Saved forecast_results_sarima_test.csv")

if __name__ == "__main__":
    main()
