# mylab/forecasting.py
import pandas as pd, numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
from statsmodels.tsa.statespace.sarimax import SARIMAX
from tool_registry import tool

@tool(
  summary="Simple SARIMAX baseline with optional exogenous features",
  inputs={"df":"pd.DataFrame","date_col":"str","target":"str","exog_cols":"List[str]|None","order":"tuple|None","seasonal_order":"tuple|None"},
  outputs={"metrics_json":"str","pred_csv":"str"},
  tags=["forecasting","timeseries","sarimax","baseline"]
)
def sarimax_baseline(df: pd.DataFrame, date_col: str, target: str,
                     exog_cols: list[str]|None = None,
                     order: tuple|None = (1,1,1),
                     seasonal_order: tuple|None = (0,0,0,0)):
    df = df.dropna(subset=[date_col, target]).copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    y = df[target].astype(float).values
    X = df[exog_cols] if exog_cols else None

    tscv = TimeSeriesSplit(n_splits=3)
    maes = []
    for train, test in tscv.split(y):
        exog_tr = X.iloc[train] if X is not None else None
        exog_te = X.iloc[test] if X is not None else None
        model = SARIMAX(y[train], exog=exog_tr, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
        res = model.fit(disp=False)
        preds = res.predict(start=test[0], end=test[-1], exog=exog_te)
        maes.append(mean_absolute_error(y[test], preds))

    model = SARIMAX(y, exog=X, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
    res = model.fit(disp=False)
    pred = res.get_prediction()
    out_csv = "sarimax_pred.csv"
    pd.DataFrame({"date": df[date_col].values, "y": y, "yhat": pred.predicted_mean}).to_csv(out_csv, index=False)

    metrics = {"cv_mae_mean": float(np.mean(maes)), "cv_mae_std": float(np.std(maes))}
    import json, pathlib; mpath = "sarimax_metrics.json"
    pathlib.Path(mpath).write_text(json.dumps(metrics, indent=2))
    return {"metrics_json": mpath, "pred_csv": out_csv}
