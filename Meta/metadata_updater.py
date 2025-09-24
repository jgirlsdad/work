from pathlib import Path  # Python 3.6+ only
from dotenv import load_dotenv
env_path = Path('.') / '../../../.env'
load_dotenv(dotenv_path=env_path)
import pandas as pd
import json
import requests
import argparse
import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

bic_etl_home = os.getenv('bic_etl_home')
sys.path.insert(0, os.path.join(bic_etl_home, 'general', 'scripts'))
import custom_log
logger = custom_log.setup("Metadata Updater")

#args
parser = argparse.ArgumentParser(prog="Metadata Updater",
                                description="Updates metadata from the "
                                "Inventory Google Sheet to data.colorado.gov "
                                "for all or specific datasets using a dataset's"
                                " unique 4x4.",
                                usage="%(prog)s [options]",
                                epilog="Uses Google Drive API to pull from the "
                                "Inventory, Socrata Metadata API to pass values"
                                ", and Selenium for browser automation to fix "
                                "Socrata API issues.")
parser.add_argument("-a", "--all", help="Update metadata for entire Inventory",
action="store_true")
parser.add_argument("-l", "--linux", help="Optional flag if accessing the "
"script from a Linux machine", action="store_true")
parser.add_argument("-p", "--partial", help="Update metadata for the entered "
"4x4s. e.g. abcd-1234 efgh-5678 ijkl-9123. Separate by space only, no commas.",
nargs="+")
args, leftovers = parser.parse_known_args()
if args.all is False and args.partial is None:
    logger.debug ("Please enter an argument. Use --help for more information")
    exit()
if args.all:
    logger.info("Updating metadata for entire Inventory")
if args.partial:
    logger.info("Updating metadata for specified 4x4s")

# #set up creds and connect to metadata spreadsheet via google api.
# SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# SERVICE_ACCOUNT_FILE = os.path.join(bic_etl_home, 'general', 'metadata_updater', 'scripts', "creds.json")
# creds = None
# creds = service_account.Credentials.from_service_account_file(
#         SERVICE_ACCOUNT_FILE, scopes=SCOPES)
# sheet_id = '137W1gqkXdgTJ0mDn7Tkj2Q5DMHDPru3A_1E0pTpm9nE'
# sheet_range = 'Sheet1!A1:AO450'
# service = build('sheets', 'v4', credentials=creds)

# # Call the Sheets API
# sheet = service.spreadsheets()
# result = sheet.values().get(spreadsheetId=sheet_id, range=sheet_range).execute()
# values = result.get('values', [])
# metadata_df = pd.DataFrame(values) #create df from the list
# new_header = metadata_df.iloc[0]
# metadata_df = metadata_df[1:]
# metadata_df.columns = new_header

#  Columns we expect to find in the dataset tracker as of 02/15/2024.. 
expectedColumns=['Dataset Title', 'Short Description', 'Category', 'Keywords', 'Type',
       'License Type', 'Data Provider', 'Data Provided by', 'Source Link',
       'State Steward', 'Citation', 'Agency Program Page',
       'Agency Data Series Page', 'Business Contact and Phone',
       'Technical Contact and Phone', 'Data Source', 'Unit of Analysis',
       'Granularity Coverage', 'Geographic Extent and Division',
       'Collection Mode', 'Collection Methodology',
       'Data Collection Instrument', 'Date of Initial Dataset Creation',
       'Field Names, comma delimited', 'Oldest Record in Dataset',
       'Newest Record in Dataset', 'Long Description', 'Data Dictionary',
       'Additional Metadata', 'Technical Documentation',
       'Data Quality Certification',
       'Applicable Information Quality Guideline Designation',
       'Stewardship Plan', 'Collection Method', 'Horizontal Accuracy',
       'Horizontal Coordinate System', 'Update Schedule', 'Update Method',
       'Source Update Schedule', 'Update Type',
       'Total Records at Initial Publish', 'Row Class RDF',
       'Subject Column RDF', 'Single Row', 'Row Count (11/20/17)',
       'Total Fields at Initial Publish',
       'FIle Size at Initial Publish or as of 3-1-2016',
       'Expected approximate increase in record count at update',
       'Date Published to CIM', 'GoCode FY Published to CIM', 'Socrata Link',
       'API 4x4', 'Web Display Coordinate System',
       'Coordinate System Disclaimer', 'Related Datasets',
       'Quarter of Gov FY Published',
       'cimAllData Updates', 'Complexity']

#  Get Metadata from Dataset tracker on google drive
scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
             "https://www.googleapis.com/auth/drive.file",
                  "https://www.googleapis.com/auth/drive"]

#creds = ServiceAccountCredentials.from_json_keyfile_name('../../scripts/client_secret.json',
#    scope)
creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join(bic_etl_home, 'general', 'scripts','client_secret.json'),scope)

client = gspread.authorize(creds)
tracker = client.open('BIC Dataset Tracker').worksheet(
'PublishedData')
metadata_df = pd.DataFrame(tracker.get_all_records(head=3))


if args.partial:
    uid_list = args.partial
    uid_list.sort()
else:
    uid_list = metadata_df["Socrata Link"]
    uid_list = uid_list.tolist()
    # uid_list.remove("id")

with open(os.path.join(bic_etl_home, 'general', 'datasync', 'config.json')) as f:
    config = json.load(f)

socrata_password = config["password"]

#set up Socrata credentials and json to pass
base_url = 'https://data.colorado.gov/api/views/metadata/v1/'
username = "oit_datacoloradogov@state.co.us"
password = socrata_password
headers = {'Content-Type': 'application/json'}

while len(uid_list) > 0:
    uid = uid_list.pop()
    logger.debug("uid is - " + str(uid))
    single_row = metadata_df.loc[metadata_df["Socrata Link"] == uid] # all row of data based on the 4x4 id
    single_row = single_row.fillna('')
    tag_list = str(single_row["Keywords"].item())
    tags = tag_list.split(", ")
   
    data = {"name": single_row["Dataset Title"].item(),
                "category": single_row["Category"].item(),
                "attribution": single_row["State Steward"].item(),
                "license": str(single_row["License Type"].item()),
                "attributionLink": single_row["Agency Program Page"].item(),
                "description": single_row["Short Description"].item(),
                "tags": tags,
                "customFields": {
                    "Data Updates": {
                        "Update Schedule": single_row["Update Schedule"].item(),
                        "Update Method": single_row["Update Method"].item(),
                        "Update Type": single_row["Update Type"].item(),
                        "Source Update Schedule": single_row["Source Update Schedule"].item(),
                        "Total Records At Initial Publish": single_row["Total Records at Initial Publish"].item()
                    },
                    "Dataset Coverage": {
                        "Unit of Analysis": single_row["Unit of Analysis"].item(),
                        "Granularity": single_row["Granularity Coverage"].item(),
                        "Geographic Coverage": single_row["Geographic Extent and Division"].item()
                        },
                    "Geospatial": {
                        "Collection Method": single_row["Collection Method"].item(),
                        "Horizontal Accuracy": single_row["Horizontal Accuracy"].item(),
                        "Horizontal Coordinate System": single_row["Horizontal Coordinate System"].item(),
                        "Web Display Coordinate System": single_row["Web Display Coordinate System"].item(),
                        "Coordinate System Disclaimer": single_row["Coordinate System Disclaimer"].item()
                    },  
                    "Additional Dataset Documentation": {
                        "Data Dictionary": single_row["Data Dictionary"].item(),
                        "Additional Metadata": single_row["Additional Metadata"].item(),
                        "Technical Documentation": single_row["Technical Documentation"].item()
                    },
                    "Data Description": {
                        "Single Row": single_row["Single Row"].item(),
                        "Long Description": single_row["Long Description"].item(),
                        "Collection Mode": single_row["Collection Mode"].item(),
                        "Collection Method": single_row["Collection Methodology"].item(),
                        "Data Collection Instrument": single_row["Data Collection Instrument"].item(),
                        "Date of Initial Dataset Creation": single_row["Date of Initial Dataset Creation"].item(),
                        "Field Names, comma delimited": single_row["Field Names, comma delimited"].item(),
                        "Oldest Record in Dataset": single_row["Oldest Record in Dataset"].item(),
                        "Newest Record in Dataset": single_row["Newest Record in Dataset"].item()
                    },
                    "Data Quality": {
                        "Expected Update Frequency": single_row["Update Type"].item()
                    },
                    "Contributing Agency Information": {
                        "Citation": single_row["Citation"].item(),
                        "Agency Program Page": single_row["Agency Program Page"].item(),
                        "Agency Data Series Page": single_row["Agency Data Series Page"].item(),
                        "Data Source": single_row["Data Source"].item()
                    },
                }}
   
    url = base_url + uid
    logger.debug("url is - " + url)
    response = requests.patch('{}/{}'.format(url, ''),
                    auth=(username, password),
                    headers=headers,
                    data=json.dumps(data))
    if "'error': True" in str(response.json()):
        logger.error("***ERROR IN UPDATING " + uid + " ***")
        logger.debug(str(response.json()))
    else:
        # logger.debug("successfully updated " + uid)
        continue

logger.info("Metadata updated successfully")
a = set(expectedColumns)- set(metadata_df.columns)
b = set(metadata_df.columns)-set(expectedColumns)

if len(a) > 0:
    logger.warn(f"In Metadata Updater, an expected column(s) is MISSING from the Dataset Tracker:  {a}")

if len(b) > 0:
    logger.warn(f"In Metadata Updater, a NEW  column(s) found in Dataset Tracker:  {b}")

if args.partial:
    print(data)
