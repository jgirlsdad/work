#!/usr/bin/env python
# coding: utf-8

# # Create Monthly Report Plots

# ## Libraries

# In[2]:


from sodapy import Socrata
import pandas as pd
import json,csv
import os,inspect,sys
#from chlorophyll import CodeView
from tkinter import Tk
import tkinter as tk
from tkinter import ttk,Button,Label
from datetime  import datetime
#import PySimpleGUI as sg
from difflib import SequenceMatcher
import pygments.lexers
import pytz
import glob
from croniter import croniter
from cron_descriptor import get_description, ExpressionDescriptor
os.environ["BROWSER"] = "google-chrome"
import webbrowser
browsers = webbrowser._tryorder
print("Browsers detected:", browsers)
today = datetime.today()
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', None)
cim_url_query = 'data.colorado.gov'
datasets = None
tody = datetime.today()
#today=f"{tody.year}-{tody.month:02d}-{tody.day:02d}"    
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import seaborn as sns,matplotlib.pyplot as plt
import matplotlib.dates as mdates

bic_etl_home = os.getenv('bic_etl_home')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import MultipleLocator
import requests
from requests.auth import HTTPBasicAuth


cimDatasets = {}
bicHome = "/home/joe/bic_etl"
allDatasets=[]


with Socrata(cim_url_query, None) as client:
    datasets = client.datasets()
    for dataset in datasets:
        allDatasets.append(dataset)
        if dataset['owner']['display_name'] == 'Business Intelligence Center of CO':
            title=dataset["resource"]["name"]
            cimDatasets[title]=dataset

print("DONE")


# In[2]:



# ## Functions

# In[7]:


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

    else:
        print("No Prgram",lang,title,file)
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
                    else:
                        print("UNK",type(info))

            else:
                print("No Title",file)
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
  #      print(grp,titl)     
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
#    print(group,title)
    if group in cronGroups:
        dct=cronGroups[group]
        if title in dct:
            cron=cronGroups[group][title]
        elif "ALL" in dct:
            cron=cronGroups[group]["ALL"]
        else:
            cron="Unknown"   

        # for how,crn in dct.items(): 
        #     print("  ",how,crn)
        #     if title in cronGroups[group]:
        #        cron=cronGroups[group][title]
        #        break
        #     elif how == "ALL":
        #         cron=crn
        #         break
        #     else:
        #         cron="Unknown"
        #         print("    Unknown ",how,title,crn)

    else:
        cron="No Group Found"
    return cron


# ## Activity Functions

# In[8]:


def getActivityLog():
    flog=open(f"{bic_etl_home}/general/datasync/config.json")
    info = json.load(flog)
    username=info['username']
    password=info['password']
    api=info['appToken']
#    "$where": "created_at > '2023-01-01T00:00:00' and acting_user_name = 'Colorado Information Marketplace'"

    # URL of the login form
    query = {
    "$where": "created_at > '2023-01-01T00:00:00' and acting_user_name = 'Business Intelligence Center of CO'"
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



def createReport(summary,lastActivityDate):
    report={}
    for title,dct in summary.items():
        if "Expected Update" in dct: 
            expt = dct["Expected Update"]
            lastSuccess= dct["Activity Data Success"]
            if expt not in report:
                report[expt]={}
                report[expt]["Pass"]=0
                report[expt]["Fail"]=0
                report[expt]["Total"]=0

            report[expt]["Total"]=0

            if lastSuccess == "NA":
                report[expt]["Fail"]+=1
                what="Fail"
            else:
                lastSuccessn=int(lastSuccess)
                exptn=int(expt)
                if exptn >= lastSuccessn:
                   report[expt]["Pass"]+=1
                   what="Pass"
                else:
                   report[expt]["Fail"]+=1
                   what="Fail"
          #  print(f"{expt:4d} {str(lastSuccess):4s}  {what:4s}  {title}")
        else:
            print("ROH ROH ",title,dct)

    tody=datetime.today().date()
    ndf=tody-lastActivityDate

    mapped = {1:"Daily",7:"Weekly",31:"Monthly",90:"Quarterly",365:"Annual"}
    fout=open("/home/joe/reportSummary.txt","w")
    fout.write(f"Date: {datetime.today().date()}\n")
    fout.write(f"Last Date in Activity Log: {lastActivityDate}\n")
    fout.write(f"Age of  Activity Log (Days): {ndf.days}\n")


    sumr=[]
    for how,dct in report.items():
     #  print(f"{mapped[how]:10s}  Passed: {dct['Pass']:4d}  Fail:{dct['Fail']:4d}")
        fout.write(f"{mapped[how]:10s}  Passed: {dct['Pass']:4d}  Fail:{dct['Fail']:4d}\n")
        sumr.append([mapped[how],dct['Pass'],dct['Fail']])

    fout.close()

    layout = [
         [sg.Text(f"Summary Report for {datetime.today()}",font='Courier 25 bold ')],
         [sg.Button('Quit',font='Courier 15 bold ')],
         [sg.Text(f"Last Date in Activity Log {lastActivityDate}",font='Courier 15 bold ')],
         [sg.Text(f"Activity Log Age in Days {ndf.days}",font='Courier 15 bold ')],
         [sg.Text("Report Output to File: /home/joe/reportSummary.txt",font='Courier 15 bold ')],
         [sg.Table(values=sumr,headings=["Cadence","Pass","Fail"],font='Courier 15 bold ')]
         ]



    window2 = sg.Window('Automated Group Info', layout,margins=(25,25),finalize=True,resizable=True,background_color="#cc4400")
    return report



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
    fails=["DataUpdate.Import.Failure","DataUpdate.Replace.Failure","DataUpdate.Import.Failure"]
    success=["DataUpdate.Replace.Success"]
    failsSched=["ScheduleFailedFatally"]
    successSched=["ScheduleSucceeded"]
    tody=datetime.today()
    summary={}
    allAuto={}
    lastActivityDate=None
    print("DF ACT",dfActivity.head(100))
    for title,dct in sorted(hist.items(), key=lambda item: item[1][which]):

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


                data.append([title,dct["Data"]-dct["Expected"],dct["Data"],dct["Expected"],dct["Meta"],what,dataSuccessNdays,dataFailsNdays,dataSuccessSchedNdays,dataFailsSchedNdays])
            else:
                print("NO INFO FOR ",title)
        else:
                allAuto[title]={}
                allAuto[title]["Status"]= 'pass'
                allAuto[title]['Expected Update'] = dct["Expected"]
                allAuto[title]["Type"]= dct["Type"]

    return logInfo,data,summary,lastActivityDate,allAuto


def analyzeActivityLog(title,logInf):
    try:
        histActivity={}
        acts=[]
        durs=[]
        mins=[]
        maxs=[]
        counts=[]
        for act,dct2 in logInf.items():
            mx=max(dct2.keys())
            mn=min(dct2.keys())
            acts.append(act)
            mins.append(mn)
            maxs.append(mx)
       #     dur=(mx-mn).total_seconds() / (24 * 3600)
            dur=(mx-mn)
            counts.append(len(dct2.keys()))
            durs.append(dur)
            if act not in histActivity:
                histActivity[act]=0
            histActivity[act]+=1


        dfa=pd.DataFrame({"Activity":acts,"Duration":durs,"Start":mins,"Ends":maxs,"Counts":counts})
        fig, ax = plt.subplots()
        #df['duration'] = (df['end'] - df['start']).dt.total_seconds() / (24 * 3600)
    #    fig.figure(figsize=(10, 6))
        sns.set(style="whitegrid")

        # Plot rectangles for each task
        for index, row in dfa.iterrows():
            plt.barh(index, row['Duration'], left=row['Start'], height=0.4, edgecolor='black')
            start=row["Start"]
            duration=row["Duration"]
            count=row["Counts"]
            ax.text(start + duration / 2, index, f"{count}", va='center', ha='center', color='white', fontsize=9)

        # Setting labels
        ax.set_yticks(range(len(dfa['Activity'])), dfa['Activity'])
        ax.set_xlabel('Date')
        ax.set_title(f"Activity Log for {title}")

        # Format the x-axis to show dates
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5))

        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    # Set the formatter to display the date in a readable format (Year-Month-Day)
        # Rotate and align the x labels for better readability
        plt.xticks(rotation=90, ha="right")
      #  ax.set_xticklabels(ax.get_xticks(), rotation=90)
        # Show grid lines for better readability
        ax.grid(False, linestyle='--', alpha=0.5)
        ax.set_xlim(left=None, right=tody)
        # Show the plot
        fig.tight_layout()

        layout = [
            [sg.Text('Actvity Log Analysis')],
            [sg.Canvas(key='-CANVAS-')],
            [sg.Button('Quit')]
        ]

        # Create the PySimpleGUI window
        window = sg.Window('Activity Log Analysis', layout, finalize=True)

        # Draw the plot on the canvas
    #    draw_figure(window['-CANVAS-'].TKCanvas, fig)
        figure_canvas_agg = FigureCanvasTkAgg(fig, window['-CANVAS-'].TKCanvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    except Exception as err:
        print("Error in Activity Analysis ",err) 

def activeGui():
#   dfActivity = pd.read_csv("Activity_Log_2025-02-03.csv")
   dfActivity = getActivityLog()
   dfTracker=getDatasetTrackerInfo(bic_etl_home)
   dfTrackerNotStatic = dfTracker.loc[~dfTracker["Update Type"].isin(["Static",""])]
   hist=getCimInfo(dfTrackerNotStatic)
   logInfo,data,summary,lastActivityDate,allAuto=analysis(hist,dfActivity)
   header=["Title","Data-Expected","Data Update","Expected Period","Metadata Update","Smell Test","Last Success","Last Failure",
           "Sched Success","Sched Fail"]
   data=sorted(data, key=lambda item: item[1],reverse=True)

   layoutS = [
         [sg.Button('Quit',font='Courier 15 bold ')],
         [sg.Text(f"Last Date in Activity Log: {lastActivityDate}",font='Courier 15 bold ')],
         [sg.Text(f"Today: {datetime.today().date()}",font='Courier 15 bold ')],
         [sg.Text(f"Age of Activity Log (Days): {(datetime.today().date()-lastActivityDate).days}",font='Courier 15 bold ')],

         [sg.Button("Create Report",key="-REPORT-")],
         [sg.Table(values=data,headings=header,col_widths=[50,15,15,15,15,15,15,15,15,15],cols_justification=["l","c","c","c","c","c","c","c","c","c"],
                   num_rows=30,row_height=40,vertical_scroll_only=False,auto_size_columns=False,
                   enable_events=True, key='-TABLE-',border_width=6,background_color = "#99ccff",
                   alternating_row_color = "#9999ff",font="CENTAUR 10 bold")]
    ]
   layout = [[ sg.Column(layoutS,scrollable=True)]]
   window3 = sg.Window('Activity GUI', layout,finalize=True,resizable=True,background_color="#cc4400")

   sourceDefFile=""  #  this is needed
   vals=[]
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
    if response.status_code != 200:

#        activity_log=json.loads(response.text)
     #   print(type(response.text))
 #   else:
        print("Failed to download Activity Log")
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")
    return pd.DataFrame(json.loads(response.text))


# ## Create Plots

# In[10]:


def generateMonthlyReport(allAuto):
    mapped = {1:"Daily",7:"Weekly",31:"Monthly",90:"Quarterly",365:"Annual",180:"Manual - biannual"}
    hist={}
    histNew={}
    badTitles={}
 #   print(allAuto)
    for title,dct in allAuto.items():
        if "Status" in dct:
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
        else:
            print("NOT FOUDN",title,dct)

## Create Summary Plot
    if 'Annual' in histNew:
        del histNew["Annual"]
    if 'Quarterly' in histNew:
        del histNew['Quarterly']
 #   print (histNew)
    histPlot={}
    for key,dct in histNew.items():
        histPlot[key]={}
        if 'fail' in dct:
            histPlot[key]['Fail']=dct['fail']
        else:
            histPlot[key]['Fail']=0
        histPlot[key]['Pass']=dct['pass']
        if "Total" not in histPlot:
            histPlot["Total"]={}
            histPlot["Total"]["Fail"]=0
            histPlot["Total"]["Pass"]=0
        if 'fail' in dct:   
            histPlot["Total"]["Fail"]+=dct["fail"]
        histPlot["Total"]["Pass"]+=dct["pass"]

    tdy = datetime.today().date()
#    print("HIST PLOT ",histPlot)
    pd.DataFrame(histPlot)[["Daily","Weekly","Monthly"]].T.plot.bar(figsize=(9,7))
    plt.title(f'Automated Datasets Meeting Update Schedule as of {tdy.strftime("%B")}, {tdy.year}')

    # Move the legend to outside of the plot
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.85))
    plt.gca().yaxis.set_major_locator(MultipleLocator(2))
    plt.savefig("automatedStatus.png")


## Plot WHY Failing
    all=None

    for cron,dct in badTitles.items():
        for title,dct2 in dct.items():
     #       print("--------------\n",title)

            tmp=dfAssets.loc[(dfAssets["name"] == title) & (dfAssets["uid"].str.len() == 9),['uid', 'name', 'owner','creation_date','audience','publication_stage', 'last_data_updated_date']]
            tmp2 = grCronGroup.loc[grCronGroup["Title"] == title]
            if tmp2.shape[0] > 1:
                print("MULTI CRON FOUND ",tmp2.head())
            if tmp2.shape[0] > 0:
                try:
                    tmp["Group"]=tmp2["Group"].values
                    tmp["Cron"]=tmp2["Cron"].values
                    grp = tmp2["Group"].values.tolist()[0]
                except Exception as err:
                    print("Error assigning cron for ",title  )
                    print("Error assigning cron info ",err)
                    print("TTT ",tmp2.head())
                    print("TTT2 ",tmp2['Group'].values)
                    print("TTT3 ",tmp.head())
                    grp=""
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

    plt.figure(figsize=(8,10))
    ax=all["Status"].value_counts().plot.bar()
    plt.title(f"Reasons for Dataset Automation Failures as of {tdy.strftime('%B')}, {tdy.year}")
    plt.gca().yaxis.set_major_locator(MultipleLocator(2))
    plt.savefig("reasons.png")


directory_path="/home/joe/bic_etl"    
datasetsEtlInfo,automationGroups = processRun_etls(directory_path=directory_path)

addresses,df = getUrlAddresses(datasetsEtlInfo) 
cron_file = '/home/joe/bic_etl/general/cron/cron_file' 
cronGroups=decodeCron(cron_file)
df["Cron"] = df.apply(addCronInfo,axis=1)
grCronGroup = df.copy()
dfAssets=getAssetDataset()

dfActivity =getActivityLog()
dfTracker=getDatasetTrackerInfo(bic_etl_home)
dfTrackerNotStatic = dfTracker.loc[~dfTracker["Update Type"].isin(["Static",""])]
#print("dftrack",dfTrackerNotStatic)
hist=getCimInfo(dfTrackerNotStatic)
#print(dfActivity)
logInfo,data,summary,lastActivityDate,allAuto=analysis(hist,dfActivity)

#print("HIST",allAuto)

generateMonthlyReport(allAuto)

print("\n\n\nUpload Files to Google Dribve at Project-Colorado-Bic/Project Deliverables-2025/Reports/Montly Reports")
print("https://drive.google.com/drive/u/0/folders/1RXTogGJBKTZubjofnveXgxgOpUD54spr")
print("Image Files are in /home/joe/work/Inventory under montlyReport.png and reasons.png")


