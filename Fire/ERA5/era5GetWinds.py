import cdsapi
import sys,datetime,os
#variables=["10m_u_component_of_wind","10m_v_component_of_wind","surface_pressure"]


x = 41
np=0
points={}
while x >=  37:
    y = -109
    while y <= -102:
        np+=1

        points[np] = (x, y)
        y+=.25

    x-=.25

process_id = os.getpid()

#variables=["2m_temperature","2m_dewpoint_temperature","10m_u_component_of_wind","10m_v_component_of_wind","total_precipitation"]
variables=["100m_u_component_of_wind"]

for pt,locs in points.items():
    print("Getting :",pt,locs)
    dataset = "reanalysis-era5-single-levels-timeseries"
    lat=locs[0]
    lon=locs[1]
    request = {
        "variable": [
            "100m_u_component_of_wind",
            "100m_v_component_of_wind"
        ],
        "location": {"longitude": lon, "latitude": lat},
        "date": ["1940-01-01/2026-03-07"],
        "data_format": "csv"
    }

    client = cdsapi.Client()
    client.retrieve(dataset, request).download()
