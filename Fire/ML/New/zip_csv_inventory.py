#!/usr/bin/env python3
"""Build an inventory of date ranges and location metadata from zipped CSV files.

Example:
    python zip_csv_inventory.py \
      --input-dir /path/to/zips \
      --output-csv /path/to/inventory.csv
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


DATE_HINTS = (
    "date",
    "datetime",
    "time",
    "timestamp",
    "yrmo",
    "year",
    "month",
    "day",
)

LOCATION_HINTS = (
    "lat",
    "latitude",
    "lon",
    "long",
    "lng",
    "longitude",
    "location",
    "site",
    "station",
    "county",
    "city",
    "state",
    "region",
    "point",
    "point_id",
    "zip",
)


@dataclass
class CsvInventoryRow:
    zip_file: str
    csv_member: str
    rows_read: int
    date_columns_used: str
    date_start: str | None
    date_end: str | None
    location_columns_used: str
    location_summary: str


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower())


def infer_date_columns(columns: list[str]) -> list[str]:
    matched = []
    for col in columns:
        n = normalize_name(col)
        if any(h in n for h in DATE_HINTS):
            matched.append(col)
    return matched


def infer_location_columns(columns: list[str]) -> list[str]:
    matched = []
    for col in columns:
        n = normalize_name(col)
        if any(h in n for h in LOCATION_HINTS):
            matched.append(col)
    return matched


def try_parse_series_as_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    s = series.astype(str).str.strip()
    parsed = pd.to_datetime(s, errors="coerce", utc=False)

    if parsed.notna().mean() >= 0.7:
        return parsed

    # Try common compact integer-like date encodings such as YYYYMMDD.
    if s.str.fullmatch(r"\d{8}").mean() >= 0.7:
        parsed_ymd = pd.to_datetime(s, format="%Y%m%d", errors="coerce")
        return parsed_ymd

    if s.str.fullmatch(r"\d{6}").mean() >= 0.7:
        parsed_ym = pd.to_datetime(s, format="%Y%m", errors="coerce")
        return parsed_ym

    return parsed


def datetime_range_from_frame(df: pd.DataFrame, date_cols: list[str]) -> tuple[pd.Timestamp | None, pd.Timestamp | None, list[str]]:
    best_start: pd.Timestamp | None = None
    best_end: pd.Timestamp | None = None
    used_cols: list[str] = []

    for col in date_cols:
        parsed = try_parse_series_as_datetime(df[col])
        parsed = parsed.dropna()
        if parsed.empty:
            continue

        used_cols.append(col)
        col_start = parsed.min()
        col_end = parsed.max()

        if best_start is None or col_start < best_start:
            best_start = col_start
        if best_end is None or col_end > best_end:
            best_end = col_end

    return best_start, best_end, used_cols


def summarize_locations(df: pd.DataFrame, location_cols: list[str]) -> str:
    if not location_cols:
        return "{}"

    summary: dict[str, Any] = {}
    lower_map = {normalize_name(c): c for c in location_cols}

    lat_col = None
    lon_col = None
    for key, col in lower_map.items():
        if lat_col is None and ("lat" in key or "latitude" in key):
            lat_col = col
        if lon_col is None and ("lon" in key or "long" in key or "lng" in key or "longitude" in key):
            lon_col = col

    if lat_col and lon_col:
        lat_vals = pd.to_numeric(df[lat_col], errors="coerce").dropna()
        lon_vals = pd.to_numeric(df[lon_col], errors="coerce").dropna()
        if not lat_vals.empty and not lon_vals.empty:
            summary["lat_min"] = float(lat_vals.min())
            summary["lat_max"] = float(lat_vals.max())
            summary["lon_min"] = float(lon_vals.min())
            summary["lon_max"] = float(lon_vals.max())

    for col in location_cols:
        if col in (lat_col, lon_col):
            continue

        vals = df[col].dropna().astype(str).str.strip()
        vals = vals[vals != ""]
        if vals.empty:
            continue
        top_values = vals.value_counts().head(5).index.tolist()
        summary[f"top_{col}"] = top_values

    return json.dumps(summary, ensure_ascii=True)


def read_csv_from_zip_member(zf: zipfile.ZipFile, member: str, sample_rows: int) -> pd.DataFrame:
    with zf.open(member) as fh:
        return pd.read_csv(fh, low_memory=False, nrows=sample_rows)


def inventory_zip_csvs(input_dir: Path, sample_rows: int) -> list[CsvInventoryRow]:
    zip_paths = sorted(input_dir.rglob("*.zip"))
    rows: list[CsvInventoryRow] = []

    for zip_path in zip_paths:
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                csv_members = [m for m in zf.namelist() if m.lower().endswith(".csv")]

                for member in csv_members:
                    try:
                        df = read_csv_from_zip_member(zf, member, sample_rows=sample_rows)
                    except Exception as ex:
                        rows.append(
                            CsvInventoryRow(
                                zip_file=str(zip_path),
                                csv_member=member,
                                rows_read=0,
                                date_columns_used="",
                                date_start=None,
                                date_end=None,
                                location_columns_used="",
                                location_summary=json.dumps({"error": f"read_failed: {type(ex).__name__}"}),
                            )
                        )
                        continue

                    cols = df.columns.tolist()
                    date_cols = infer_date_columns(cols)
                    location_cols = infer_location_columns(cols)

                    # If no obvious date columns were found by name, probe all columns.
                    if not date_cols:
                        date_cols = cols

                    start, end, used_date_cols = datetime_range_from_frame(df, date_cols)
                    loc_summary = summarize_locations(df, location_cols)

                    rows.append(
                        CsvInventoryRow(
                            zip_file=str(zip_path),
                            csv_member=member,
                            rows_read=len(df),
                            date_columns_used=",".join(used_date_cols),
                            date_start=start.isoformat() if start is not None else None,
                            date_end=end.isoformat() if end is not None else None,
                            location_columns_used=",".join(location_cols),
                            location_summary=loc_summary,
                        )
                    )
        except zipfile.BadZipFile:
            rows.append(
                CsvInventoryRow(
                    zip_file=str(zip_path),
                    csv_member="",
                    rows_read=0,
                    date_columns_used="",
                    date_start=None,
                    date_end=None,
                    location_columns_used="",
                    location_summary=json.dumps({"error": "bad_zip_file"}),
                )
            )

    return rows


def to_dataframe(rows: list[CsvInventoryRow]) -> pd.DataFrame:
    return pd.DataFrame([r.__dict__ for r in rows])


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory zipped CSV files for date range and location coverage")
    parser.add_argument("--input-dir", required=True, help="Directory containing .zip files (recursive)")
    parser.add_argument("--output-csv", required=True, help="Output inventory CSV path")
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=200000,
        help="Rows to read from each CSV member for profiling (default: 200000)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_csv = Path(args.output_csv).expanduser().resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist or is not a directory: {input_dir}")

    rows = inventory_zip_csvs(input_dir=input_dir, sample_rows=args.sample_rows)
    df_out = to_dataframe(rows)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_csv, index=False)

    print(f"Scanned zip files under: {input_dir}")
    print(f"Rows in inventory: {len(df_out)}")
    print(f"Wrote: {output_csv}")


if __name__ == "__main__":
    main()
