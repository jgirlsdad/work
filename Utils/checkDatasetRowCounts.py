import pandas as pd
import sys
import os.path,json
bic_etl_home = os.getenv('bic_etl_home')
sys.path.insert(0, '/home/joe/work/myLibs')

from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from sodapy import Socrata

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from sib_api_v3_sdk import SendSmtpEmail, TransactionalEmailsApi

logger2 = custom_log.setupNew(args.title)
logger2.info(f"Starting: CIM-Tracker Update Analysis")

cimDatasets = {}
allDatasets=[]
cim_url_query = 'data.colorado.gov'


with Socrata(cim_url_query, None) as client:
    datasets = client.datasets()
    for dataset in datasets:
        allDatasets.append(dataset)
        if dataset['owner']['display_name'] == 'Business Intelligence Center of CO':
            title=dataset["resource"]["name"]
            cimDatasets[title]=dataset



def getDatasetTrackerInfo(bic_etl_home):

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


dfTracker=getDatasetTrackerInfo(bic_etl_home)
countCheck={}
nrows=dfTracker.shape[0]
nint=0

## Check Record Counts on CIM
for indx,row in dfTracker.iterrows():
    title=row['Dataset Title']
    w4x4=row['Socrata Link']
    url=f'https://data.colorado.gov/resource/{w4x4}.json?$select=count(*)'
    response = requests.get(url)
    nint+=1
#    print(f"Processing {nint} of {nrows} : {title}" )
# Check if request was successful
    countCheck[title]=-1
    if response.status_code == 200:
        a=json.loads(response.content)
        if len(a) > 0 and 'count' in a[0]:
            countCheck[title]=a[0]['count']
        elif len(a) > 0 and 'count_1' in a[0]:
            countCheck[title]=a[0]['count_1']  
        else:
            print("ROh ROh Scooby... did not get an a",a,title) 
    else: 
       countCheck[title]=None      
       print(w4x4,title)


## Analyze Results
types={}
hist={"Good":0,"Bad":0}
notFound={}
for title,count in countCheck.items():
    title=title.strip()
    if title in cimDatasets:
        tp = cimDatasets[title]['resource']['type']
        types[tp]=types.get(tp,0)+1
    else:
        tp="Unknown"
        types[tp]=types.get(tp,0)+1
        print("Unknown Type for ",title)
        notFound[title]= count
    if count is None or int(count) < 1:
        if tp.lower() == 'dataset':
            print(title,count,tp)
            hist["Bad"]+=1
    else:
        hist["Good"]+=1


## Print Summary
print("Summary of Dataset Checks")
print("Dataset That Have 0 Records on CIM")
print(f" Bad Datasets {hist['Bad']:4d}")
print(f"Good Datasets {hist['Good']:4d}")

print("\n------------------------------------")
print("Tracker Datasets NOT Found in CIM Metadata")
print(f"Total Not Found: {len(notFound)}")
for title, count in notFound.items():
    print(title,count)

print("\n-----------------------------------")
print("Summary of Dataset Types on CIM")
print("   Type      Count")
for tp in types:
    print(f"{tp:10s}   {types[tp]:4d}")
      