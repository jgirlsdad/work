import arcgis,requests,pandas as pd

from arcgis.gis import GIS

# Public / anonymous server
#gis = GIS("https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis", anonymous=True)
url="https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_PARK_DOGPARKS_A/FeatureServer/0/query"

from arcgis.features import FeatureLayer

# Full URL to the layer endpoint (you can add /0 if it has a single layer)

# layer = FeatureLayer(url)

# # Query all records (limit 2000 by default)
# data = layer.query( out_fields="*", return_geometry=False)

# # Convert to a pandas DataFrame
# df = data.sdf
# print(df.head())

# params = {
#     "where": "1=1",
#     "outFields": "*",
#     "f": "json"
# }

# r = requests.get(url, params=params)
# r.raise_for_status()
# data = r.json()
# print(data)
# # Convert to DataFrame
# # df = pd.json_normalize(data)
# # print(df.head())


#import requests
#import pandas as pd
import geopandas as gpd
geojson_url = "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_PARK_DOGPARKS_A/FeatureServer/84/query?outFields=*&where=1%3D1&f=geojson"

# r = requests.get(geojson_url)
# r.raise_for_status()
# data = r.json()

# Convert to a DataFrame
# features = [f["properties"] for f in data["features"]]
# df = pd.DataFrame(features)
# print(df.head())
# print(f"\n✅ {len(df)} features downloaded")

# # Save as CSV
# df.to_csv("dog_parks.csv", index=False)

df = pd.read_json(geojson_url)
print(df.head())