import cdsapi
import sys,datetime,os
#variables=["10m_u_component_of_wind","10m_v_component_of_wind","surface_pressure"]

#variables=["2m_temperature","2m_dewpoint_temperature"]
#variables=["2m_temperature"]
#variables=["2m_dewpoint_temperature"]
##variables=["total_precipitation"]
#variables=["10m_u_component_of_wind"]

variables=["10m_v_component_of_wind"]

dataset = "reanalysis-era5-land"
request = {
    "variable": variables,
    "year": ["2026"],
    "month":  ["01" , "02", "03",
                     "04", "05", "06",
                     "07", "08", "09",
                     "10", "11", "12"],
    "day": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12",
        "13", "14", "15",
        "16", "17", "18",
        "19", "20", "21",
        "22", "23", "24",
        "25", "26", "27",
        "28", "29", "30",
        "31"
    ],
    "time": [
        "00:00", "03:00", "06:00",
        "09:00", "12:00", "15:00",
        "18:00", "21:00"
    ],
    "data_format": "grib",
    "download_format": "unarchived",
    "area": [41.1, -109, 37, -102]
}

client = cdsapi.Client()
client.retrieve(dataset, request).download()