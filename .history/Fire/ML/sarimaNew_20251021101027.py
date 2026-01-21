import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path

def fit_sarimax(y, X, order, sorder, m, enforce=False):
    """Fit SARIMA model and return fitted result."""
    model = sm.tsa.statespace.SARIMAX(
        y,
        exog=X,
        order=order,
        seasonal_order=sorder + (m,),
        enforce_stationarity=enforce,
        enforce_invertibility=enforce,
    )
    return model.fit(disp=False)

def rolling_forecast(df, target_col, exog_cols=None, order=(1,0,1), sorder=(1,1,1),
                     m=12, train_frac=0.8, H_max=12, enforce=False):
    """Perform rolling-origin SARIMA forecast (refitting at each step)."""
    df = df.copy()
    df["Yrmo"] = pd.to_datetime(df["Yrmo"].astype(str).str.replace(r"\D", "", regex=True) + "01",
                                format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["Yrmo"]).set_index("Yrmo").sort_index()

    y_full = df[target_col].astype(float)
    X_full = df[exog_cols].astype(float) if exog_cols else None

    n_train = int(len(y_full) * train_frac)
    train_end_dates = y_full.index[n_train:-H_max]  # rolling origins
    all_results = []

    for origin in train_end_dates:
        # define train window
        y_train = y_full.loc[:origin]
        X_train = X_full.loc[:origin] if X_full is not None else None

        # fit model
        try:
            res = fit_sarimax(y_train, X_train, order, sorder, m, enforce)
        except Exception as e:
            print(f"⚠️ Skipping origin {origin.strftime('%Y-%m')} due to fitting error: {e}")
            continue

        # forecast next H_max months
        forecast_index = pd.date_range(origin + pd.offsets.MonthBegin(1), periods=H_max, freq="MS")
        X_fore = X_full.loc[forecast_index] if X_full is not None else None

        try:
            pred = res.get_forecast(steps=H_max, exog=X_fore)
            yhat = pred.predicted_mean
        except Exception as e:
            print(f"⚠️ Forecast failed at origin {origin.strftime('%Y-%m')}: {e}")
            continue

        # collect valid targets that exist in actual data
        valid_targets = forecast_index.intersection(y_full.index)
        for target in valid_targets:
            H = (target.year - origin.year) * 12 + (target.month - origin.month)
            all_results.append({
                "Origin": origin.strftime("%Y-%m"),
                "Target": target.strftime("%Y-%m"),
                "Horizon": H,
                "Observed": y_full.loc[target],
                "Forecast": yhat.loc[target] if target in yhat.index else np.nan,
            })

    out = pd.DataFrame(all_results)
    return out


def main():
    csv_path = Path("full_data.csv")  # your input file
    target_col = "VPD"
    exog_cols = ["F1","F2","F3","F4","F5","F6"]
    order  = (1, 0, 1)
    sorder = (1, 1, 1)
    m = 12
    train_frac = 0.8
    H_max = 12

    df = pd.read_csv(csv_path)
    results = rolling_forecast(
        df, target_col, exog_cols, order, sorder, m,
        train_frac=train_frac, H_max=H_max
    )

    results.to_csv("forecast_results_sarima_rolling.csv", index=False)
    print("✅ Saved forecast_results_sarima_rolling.csv")
    print(results.head(12))


if __name__ == "__main__":
    main()
