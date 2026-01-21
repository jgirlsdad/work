"""
This module contains functions to interact with the Colorado Information Marketplace (CIM) and Google Sheets.
  ### df = getActivityLog((bic_etl_home: str) -> 'pd.DataFrame')

  ### df = getDatasetTrackerInfo(bic_etl_home: str) -> 'pd.DataFrame'
  #####     Requires the following packages:
           pip install pandas gspread oauth2client google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 
  
  
  ### df = getAssetDataset(bic_etl_home: str)

  ### Needed improts and paths
  import os.path
  bic_etl_home = os.getenv('bic_etl_home')
  sys.path.insert(0, '/home/joe/work/myLibs')
  from funcs import *
"""
import json,requests, pandas as pd, os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def getActivityLog(bic_etl_home: str) -> 'pd.DataFrame':
    """
    Reads the CIM activity log from Socrata API starting Jan 01, 2023 and returns a DataFrame.

    Returns:
        pd.DataFrame: Activity log data.
    """
    flog=open(f"{bic_etl_home}/general/datasync/config.json")
    info = json.load(flog)
    username=info['username']
    password=info['password']
    api=info['appToken']
#    "$where": "created_at > '2023-01-01T00:00:00' and acting_user_name = 'Colorado Information Marketplace'"
    
    # URL of the login form
    query = {
    "$where": "created_at > '2023-01-01T00:00:00' and acting_user_name = 'Colorado Information Marketplace'"
    }
    login_url = 'https://data.colorado.gov/api/activity_log.json?$limit=6000000'
    response=requests.get(login_url,auth=(username, password),params=query)
    if response.status_code == 200:
      
#        activity_log=json.loads(response.text)
        print(type(response.text))
    else:
        print("Failed to download Activity Log")
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")
    return pd.DataFrame(json.loads(response.text))


def getCimInfo(df: 'pd.DataFrame') -> dict:
    """
    Processes a DataFrame to map update types and calculate update history.

    Args:
        df (pd.DataFrame): Input DataFrame with dataset info.

    Returns:
        dict: Mapping of dataset titles to update history.
    """
    notFound=[]
    mapped = {
    "Manual - annual":365,       
    "Automated - monthly":31,    
    "Automated - daily":1,      
    "Automated - weekly":7,      
    "Manual - quarterly":90,                          
    "Manual - monthly":31}        
    
    tody = datetime.today()
    hist={}
    for indx,row in df.iterrows():
        title=row["Dataset Title"]
        expctdUpdt = row["Update Type"]
      #  print("Expet:",expctdUpdt)
        nexpctdUpdt=mapped[expctdUpdt]
        if title  in cimDatasets:    
            cimUpdtMeta = cimDatasets[title]["resource"]["updatedAt"]
            cimUpdtData = cimDatasets[title]["resource"]["data_updated_at"]
            
            cimUpdtMeta=convDateTime(cimUpdtMeta, "%Y-%m-%dT%H:%M:%S.%fZ",1)
            cimUpdtData=convDateTime(cimUpdtData, "%Y-%m-%dT%H:%M:%S.%fZ",1)
      
            diffMeta = tody-cimUpdtMeta
            diffData = tody-cimUpdtData
            typ=cimDatasets[title]['resource']['type']
            diffMeta=round(diffMeta.total_seconds()/(24 * 60 * 60))
            diffData=round(diffData.total_seconds()/(24 * 60 * 60))
            if title not in hist:
                hist[title]={}
            hist[title]["Meta"]=diffMeta
            hist[title]["Data"]=diffData
            hist[title]["Expected"]=nexpctdUpdt
            hist[title]["Type"]=typ
            
    
        else:
            notFound.append(title)
    return hist


def getDatasetTrackerInfo(bic_etl_home: str) -> 'pd.DataFrame':
    """
    Retrieves the BIC Dataset Tracker as a DataFrame from Google Sheets.

    Args:
        bic_etl_home (str): Path to ETL home directory.

    Returns:
        pd.DataFrame: Tracker data.
    """

    scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
                 "https://www.googleapis.com/auth/drive.file",
                      "https://www.googleapis.com/auth/drive"]
    
    #creds = ServiceAccountCredentials.from_json_keyfile_name('../../scripts/client_secret.json',
    #    scope)
    creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join(bic_etl_home, 'general', 'scripts','client_secret.json'),scope)
    
    client = gspread.authorize(creds)
    tracker = client.open('BIC Dataset Tracker').worksheet(
    'PublishedData')
    dfTracker = pd.DataFrame(tracker.get_all_records(head=2))
    return dfTracker

def getAssetDataset(bic_etl_home: str) -> 'pd.DataFrame':
    """
    Reads asset dataset from Socrata API and returns a DataFrame.

    Args:
        bic_etl_home (str): Path to ETL home directory.

    Returns:
        pd.DataFrame: Asset dataset.
    """
    flog=open(f"{bic_etl_home}/general/datasync/config.json")
    info = json.load(flog)
    username=info['username']
    password=info['password']
    api=info['appToken']
    
    # URL of the login form
    query = {
    "$where": "timestamp > '2013-01-01T00:00:00' "
    }
    login_url = 'https://data.colorado.gov/resource/pb79-5bvp.json?$limit=4000000'
    response=requests.get(login_url,auth=(username, password))
    if response.status_code == 200:
        pass
 #        activity_log=json.loads(response.text)
     #   print(type(response.text))
    else:
        print("Failed to download Activity Log")
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")
    return pd.DataFrame(json.loads(response.text))


def top_vars(scope, n=10):
    """
    Show the largest objects in a scope (globals/locals) with names.

    Args:
        scope (dict): The scope to analyze (e.g., globals(), locals()).
        n (int, optional): Number of top objects to display. Defaults to 10.

    Returns:
        None: Prints the top n largest objects in the scope.
    """
   
    sizes = []
    for name, obj in scope.items():
        try:
            sizes.append((sys.getsizeof(obj), name, type(obj)))
        except Exception:
            pass
    for size, name, typ in sorted(sizes, reverse=True)[:n]:
        print(f"{name:<20} | {typ} | {size/1024:.2f} KB")
