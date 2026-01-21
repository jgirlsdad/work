import requests
import pandas as pd
from io import StringIO

url = "https://stg-arcgisazurecdataprod1.az.arcgis.com/exportfiles-7647-210058/ODC_CRIME_TRAFFICACCIDENTS5YR_P_5008541234304418365.csv?sv=2025-05-05&st=2025-11-04T20%3A59%3A01Z&se=2025-11-04T22%3A04%3A01Z&sr=c&sp=r&sig=imykFwlr8w2vxxcGKd3UKBfQT5eh9ySnPIcnck7xZfM%3D"
response = requests.get(url)

# Check if request was successful
if response.status_code == 200:
    # Save to file
 #   print(response.content)
    # Or read directly into pandas DataFrame
    # 
    df = pd.read_csv(StringIO(response.text))
    print(df.head())
else:
    print(f"Failed to download: {response.status_code}")