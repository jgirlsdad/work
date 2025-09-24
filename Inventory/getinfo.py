#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sodapy import Socrata
import pandas as pd
import json,csv
import os,inspect,sys
from chlorophyll import CodeView
from tkinter import Tk
import tkinter as tk
# from tkinter import ttk,Button,Label
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


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', None)
cim_url_query = 'data.colorado.gov'
datasets = None
today = datetime.today()
#today=f"{tody.year}-{tody.month:02d}-{tody.day:02d}"    
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
# import seaborn as sns,matplotlib.pyplot as plt
# import matplotlib.dates as mdates

bic_etl_home = os.getenv('bic_etl_home')

import requests
from requests.auth import HTTPBasicAuth


cimDatasets = {}
bicHome = "/home/joe/bic_etl"
allDatasets=[]

import argparse

parser = argparse.ArgumentParser(description="A sample script.")
#parser.add_argument("-g","--name", type=str, help="Your name")
parser.add_argument("-g","--group", action="store_true", help="List available groups")

args = parser.parse_args()




with Socrata(cim_url_query, None) as client:
    datasets = client.datasets()
    for dataset in datasets:
        allDatasets.append(dataset)
        if dataset['owner']['display_name'] == 'Colorado Information Marketplace':
            title=dataset["resource"]["name"]
            cimDatasets[title]=dataset


# %%
def find_files_recursive(directory):
    # This function finds all files recursively in a given directory
    return glob.glob(f'{directory}/**/run_etl.json', recursive=True)

def getGroups(directory_path='/home/joe/bic_etl'): 
## Get all run_etl.json files
    files = find_files_recursive(directory_path)
    skip_groups = ["catalog","general/example"]
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
             
                if group not in skip_groups:
                    if group not in groups:
                        groups[group]=[]
                    groups[group].append(title)
    return groups


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
groups=getGroups()


from rich.table import Table
from rich.console import Console

console = Console()
table = Table(title="Sample Table")
table.add_column("Index", style="cyan", no_wrap=True)
table.add_column("Name", style="magenta")


from prompt_toolkit.shortcuts import radiolist_dialog,checkboxlist_dialog
from prompt_toolkit.styles import Style
from rich.box import DOUBLE
# Define custom styles
custom_style = Style.from_dict({
    "dialog": "bg:#282c34 fg:#ffffff",  # Background and foreground for the dialog
    "dialog.body": "bg:#1c1f26 fg:#61afef",  # Body styling
    "dialog.shadow": "bg:#000000",  # Shadow styling
    "radio.selected": "fg:#98c379",  # Selected option
    "radio": "fg:#abb2bf",  # Unselected option
})
values = [(option, option) for i, option in enumerate(groups)]
result = checkboxlist_dialog(
    title="Menu",
    text="Choose an option:",
    values=values,
    style=custom_style,
).run()


for res in result:
    count=0
   

 
    table = Table(title=res,box=DOUBLE,row_styles=["green", "magenta"])
    table.add_column("Index", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Data Delta Days", style="green")
    table.add_column("Data Updated", style="green")

    table.add_column("Meta Delta Days", style="green")
    table.add_column("Meta Updated", style="blue")

    for title in groups[res]:
        if title not in cimDatasets:
            print(f"NOT FOUND {title} ")
            continue
        count+=1
        metaUp=cimDatasets[title]['resource']['metadata_updated_at']
        dataUp=cimDatasets[title]['resource']['data_updated_at']
        metaUp=convDateTime(metaUp,"%Y-%m-%dT%H:%M:%S.%fZ",1)
        dataUp=convDateTime(dataUp,"%Y-%m-%dT%H:%M:%S.%fZ",1)
        metaDays = int((today-metaUp).days)
        dataDays = int((today-dataUp).days)
        table.add_row(str(count),title,str(dataDays),str(dataUp),str(metaDays),str(metaUp))
       
        
       
    console.print(table)

# %%
