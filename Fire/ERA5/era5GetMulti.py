import cdsapi
import multiprocessing
import os
import psutil
import time

# -----------------------------
# CONFIGURATION
# -----------------------------
dataset = "reanalysis-era5-land"

# variables = [
#     "2m_temperature",
#     "total_precipitation",
#     # add more ERA5 variables as needed
# ]
#variables=["2m_temperature","2m_dewpoint_temperature","10m_u_component_of_wind","10m_v_component_of_wind","total_precipitation"]
variables=["10m_u_component_of_wind","10m_v_component_of_wind","total_precipitation"]

start_year = 1987
end_year = 1989 # inclusive
years = [str(y) for y in range(start_year, end_year + 1)]

months = [f"{m:02d}" for m in range(1, 13)]
days = [f"{d:02d}" for d in range(1, 32)]
times = ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]

output_dir = "era5_downloads"
os.makedirs(output_dir, exist_ok=True)

# -----------------------------
# WORKER FUNCTION
# -----------------------------
def download_year(task_id, year):
    """Download all variables & months for one year (single CDS request)."""
    p = psutil.Process(os.getpid())
    p.cpu_affinity([task_id % psutil.cpu_count(logical=True)])

    client = cdsapi.Client()
    filename = os.path.join(output_dir, f"era5_{year}.grib")

    # Skip if already downloaded
    if os.path.exists(filename):
        print(f"⏩ Year {year} already downloaded.")
        return year

    request = {
        "variable": variables,       # list of variables
        "year": [year],              # single year per worker
        "month": months,             # all months
        "day": days,                 # all days
        "time": times,               # all hours
        "data_format": "grib",
        "download_format": "unarchived",
        "area": [41.1, -109, 37, -102],  # [North, West, South, East]
    }

    print(f"[Worker {task_id}] ⬇️ Downloading ERA5 {year} on cores {p.cpu_affinity()}")

    try:
        client.retrieve(dataset, request).download(filename)
        print(f"[Worker {task_id}] ✅ Finished {year}")
    except Exception as e:
        print(f"[Worker {task_id}] ❌ Error downloading {year}: {e}")
        # Retry once if temporary network error
        time.sleep(10)
        try:
            client.retrieve(dataset, request).download(filename)
            print(f"[Worker {task_id}] ✅ Retried and finished {year}")
        except Exception as e2:
            print(f"[Worker {task_id}] ⚠️ Second attempt failed: {e2}")

    return year


# -----------------------------
# PARALLEL DRIVER
# -----------------------------
def main():
    num_workers = min(12, len(years))  # up to 12 concurrent downloads
    print(f"Starting {num_workers} parallel downloads for {len(years)} years...")

    with multiprocessing.Pool(processes=num_workers) as pool:
        results = [pool.apply_async(download_year, (i, year)) for i, year in enumerate(years)]
        for r in results:
            r.wait()

    print("🎉 All downloads complete.")


if __name__ == "__main__":
    main()
