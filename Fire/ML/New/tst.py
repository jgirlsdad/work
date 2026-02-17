import xarray as xr
import numpy as np

# open the GRIB file
ds = xr.open_dataset(
    "Data/data.grib",
    engine="cfgrib"
)

# show what variables are present
print(ds)

# explicitly look at geopotential
z = ds["z"]

print("\nVariable metadata:")
print(z)

# check dimensions
print("\nDimensions:", z.dims)

# check whether it varies in time
if "time" in z.dims:
    diffs = z.isel(time=0) - z.isel(time=-1)
    max_diff = np.abs(diffs).max().item()
    print("\nMax difference between first and last timestep:", max_diff)
else:
    print("\nNo time dimension — variable is static")
