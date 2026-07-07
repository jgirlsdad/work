import xarray as xr
import pandas as pd
import sqlalchemy
import pygrib
import sqlite3

import numpy as np
from pathlib import Path

import numpy as np




import sqlite3
from pathlib import Path
import pandas as pd

sqlite_path_2t = Path(f"/home/joe/work/Fire/ML/Data/DB/era5_daily_2982_2t.sqlite")
sqlite_path_2d = Path(f"/home/joe/work/Fire/ML/Data/DB/era5_daily_2982_2d.sqlite")
table_name = "daily_data"



sqlite_path_out_rh = Path(f"/home/joe/work/Fire/ML/Data/DB/era5_daily_2982_RH.sqlite")
table_name = "daily_data"
latlons = pd.read_csv("latlons_42x71.csv")
sqlite_path_out_vpd = Path(f"/home/joe/work/Fire/ML/Data/DB/era5_daily_2982_VPD.sqlite")
table_name = "daily_data"


with sqlite3.connect(sqlite_path_out_rh) as conn:
    create_sql = """
    CREATE TABLE IF NOT EXISTS daily_data (
        datetime TEXT NOT NULL,
        point_id INTEGER NOT NULL,
        variable TEXT NOT NULL,
        '0' REAL,
        '3' REAL,
        '6' REAL,
        '9' REAL,
        '12' REAL,
        '15' REAL,
        '18' REAL,
        '21' REAL,
        PRIMARY KEY (datetime, point_id)
    );
    """
    conn.execute(create_sql)

with sqlite3.connect(sqlite_path_out_vpd) as conn:
    create_sql = """
        CREATE TABLE IF NOT EXISTS daily_data (
        datetime TEXT NOT NULL,
        point_id INTEGER NOT NULL,
        variable TEXT NOT NULL,
        '0' REAL,
        '3' REAL,
        '6' REAL,
        '9' REAL,
        '12' REAL,
        '15' REAL,
        '18' REAL,
        '21' REAL,
        PRIMARY KEY (datetime, point_id)
    );
    """
    conn.execute(create_sql)


import numpy as np

def rh_from_t_td(t, td, units="C"):
    """Compute relative humidity (%) from air temperature and dew point.

    Parameters
    ----------
    t : float
        Air temperature.
    td : float 
        Dew point temperature (same units as t).
    units : str
        "C" for Celsius (default) or "K" for Kelvin.
    """
    # t = np.asarray(t, dtype=float)
    # td = np.asarray(td, dtype=float)

    if units.upper() == "K":
        t = t - 273.15
        td = td - 273.15
    elif units.upper() != "C":
        raise ValueError("units must be 'C' or 'K'")

    # Magnus formula (valid for typical atmospheric conditions)
    rh = 100.0 * np.exp((17.625 * td) / (243.04 + td)) / np.exp((17.625 * t) / (243.04 + t))
    return round(rh, 1)

# Example
def vpd_from_t_td(t, td, units="C", out_units="kPa"):
    """Compute vapor pressure deficit from air temperature and dew point.

    VPD = es(T) - ea, where ea = es(Td).
    Inputs can be scalars, NumPy arrays, or pandas Series.
    """
    # t = np.asarray(t, dtype=float)
    # td = np.asarray(td, dtype=float)

    if units.upper() == "K":
        t = t - 273.15
        td = td - 273.15
    elif units.upper() != "C":
        raise ValueError("units must be 'C' or 'K'")

    es = 0.6108 * np.exp((17.27 * t) / (t + 237.3))
    ea = 0.6108 * np.exp((17.27 * td) / (td + 237.3))
    vpd_kpa = np.maximum(es - ea, 0.0)

    if out_units.lower() == "kpa":
        return vpd_kpa
    if out_units.lower() == "pa":
        return vpd_kpa * 1000.0
    raise ValueError("out_units must be 'kPa' or 'Pa'")

# Compute VPD columns for each 3-hour slot

from multiprocessing import Pool
import time
max_yrmo = 0

def process_batch(batch_pids):
    """Process a batch of points in parallel."""
    conn2t_local = sqlite3.connect(sqlite_path_2t)
    conn2d_local = sqlite3.connect(sqlite_path_2d)
    
    try:
        pid_list = ','.join(map(str, batch_pids))
        
        # Load batch data
        t_batch = pd.read_sql_query(
            f"SELECT * FROM {table_name} WHERE point_id IN ({pid_list}) AND datetime > {max_yrmo}",
            conn2t_local
        )
        td_batch = pd.read_sql_query(
            f"SELECT * FROM {table_name} WHERE point_id IN ({pid_list}) AND datetime > {max_yrmo}",
            conn2d_local
        )
        
        # Merge and compute
        df_batch = pd.merge(t_batch, td_batch, on='datetime', suffixes=('_t', '_td'))
        cols = ['0', '3', '6', '9', '12', '15', '18', '21']
        
        for col in cols:
            df_batch[f"rh_{col}"] = rh_from_t_td(df_batch[f"{col}_t"], df_batch[f"{col}_td"], units="K")
            df_batch[f"vpd_{col}"] = vpd_from_t_td(df_batch[f"{col}_t"], df_batch[f"{col}_td"], units="K", out_units="kPa")
        
        # Reshape for RH and VPD tables
        df_rh = df_batch[['datetime', 'point_id_t', 'rh_0', 'rh_3', 'rh_6', 'rh_9', 'rh_12', 'rh_15', 'rh_18', 'rh_21']]
        df_rh['variable'] = 'rh'
        df_rh.rename(columns={'point_id_t': 'point_id'}, inplace=True)
        for col in cols:
            df_rh.rename(columns={f"rh_{col}": f"{col}"}, inplace=True)
        
        df_vpd = df_batch[['datetime', 'point_id_t', 'vpd_0', 'vpd_3', 'vpd_6', 'vpd_9', 'vpd_12', 'vpd_15', 'vpd_18', 'vpd_21']]
        df_vpd['variable'] = 'vpd'
        df_vpd.rename(columns={'point_id_t': 'point_id'}, inplace=True)
        for col in cols:
            df_vpd.rename(columns={f"vpd_{col}": f"{col}"}, inplace=True)
        
        return df_rh, df_vpd, len(batch_pids)
    finally:
        conn2t_local.close()
        conn2d_local.close()


# Split points into batches
npoints = len(latlons)
batch_size = 100
batch_list = []
for i in range(0, npoints, batch_size):
    batch_end = min(i + batch_size, npoints)
    batch_pids = latlons.iloc[i:batch_end]['point'].tolist()
    batch_list.append(batch_pids)

print(f"Processing {npoints} points in {len(batch_list)} batches of ~{batch_size} points")
print(f"Starting parallel processing with 8 workers...")

start_time = time.time()
with Pool(8) as pool:
    results = pool.map(process_batch, batch_list)

# Collect results
all_rh = []
all_vpd = []
total_processed = 0
for df_rh, df_vpd, batch_count in results:
    all_rh.append(df_rh)
    all_vpd.append(df_vpd)
    total_processed += batch_count
    print(f"Processed batch: {batch_count} points")

# Concatenate all results
df_all_rh = pd.concat(all_rh, ignore_index=True)
df_all_vpd = pd.concat(all_vpd, ignore_index=True)

print(f"\nTotal rows RH: {len(df_all_rh)}, VPD: {len(df_all_vpd)}")

# Bulk write to SQLite
print("Writing to SQLite...")
with sqlite3.connect(sqlite_path_out_rh) as conn:
    df_all_rh.to_sql(table_name, conn, index=False, if_exists='append')
with sqlite3.connect(sqlite_path_out_vpd) as conn:
    df_all_vpd.to_sql(table_name, conn, index=False, if_exists='append')

elapsed = time.time() - start_time
print(f"\n✓ Completed in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")