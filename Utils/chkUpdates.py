
import pandas as pd
import sys
import os.path
bic_etl_home = os.getenv('bic_etl_home')

import base64

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from sib_api_v3_sdk import SendSmtpEmail, SendSmtpEmailAttachment, TransactionalEmailsApi
import base64

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = os.getenv('brevo_api_key')
api_client = sib_api_v3_sdk.ApiClient(configuration)
email_api = TransactionalEmailsApi(api_client)

from sodapy import Socrata

import json,csv
import inspect
#from chlorophyll import CodeView
import datetime
from datetime  import datetime

#dt = datetime.datetime.utcfromtimestamp(a['rowsUpdatedAt'])
from zoneinfo import ZoneInfo
#import PySimpleGUI as sg
from difflib import SequenceMatcher
import pygments.lexers
import pytz
import glob
from croniter import croniter
from cron_descriptor import get_description, ExpressionDescriptor

today = datetime.today()
sys.path.insert(0, os.path.join(bic_etl_home, 'general', 'scripts'))
import custom_log
cim_url_query = 'data.colorado.gov'
datasets = None
tody = datetime.today()
#today=f"{tody.year}-{tody.month:02d}-{tody.day:02d}"    
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import requests
from requests.auth import HTTPBasicAuth


import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from sib_api_v3_sdk import SendSmtpEmail, TransactionalEmailsApi

logger2 = custom_log.setupNew(args.title)
logger2.info(f"Starting: CIM-Tracker Update Analysis")

cimDatasets = {}

allDatasets=[]


with Socrata(cim_url_query, None) as client:
    datasets = client.datasets()
    for dataset in datasets:
        allDatasets.append(dataset)
        if dataset['owner']['display_name'] == 'Business Intelligence Center of CO':
            title=dataset["resource"]["name"]
            cimDatasets[title]=dataset



# %% [markdown]
# ## Functions 1

# %%
def find_files_recursive(directory):
    # This function finds all files recursively in a given directory
    return glob.glob(f'{directory}/**/run_etl.json', recursive=True)

def decodeExtract(extract):
    
    prog=""
    lang=""
    if 'language' in extract:
        lang=extract['language']
            
    if 'file' in extract:
        prog=extract['file']
    
    opts={}
    if 'options' in extract:
        lang=extract['language']
        for opt in extract['options']:
            opt=opt.strip()
            indx=opt.find(" ")
            o=opt[:indx]
            opts[o]= opt[indx+1:]

    return lang,prog,opts


def processRun_etls(directory_path='/home/joe/bic_etl'): 
## Get all run_etl.json files
    files = find_files_recursive(directory_path)
    
    datasets={}
    noEx=0
    groups={}
    for file in files:
        ll=len(file)
        group=file[18:-13]
        fin=open(file)
        infos = json.load(fin)
        fin.close()
        title=""
        extract=""
        for info in infos: 
            if 'title' in info:
                title=info['title']
                datasets[title]={}
                datasets[title]['extract']={}
                datasets[title]['extract']['language']=''
                datasets[title]['extract']['program']=''
                datasets[title]['extract']['options']={}
                datasets[title]['group']=group
                if group not in groups:
                    groups[group]=[]
                groups[group].append(title)
                if 'extract' in info:
                    extract=info['extract']
                    if isinstance(extract,dict):
                       lang,prog,opts=decodeExtract(extract)
                       datasets[title]['extract']['language']=lang
                       datasets[title]['extract']['program']=prog
                       datasets[title]['extract']['options']=opts
                    elif isinstance(extract,list):
                        for infoL in extract: 
                            lang,prog,opts=decodeExtract(infoL)
                            datasets[title]['extract']['language']=lang
                            datasets[title]['extract']['program']=prog
                            datasets[title]['extract']['options']=opts
        
    return datasets,groups

def getUrlAddresses(datasets):
    hist={}
    addresses={}
    options={}
    specOpts={}
    specOpts["general/scripts/request_url.js"]={}
    specOpts["general/scripts/request_url.js"]["-u"]="-f"
    
    specOpts["general/scripts/sftp_extract.js"]={}
    specOpts["general/scripts/sftp_extract.js"]["-h"]="-f"
    specOpts["general/scripts/sftp_extract.js"]["none"]="-f"
    
    specOpts["cdos/general/scripts/sftp_extract.js"]={}
    specOpts["cdos/general/scripts/sftp_extract.js"]["none"]="-f"
    
    lookupNotFound = {
    'bea/scripts/bea_msa_api_reader.py':['https://apps.bea.gov/api/data'],
    'denver/scripts/get_data.py':['https://www.denvergov.org/content/dam/denvergov/Portals/covid19/documents/Denver-Approved-Patio-Expansion-List.xlsx'],
    'scripts/extract_liquor_files.py':'https://sbg.colorado.gov/liquor-license-lists',
    'county_sales_extract.py':['https://docs.google.com/spreadsheets/d/1br_cwfHy24d2R2bcXacb2KarOIBKGrbR/export?format=csv'],
    'scripts/county_salestax_extract.py':['https://docs.google.com/spreadsheets/d/1EhlDIrXjJdmg_ob2eMFeN5xtyvTq2jtr/export?format=csv'],
    'scripts/tax_fee_extract.py':['https://docs.google.com/spreadsheets/d/1e8hnG64Vkg9ffgkNpKQ1kzPsXNbGjG2X/export?format=csv'],
    'scripts/state_mar_sales_extract.py':['https://docs.google.com/spreadsheets/d/1wE7Z_1q2zxL7-kP0AqlUvL731U3Aui1l/export?format=csv'],
    'scripts/city_extract.py':['https://docs.google.com/spreadsheets/d/1wo4WKzvlfdw47_3841jD2RUibbDwos3L/export?format=csv','https://docs.google.com/spreadsheets/d/1WI2jvRCzBqYFIPA2vsUmCjHedKCQD911/export?format=csv'],
    'scripts/county_extract.py':['https://docs.google.com/spreadsheets/d/1irLP8K7jREdDgIiamgZ2MiTbkeMX5lrM/export?format=csv'],
    'scripts/extract_scripts/citybyindustry_extract.py':['https://docs.google.com/spreadsheets/d/1ZKc0olDlChHyRiLlxL3ECxKqBYtyaUaB/export?format=csv','https://docs.google.com/spreadsheets/d/1E6VqKiPnUD3LMnrSBy1aEYSc4QsU6Y9v/export?format=csv'],
    'scripts/extract_scripts/industry_extract.py':['https://docs.google.com/spreadsheets/d/{1WANzZQFE57J73daXvo1xu4mITy-1DmuP/export?format=csv','https://docs.google.com/spreadsheets/d/1cmTJ4ZRAjBFfevT0hyCatUXDIzIG393I/export?format=csv'],
    'scripts/extract_scripts/countybyindustry_extract.py':['https://docs.google.com/spreadsheets/d/1CI66-qv0ooK93asc21VyV-tJiYSc2J3c/export?format=csv','https://docs.google.com/spreadsheets/d/1kybUGf02krqwyl8yBPHnTbn0iQT4Cnnz/export?format=csv'],
    'scripts/extract_liquor_files.py':['https://sbg.colorado.gov/liquor-license-lists']
    }
    
    
    noProg={}
    for title,dct in datasets.items():
        if 'group' in dct:
            group=dct['group']
        else:
            group=""
        if 'extract' in dct:
            if 'language' in dct['extract']:
                lang=dct['extract']['language']
                prog=dct['extract']['program']
                if lang not in hist:
                    hist[lang]={}
                if prog not in hist[lang]:
                    hist[lang][prog]=0
                hist[lang][prog]+=1
    
                if prog not in addresses:
                    addresses[prog]={}
                if 'options' in dct['extract']:
                    if prog in specOpts:
                        o=list(specOpts[prog].keys())[0]
                        fOpt=specOpts[prog][o]
                        ff = dct['extract']['options'][fOpt]  
                        if o in dct['extract']['options']:
                            a=dct['extract']['options'][o]
                        else:
                            if prog == "general/scripts/sftp_extract.js":
                              a="ftps.sos.state.co.us"
                            else:
                              a=""
                    else:
                        ff=""
                        o=""
                        a=""
                        if prog in lookupNotFound:
                            a = lookupNotFound[prog]
                        else:
                            if prog not in noProg:
                                noProg[prog]={}
                            noProg[prog]['group']=group
                        
                    if isinstance(a,str):
                        b=[]
                        b.append(a)
                    else:
                        b=a
                    for a in b: 
                        if a not in addresses[prog]:
                            addresses[prog][a]={}
                        if ff not in addresses[prog][a]:
                           addresses[prog][a][ff]={}
                        
                        if title not in addresses[prog][a][ff]:
                           addresses[prog][a][ff][title]={}
                            
                           addresses[prog][a][ff][title]['count']=0
                           addresses[prog][a][ff][title]['group']=group
                        
                        
                    addresses[prog][a][ff][title]['count']+=1
##  Create a DataFrame
    programs=[]
    address=[]
    files=[]
    counts=[]
    titles=[]
    groups=[]
    for p,dct in addresses.items():
        for o,dct2 in dct.items():   
            for f,dct3 in dct2.items():
                for t,dct4 in dct3.items():
                    
                    programs.append(p)
                    address.append(o)
                    files.append(f)
                    counts.append(dct4['count'])
                    groups.append(dct4['group'])
                    
                    titles.append(t)
    df = pd.DataFrame({
        "Title":titles,
        "Group":groups,
        "Program":programs,
        "Address":address,
        "File":files,
        "Count":counts})
    return addresses,df

## Collect CRON Info from cron File

def getCronInfo(cron_file_path):
    fin=open(cron_file_path)
    lines=fin.readlines()
    crons={}
    for line in lines:
        if line[0:1] != "#" and line[0:1] != " " and len(line) > 2:
            line=line.strip()
            spl=line.split()
            crn=' '.join(spl[:5])
            rest = ' '.join(spl[5:])
            
            crons[rest]=crn
    return crons

def decodeCron(cron_file):
    hist={}
    cronGroups={}
    crons=getCronInfo(cron_file)
    for inf,crn in crons.items():
    
        desc = get_description(crn)
        spl=inf.split()
        lang=spl[0]
        prg=spl[1]
        indxP=inf.find("-p")
        if indxP > -1:
           tmp=inf[indxP+2:].lstrip()
           end=tmp.find(" ")
           grp=tmp[:end]
        else:
            grp=""
    
        indxT=inf.find("-t")
        if indxT > -1:
           tmp=inf[indxT+2:].lstrip()
           start = tmp.find('"')
           end=tmp[start+1:].find('"')
           titl=tmp[start+1:end+1]
        else:
            titl="ALL"
        if grp not in cronGroups:
            cronGroups[grp]={}
        cronGroups[grp][titl]=desc     
        if lang not in hist:
            hist[lang]={}
        if prg not in hist[lang]:
            hist[lang][prg]=0
        hist[lang][prg]+=1
    return cronGroups

## Combine Dataset ETL Info and CRON Info 
def addCronInfo(row):
    title=row['Title']
    group=row['Group']

    if group in cronGroups:
        dct=cronGroups[group]
        if title in dct:
            cron=cronGroups[group][title]["desc"]
            days=cronGroups[group][title]["days"]

        elif "ALL" in dct:
            cron=cronGroups[group]["ALL"]["desc"]
            days=cronGroups[group]["ALL"]["days"]
        else:
            cron="Unknown"   
            days=-99

    else:
        cron="No Group Found"
        days=-99
    row['Cron'] = cron
    row['Ndays'] = days
    return row

def decodeCron2(cron_file):
    hist={}
    cronGroups={}
    crons=getCronInfo(cron_file)
    for inf,crn in crons.items():
        desc = get_description(crn)
        spl=inf.split()
        lang=spl[0]
        prg=spl[1]
        indxP=inf.find("-p")
        if indxP > -1:
           tmp=inf[indxP+2:].lstrip()
           end=tmp.find(" ")
           grp=tmp[:end]
        else:
            grp=""
    
        indxT=inf.find("-t")
        if indxT > -1:
           tmp=inf[indxT+2:].lstrip()
           start = tmp.find('"')
           end=tmp[start+1:].find('"')
           titl=tmp[start+1:end+1]
        else:
            titl="ALL"
        if grp not in cronGroups:
            cronGroups[grp]={}
        cronGroups[grp][titl]={}
        cronGroups[grp][titl]['desc']=desc
        cronGroups[grp][titl]['days']=cron_to_days_direct(crn)
           
        if lang not in hist:
            hist[lang]={}
        if prg not in hist[lang]:
            hist[lang][prg]=0
        hist[lang][prg]+=1
    return cronGroups

def cron_to_days_direct(cron_expression):
    """
    Calculate days between cron runs using croniter.
    
    Args:
        cron_expression (str): Standard cron format (5 fields)
        
    Returns:
        int: Days between updates
    """
    try:
        base = datetime.now()
        cron = croniter(cron_expression, base)
        
        # Get next two occurrences
        next_run = cron.get_next(datetime)
        following_run = cron.get_next(datetime)
        
        # Calculate difference in days
        diff = (following_run - next_run).days
        return round(diff)
        
    except Exception as e:
        logger2.error(f"Error parsing cron '{cron_expression}': {e} ")

        return None

def getActivityLog():
    flog=open(f"{bic_etl_home}/general/datasync/config.json")
    info = json.load(flog)
    username=info['username']
    password=info['password']
    api=info['appToken']
#    "$where": "created_at > '2023-01-01T00:00:00' and acting_user_name = 'Colorado Information Marketplace' order by 'created_at' desc"
    
    # URL of the login form
    query = {
    "$where": "created_at > '2023-01-01T00:00:00' and (acting_user_name = 'Colorado Information Marketplace' or acting_user_name = 'Business Intelligence Center of CO')"
    }
    login_url = 'https://data.colorado.gov/api/activity_log.json?$limit=6000000'
    response=requests.get(login_url,auth=(username, password),params=query)
    if response.status_code == 200:
         continue
#        activity_log=json.loads(response.text)
    else:
        logger2.error("Failed to download Activity Log")
        logger2.error(f"Error: {response.status_code}")
        logger2.error(f"Message: {response.text}")
        sys.exit(1)
    return pd.DataFrame(json.loads(response.text))


def getCimInfo(df):
    notFound=[]
    mapped = {
    "Manual - annual":365,   
    "Manual - biannual":180,       

    "Automated - monthly":31,    
    "Automated - daily":1,      
    "Automated - weekly":7,      
    "Manual - quarterly":90,                          
    "Manual - monthly":31}        
    
    tody = datetime.today()
    hist={}
    for indx,row in df.iterrows():
        title=row["Dataset Title"]
        w4x4=row['Socrata Link']
      
        expctdUpdt = row["Update Type"]
   
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
            hist[title]['4x4']=w4x4
            
    
        else:
            notFound.append(title)
    return hist

def convDateTime(string,format,type):
   if type == 1: # Convert Date Time string to Date Time Object
        dateTime=datetime.strptime(string,format)
        # Convert Zulu Time to Mountain Time
        if format.find("Z") > -1:
            utc_timezone = pytz.utc
            zulu_time = utc_timezone.localize(dateTime)
            
            # Define the local timezone (e.g., US/Eastern)
            local_timezone = pytz.timezone("US/Mountain")
            
            # Convert the Zulu time (UTC) to local time
            dateTime = zulu_time.astimezone(local_timezone)
            # Convert the offset-aware datetime to offset-naive by removing the timezone info
            dateTime=dateTime.replace(tzinfo=None)
        return dateTime
       



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

    
def analysis(hist,dfActivity):
    data=[]
    which="Data"
    logInfo={}
    counts=[]

    fails=["DataUpdate.Import.Failure",
           "DataUpdate.Replace.Failure",
           "DataUpdate.Import.Failure",
           "ScheduleFailed",
           "DataUpdate.Replace.SuccessWithDataErrors",
           "DataUpdate.Upsert.Failure"]
    failsSched=["ScheduleFailedFatally"]
    successSched=["ScheduleSucceeded"]
    success=["DataUpdate.Replace.Success",
              "DataUpdate.Upsert.Success",
              "DataUpdate.Import.Success",
              "DataUpdate.Append.Success"]

    tody=datetime.today()
    summary={}
    allAuto={}
    lastActivityDate=None
    for title,dct in sorted(hist.items(), key=lambda item: item[1][which]):
        lastActivityDate=None
        w4x4=dct['4x4']
        if dct[which] > dct["Expected"]:
         #   data.append([title,dct["Data"]-dct["Expected"],dct["Data"],dct["Expected"],dct["Meta"]])
            tmp=dfActivity.loc[dfActivity["affected_item"] == title]
            summary[title]={}
            allAuto[title]={}
            
            if tmp.shape[0] > 0:
                for indx,row in tmp.iterrows(): 
                    activity = row["activity_type"]
                    cdate=row["created_at"]
                    cdate = convDateTime(cdate, "%Y-%m-%dT%H:%M:%S.%fZ",1)
                    ndays=round((tody-cdate).total_seconds()/(24 * 60 * 60))
                    cdate=cdate.date()
                    if not lastActivityDate:
                        lastActivityDate=cdate
                    else:
                        if cdate > lastActivityDate:
                            lastActivityDate=cdate
                    if title not in logInfo:
                        logInfo[title]={}
                    if activity not in logInfo[title]:
                       logInfo[title][activity]={}
                    # if cdate not in logInfo[title][activity] = {}
                    #     logInfo[title][activity][cdate]={}
                    logInfo[title][activity][cdate]=ndays
                       
                dataFailsMax=None
                dataSuccessMax=None
                dataSuccessSchedMax=None
                dataFailsSchedMax=None
            
                for act,dct2 in logInfo[title].items():
                    mx=max(dct2.keys())
                    mn=min(dct2.keys())
            
                    if act in fails:
                        if not dataFailsMax:
                            dataFailsMax=mx
                        else:
                            if mx > dataFailsMax:
                                dataFailsMax=mx
                    elif act in success:
                        if not dataSuccessMax:
                            dataSuccessMax=mx
                        else:
                            if mx > dataSuccessMax:
                                dataSuccessMax=mx
                    elif act in failsSched:
                        if not dataFailsSchedMax:
                            dataFailsSchedMax=mx
                        else:
                            if mx > dataFailsSchedMax:
                                dataFailsSchedMax=mx
                    elif act in successSched:
                        if not dataSuccessSchedMax:
                            dataFailsSuccessMax=mx
                        else:
                            if mx > dataSuccessSchedMax:
                                dataSuccessSchedMax=mx  
                                
                tody=datetime.today()
                if dataFailsMax:
                    dataFailsNdays=round((tody.date() - dataFailsMax).total_seconds() / (24 * 3600))
                else:
                    dataFailsNdays="NA"
        
                if dataSuccessMax:
                    dataSuccessNdays=round((tody.date() - dataSuccessMax).total_seconds() / (24 * 3600))
                else:
                    dataSuccessNdays="NA"
        
                if dataFailsSchedMax:
                    dataFailsSchedNdays=round((tody.date() - dataFailsSchedMax).total_seconds() / (24 * 3600))
                else:
                    dataFailsSchedNdays="NA"
        
                if dataSuccessSchedMax:
                    dataSuccessSchedNdays=round((tody.date() - dataSuccessSchedMax).total_seconds() / (24 * 3600))
                    
                else:
                    dataSuccessSchedNdays="NA"

                what=""
                expt=dct["Expected"]
                if dataSuccessNdays == "NA":
                    what="Fail"
                else:
                    lastSuccessn=int(dataSuccessNdays)
                    exptn=int(expt)
                    if exptn >= lastSuccessn:
                       what="Pass"
                    else:
                       what="Fail"

                summary[title]["Data-Expected"]= dct["Data"]-dct["Expected"]
                summary[title]["Data Update"]= dct["Data"]
                summary[title]["Expected Update"]= dct["Expected"]
                summary[title]["Meta Update"]= dct["Meta"]
                summary[title]["Activity Data Success"]= dataSuccessNdays
                summary[title]["Activity Data Fail"]= dataFailsNdays
                summary[title]["Activity Scheduled Success"]= dataSuccessSchedNdays
                summary[title]["Activity Scheduled Fail"]= dataFailsSchedNdays     

                allAuto[title]["Data-Expected"]= dct["Data"]-dct["Expected"]
                allAuto[title]["Data Update"]= dct["Data"]
                allAuto[title]["Expected Update"]= dct["Expected"]
                allAuto[title]["Meta Update"]= dct["Meta"]
                allAuto[title]["Activity Data Success"]= dataSuccessNdays
                allAuto[title]["Activity Data Fail"]= dataFailsNdays
                allAuto[title]["Activity Scheduled Success"]= dataSuccessSchedNdays
                allAuto[title]["Activity Scheduled Fail"]= dataFailsSchedNdays     
                allAuto[title]["Status"]= 'fail'
                allAuto[title]["Type"]= dct["Type"]
               
                if dataFailsMax:
                    dataFailsMax=dataFailsMax.strftime("%Y-%m-%d")
                if dataSuccessMax:
                    dataSuccessMax=dataSuccessMax.strftime("%Y-%m-%d")
                if dataSuccessSchedMax:
                    dataSuccessSchedMax=dataSuccessSchedMax.strftime("%Y-%m-%d")
                if dataFailsSchedMax:
                    dataFailsSchedMax=dataFailsSchedMax.strftime("%Y-%m-%d")
                allAuto[title]["dataFailsMax"]= dataFailsMax
                allAuto[title]["dataSuccessMax"]= dataSuccessMax
                allAuto[title]["dataSuccessSchedMax"]= dataSuccessSchedMax
                allAuto[title]["dataFailsSchedMax"]= dataFailsSchedMax
                allAuto[title]["4x4"]= dct["4x4"]
                allAuto[title]["Link"]= f"https://data.colorado.gov/d/{dct['4x4']}"
                data.append([title,dct["Data"]-dct["Expected"],dct["Data"],dct["Expected"],dct["Meta"],what,dataSuccessNdays,dataFailsNdays,dataSuccessSchedNdays,dataFailsSchedNdays])
                
        else:
                allAuto[title]={}
                allAuto[title]["Status"]= 'pass'
                allAuto[title]['Expected Update'] = dct["Expected"]
                allAuto[title]["Type"]= dct["Type"]
             
    return logInfo,data,summary,lastActivityDate,allAuto

    
def getAssetDataset():
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
    if response.status_code !=  200:
        logger2.error("Failed to download Activity Log")
        logger2.error(f"Error: {response.status_code}")
        logger2.error(f"Message: {response.text}")
    return pd.DataFrame(json.loads(response.text))





def generateMonthlyReport(allAuto):
    mapped = {1:"Daily",7:"Weekly",31:"Monthly",90:"Quarterly",180:"Bi-Annual",365:"Annual"}
    hist={}
    histNew={}
    badTitles={}
    for title,dct in allAuto.items():
        if "Status" not in dct:
            continue
        stat = dct["Status"]
        expected = dct["Expected Update"]
        
        mapd=mapped[expected]
        if mapd not in hist:
            hist[mapd]={}
        if stat not in hist[mapd]:
            hist[mapd][stat]=0
        hist[mapd][stat]+=1
        if stat == "fail":
            if dct['Activity Data Success'] != 'NA'  and int(dct['Activity Data Success']) <= dct['Expected Update']:
                stat='pass'
        if stat == "fail":
            if mapd not in badTitles:
                badTitles[mapd]={}
            badTitles[mapd][title]=dct
            
        if mapd not in histNew:
            histNew[mapd]={}
        if stat not in histNew[mapd]:
            histNew[mapd][stat]=0
        histNew[mapd][stat]+=1

    tdy = datetime.today().date()

    all=None
    
    for cron,dct in badTitles.items():
        for title,dct2 in dct.items():
     
          
            tmp=dfAssets.loc[(dfAssets["name"] == title) & (dfAssets["uid"].str.len() == 9),['uid', 'name', 'owner','creation_date','audience','publication_stage', 'last_data_updated_date']]
            tmp2 = grCronGroup.loc[grCronGroup["Title"] == title]
        
            if tmp2.shape[0] > 0:
                tmp["Group"]=tmp2["Group"].values
                tmp["Cron"]=tmp2["Cron"].values
                grp = tmp2["Group"].values.tolist()[0]
                
            else:
                tmp["Group"]=""
                tmp["Cron"]=""
                grp=""
                
            if "Data Update" in dct2 and "Expected Update" in dct2:
                tmp["Data Update CIM"]=dct2["Data Update"]
                tmp["Expected Update"]=dct2["Expected Update"]
                tmp["Diff Update"]=dct2["Data Update"]-dct2["Expected Update"]           
            else:
                tmp["Data Update CIM"]=""
                tmp["Expected Update"]=""
    
                
            if title.lower().find("denver") > -1: 
                why="Denver"
            
            elif grp == "dola/special_districts" or grp == "cdot/transportation_infrastructure" or  grp == "dola/boundaries" or  \
                 grp == "cdot/transportation_road_attributes" or grp == "cdot/natural_resources":
                 why="Map Issue"
            else:
                why="Unknown"
            tmp["Sched"]=cron
            tmp["Status"]=why
            if all is not None:
                all=pd.concat([all,tmp])
            else:
                all=tmp     
    return badTitles,hist


# %% [markdown]
# ## Main

# %%
directory_path="/home/joe/bic_etl"    
datasetsEtlInfo,automationGroups = processRun_etls(directory_path=directory_path)
    
addresses,df = getUrlAddresses(datasetsEtlInfo) 
cron_file = f'{bic_etl_home}/general/cron/cron_file' 
cronGroups=decodeCron2(cron_file)
df = df.apply(addCronInfo,axis=1)
grCronGroup = df.copy()

dfAssets=getAssetDataset()
dfAssets = dfAssets.loc[dfAssets['audience'] == "public"]

dfActivity =getActivityLog()
dfTracker=getDatasetTrackerInfo(bic_etl_home)
dfTrackerNotStatic = dfTracker.loc[~dfTracker["Update Type"].isin(["Static",""])]
hist=getCimInfo(dfTrackerNotStatic)
logInfo,data,summary,lastActivityDate,allAuto=analysis(hist,dfActivity)
bt,h = generateMonthlyReport(allAuto)

# Collect data for DataFrame
frequencies = []
titles = []
keys = []
values = []
values_dict={}
for frq, dst in bt.items():
    for title, dct in dst.items():
        values_dict.setdefault('frequencies', []).append(frq)
        values_dict.setdefault('titles', []).append(title)
        for key, value in dct.items():
            values_dict.setdefault(key, []).append(value)

# Create DataFrame
df_results = pd.DataFrame(values_dict)
# Check Real-Time Metadata 


def chkUptoDate(row):
    ''' One last check.  The metadata originally checked is from 
    the assets dataset, which is only updated once a day.  For 
    datasets that have failed, this checks the real-time metadata from Socrata
    to see if they have been updated more recently than the asset metadata.'''
    title=row['titles']
    w4x4=row['4x4']
    url=f'https://data.colorado.gov/api/views/{w4x4}'
    response = requests.get(url)
   
# Check if request was successful
    
    if response.status_code == 200:
        a=json.loads(response.content)
        unix_time = a['rowsUpdatedAt']  # e.g., 1731437265
        mst = ZoneInfo("America/Denver")  # Mountain Time zone (handles DST automatically)
        dt_local = datetime.fromtimestamp(unix_time, tz=mst)
        diff = datetime.now(mst) - dt_local
        if diff.days > row['Expected Update']:
            row['checkDate'] = datetime.now(mst).strftime("%Y-%m-%d")
            return row
    else:
        logger2.error(f"Failed to retrieve data for {title}. Status code: {response.status_code}")
        return row
        

df_results = df_results.apply(chkUptoDate, axis=1)
df_results_old = pd.read_csv(f"{bic_etl_home}/general/data_compare/monthly_report.csv")

new_rows = df_results[~df_results['titles'].isin(df_results_old['titles'])]

missing_rows = df_results_old[~df_results_old['titles'].isin(df_results['titles'])]

df_results.to_csv(f"{bic_etl_home}/general/data_compare/monthlyReport.csv", index=False)

mapped = {
    "Manual - annual":365,   
    "Manual - biannual":180,       

    "Automated - monthly":31,    
    "Automated - daily":1,      
    "Automated - weekly":7,      
    "Manual - quarterly":90,                          
    "Manual - monthly":31}    
dfTrackerNotStatic["Update Days"]= dfTrackerNotStatic["Update Type"].map(mapped)
cronChk = pd.merge(dfTrackerNotStatic,df,left_on="Dataset Title",right_on="Title",how="left")
cronChk['Cron Diff'] = abs(cronChk['Update Days']-cronChk['Ndays'])
cronBad=cronChk.loc[(cronChk['Ndays'] != -99) & (cronChk['Cron Diff'] > 2)  ,['Dataset Title','Update Type','Update Days','Cron','Ndays','Cron Diff']]
#cronBad.to_csv(f"{bic_etl_home}/general/data_compare/cronTrackerMismatch.csv", index=False)
cronBadHtml=cronBad.to_html(index=False)


def send_email(df_results, new_rows, missing_rows):
    html_table = df_results.to_html(index=False)
    if  new_rows.shape[0] > 0:
        new_rows_html = new_rows.to_html(index=False)
    else:
        new_rows_html = "<p>No New Rows</p>"    
    if missing_rows.shape[0] > 0:
        missing_rows_html = missing_rows.to_html(index=False)
    else:
        missing_rows_html = "<p>No Missing Rows</p>"  

    csv_content1 = df_results.to_csv(index=False)
    csv_base641 = base64.b64encode(csv_content1.encode('utf-8')).decode('utf-8')
    
    attachment1 = SendSmtpEmailAttachment(
        content=csv_base641,
        name=f"monthlyReport.csv"
    )

    csv_content2 = cronBad.to_csv(index=False)
    csv_base642 = base64.b64encode(csv_content2.encode('utf-8')).decode('utf-8')

    attachment2 = SendSmtpEmailAttachment(
        content=csv_base642,
        name=f"cronTrackerMismatch.csv"
    )

    html=f"""
    <html>
    <head>
    <style>
      table {{ border-collapse: collapse; width: 100%; }}
      th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
      th {{ background-color: #4CAF50; color: white; }}
      tr:nth-child(even) {{ background-color: #f2f2f2; }}
    </style>
    </head>
    <body>
      <h1>Summary of Dataset Update Status</h1>
      <h2>Monthly Report - {datetime.now().strftime('%Y-%m-%d')}</h2>
      <hr>
      <p><h4>Tracker-Cron Schedule Mismatchs - {cronBad.shape[0]} datasets</h4> - See full table below or attachment
      </p>
      <hr>
      <p><h4>New Datsets on CIM Out of Sync with Dataset Tracker: {new_rows.shape[0]}</h4></p>
      {new_rows_html}
      
    <p><br></p>
    <p><br></p>
      <h3>Full Monthly Report</h3>
      ALL datasets whose Update Schedule is out of Sync on CIM
      Total Datasets on List: {df_results.shape[0]} <br>
      {html_table}
      <p><br></p>
      <h3>Cron Dataset Tracker Mismatches</h3>
      Total Datasets with Cron Mismatches: {cronBad.shape[0]} <br>
      {cronBadHtml}

    <hr>
    <h3>Analysis Method</h3>
    <p>This goal of this program is to check if our automated datasets are out of sync with their expected update schedule from the Dataset Tracker (i.e. updates are failing).  This requires info to be gathered from the cron file, dataset tracker, cim metadata and cim activity log.  The process is to get the update schedule from the Tracker and compare it to the last dataset update date on CIM.  However, when we update a dataset on CIM that has not change at the source, the dataset update date does not change.  To account for these cases, we also check the CIM Activity Log  to determine the last date we successfully updated the dataset.  If this was in the expected amount time as defined by the tracker, than all is good.  If this date also exceeds the limit, then the dataset fails and is included in this log.</p>
    <p>A second check is performed where the actual update cycle set by the Cron file is checked against the Dataset Tracker for datasets that are out of sync between the 2.  This is the Cron-Tracker-Mismatch check. 
    
    <p><br></p>
    <h3> Column Descriptions for the CIM Monthly Report</h3>
    
    <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
        <thead>
            <tr>
                <th style="padding: 8px; text-align: left; border: 1px solid #ddd; background-color: #4CAF50; color: white; font-weight: bold;">
                    Field Name
                </th>
                <th style="padding: 8px; text-align: left; border: 1px solid #ddd; background-color: #4CAF50; color: white; font-weight: bold;">
                    Description
                </th>
            </tr>
        </thead>
        <tbody>
    
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    frequencies
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Update frequency, taken from Dataset Tracker
                </td>
            </tr>
        
            <tr style="background-color: #ffffff;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    titles
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Dataset Title
                </td>
            </tr>
        
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Data-Expected
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    # of Days Update is overdue
                </td>
            </tr>
        
            <tr style="background-color: #ffffff;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Data Update
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    # of Days since last update
                </td>
            </tr>
        
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Expected Update
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    # of Expected days between updates
                </td>
            </tr>
        
            <tr style="background-color: #ffffff;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Meta Update
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    When was metadata last updated
                </td>
            </tr>
        
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Activity Data Success
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    # of days since data was last updated, from the Activity Log
                </td>
            </tr>
        
            <tr style="background-color: #ffffff;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Activity Data Fail
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    # of days since data last failed to update
                </td>
            </tr>
        
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Activity Scheduled Success
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    # of days since Socrata Scheduled Update succeeded
                </td>
            </tr>
        
            <tr style="background-color: #ffffff;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Activity Scheduled Fail
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    # of days since last Socrata Schedule Update failed
                </td>
            </tr>
        
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Status
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Status from the Activity Log
                </td>
            </tr>
        
            <tr style="background-color: #ffffff;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Type
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Type of asset (i.e. dataset, map, story,...)
                </td>
            </tr>
        
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    dataFailsMax
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Date of last failed dataset update
                </td>
            </tr>
        
            <tr style="background-color: #ffffff;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    dataSuccessMax
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Date of last successful dataset update
                </td>
            </tr>
        
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    dataSuccessSchedMax
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Date of last successful Socrata Scheduled update
                </td>
            </tr>
        
            <tr style="background-color: #ffffff;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    dataFailsSchedMax
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Date of last failed Socrata Scheduled update
                </td>
            </tr>
        
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    4x4
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Datasets 4x4
                </td>
            </tr>
        
            <tr style="background-color: #ffffff;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    Link
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    CIM Link for dataset
                </td>
            </tr>
        
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">
                    checkDate
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">
                    Date this check was run
                </td>
            </tr>
        
        </tbody>
    </table>
    
    </body>
    </html>
    """

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.getenv('brevo_api_key')
    api_client = sib_api_v3_sdk.ApiClient(configuration)
    email_api = TransactionalEmailsApi(api_client)

    email = SendSmtpEmail(
        to=[{"email": "bic-help@xentity.com"}],
        sender={"email": "bic-help@xentity.com"},
        subject=f"Weekly CIM-Tracker Update Report - {datetime.now().strftime('%Y-%m-%d')}",
        html_content=html,
        attachment=[attachment1, attachment2]
    )

    try:
        result = email_api.send_transac_email(email)
    except ApiException as e:
        logger2.error(f"Report NOT SENT: Error: {e}")

send_email(df_results, new_rows, missing_rows)


