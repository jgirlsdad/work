#!/usr/bin/env python
# coding: utf-8

# # ETL Flow GUI

# ## Top

# In[1]:


import pandas as pd
import sys,os,inspect
import calendar
from datetime import datetime
from datetime import timedelta
#from cronsim import CronSim
import argparse
import json
import ast
import pygsheets
from tabulate import tabulate
from difflib import SequenceMatcher

import PySimpleGUI as sg
#import PySimpleGUIWeb as sg
import pathlib
#from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import textwrap
import re
from shlex import split
import webbrowser
import subprocess
import collections
import pyglet,tkinter
from pyglet import font
from tkinter import Tk
import pygments.lexers
from chlorophyll import CodeView
import tkinter as tk
from tkinter import ttk,Button,Label


font.add_file('/etc/fonts/fonts/CENTAUR.TTF')
font='Courier 10 bold '
bicHome = "/home/joe/bic_etl/"
numWindows=0
headerStore = {}

colorPairs = [["#D6EAF8","#85C1E9"],["#b3f0ff","#33d6ff"],["#D5F5E3","#A3E4D7"],["#FCF3CF","#F7DC6F"]]
windowsOpen = {}
windowsOpen["main"] = []
windowsOpen["unique"] = []


import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

global datasets

if sys.platform == "linux":
    path="/home/joe/work/Logs/logs"
else:
    path= "\\\\wsl.localhost\\Ubuntu\\home\\joe\\work\\Logs\\"

logging = 2
today = datetime.today()
## Directory where dataset difintions will be store... this will be inside
## bic_etl/dataset_dirs/definitionDir
definitionDir = "defs" 
sourceDefFile = " "
nfieldsAdded = 0  # numbers of XREF Fields added
nfieldsAddedS = 0  # numbers of XREF Fields added for from scratch


## map etl dataset names to invenotry  dataset names:
mapTitles = {}
#mapTitles[etl title] = invenotry title
mapTitles["Other Names a Registered Entity Uses to Solicit Contributions"] = "Other Names a Registered Entity Uses to Solicit Contributions in Colorado"

mapTitles["Registration for Charities, Paid Solicitors, Professional Fundraising Consultants, and for-profit Public Benefit Corporations in Colorado"] =  "Registration of Charities, Paid Solicitors, Professional Fundraising Consultants, and for-profit Public Benefit Corporations in Colorado"



# "Recently Expired and Surrendered Liquor Licenses in Colorado"
# "Recently Expired and Surrendered Liquor Licenses in Colorado"


# ## Functions 1

# In[2]:


def showFile(file):
    fin = open(file,"r") 
    text = fin.readlines()
    string=""
    for aa in text:
        string+=aa
    root = Tk()
    root.title(file)
    codeview = CodeView(root, lexer=pygments.lexers.JavascriptLexer, color_scheme="monokai")
    codeview.pack(fill="both", expand=True)
    codeview.insert(tk.END,chars=string)
    root.mainloop()

#############################################################
    
def showInvFields(w4x4):
    values = list(zip(fields[w4x4]["source"],fields[w4x4]["cim"]))
    columns = ["Source","Transformed"]
    layout = [[sg.Text(f"Inventory Field List",font="CENTAUR 15 bold")],
              [sg.Button("Quit")],
               [sg.Table(values=values,text_color="black", auto_size_columns=False,enable_events=True,num_rows=20,font="CENTAUR 15",
                   justification='left',vertical_scroll_only=False,col_widths=30,
                    background_color="#F8C471",def_col_width = 20,
                   alternating_row_color="#FAE5D3",key='-INVFIELDS-',headings = columns)]
               ]
    

#    sg.theme(colorTheme)     
    window2 = sg.Window("Inventory Field List",layout,finalize=True,resizable=True)
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
    # tableFile1 = window2['-LOGSUMMARY-']
    # tableFile1.bind('<Button-1>', "Click")
   # headerStore[tableFile1] = columns
   # statsStore[tableFile1] = stats1

#############################################################

def getRecentErrorsNew():
    global ids,errorsByDate
    files = []
    print(path)
    ids={}
    for x in os.listdir(path):
            if re.findall("^log.json*",x):
                 # files2Process.append(x)
                 files.append(x)

    x = datetime.today() - timedelta(days=30)
    monthM = x.month  
    yearM = x.year
    ff=f"log_backup_{yearM}_{monthM}.json"
    files.append(ff)
    # files=["log.json.0"]
    errorsByDate = {}
    errorsByName = {}
    found2=False
    bad = []
    tim=0
    nfile=0
   # print(sorted(files))
    for file in sorted(files):
        print("Processing ",file)
        try:
            jsf = open(f"{path}/{file}")
            found=True
        except:
            print(f"File not found {path}/{file}")
            sg.Popup(f"File NOT FOUND, Please Download it {path}/{file}")
            found=False
           
        if found:  
                log=[]
                nline=0
                nfile+=1
                for line in jsf:
                    try: 
                         xl=line.lower()

                         if "error" in xl and "metadata" not in xl:
                    #     if "error" in xl :
                             log.append(ast.literal_eval(line))
                    except Exception as err:
                       print("ERROR ",err)
                       bad.append(line)
                       print("BAD ",line)
                    nline+=1
                    
                    
                if  len(log) > 0 and  found2 == False:
                    msg = log[0]
                    time0 = datetime.strptime(msg['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    name0 = msg['name'].strip()
                    found2=True
                   # print("TIME0 ",file,time0)
                    
             #   tim=0
                if found2:
                  for line in log:
                  #  print(line['time'],line['name'])
                    time = line['time']
                    time1 = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")
                    diff = time1-time0
                    name1 = line['name'].strip()
                  #  print(name0,name1,time0,time1,diff.total_seconds())
                    if name1 == name0 and  abs(diff.total_seconds()) < 1:
                        same=True
                      #  print("    ",tim,name0,name1)
                    else:
                        tim+=1
                    name0=name1
                    time0=time1
                    
                    spl = time.split("T")
                    time = spl[0]
                    name = line['name'].strip()

                    msg= line['msg'].strip()

                    emsg = ""
                    if "err" in line:
                        emsg = line['err']
                #        msg+= f"\n\n-------------\n{err}"


                    uid = f"{line['time']}{msg[1:20]}"
                    if uid in ids:
                        ids[uid]+=1
                    else:
                        ids[uid]=1

                    stitle=""
                    xm = msg.find("Full ETL failure for ")
                    if xm > -1:
                       stitle = msg[xm+20:].split(":")[0]
                       stitle=stitle.replace(" at load","")

                    xm = msg.find("Error Loading ")
                    if xm > -1:
                       stitle = msg[xm+14:]

                    xm = msg.find("Error Extracting ")
                    if xm > -1:
                       stitle=msg[xm+16:]

                    xm = msg.find("Error Transforming ")
                    if xm > -1:
                       stitle=msg[xm+18:]

                #   
                    titl=""
                    s4x4=""
                    w4x4=""
                    try:
                        s4x4s = re.findall("[\w]{3,4}-[\w]{3,4}",line['msg'])


                        if len(s4x4s) > 0:
                          for s4x4 in s4x4s:
                             if s4x4 in xrefsBy4x4:
                                titl = xrefsBy4x4[s4x4]
                                w4x4=s4x4


                    except:
                        titl=""


                    if tim in errorsByDate:
                        errorsByDate[tim]['name'].append(name)
                        errorsByDate[tim]['msg'].append(msg)
                        errorsByDate[tim]['emsg'].append(emsg)
                        errorsByDate[tim]['line'].append(line)
                        errorsByDate[tim]['file'].append(file)
                        errorsByDate[tim]['title'].append(titl)
                        errorsByDate[tim]['stitle'].append(stitle)
                        errorsByDate[tim]['4x4'].append(w4x4)
                        errorsByDate[tim]['uid'].append(uid)
                        errorsByDate[tim]['time'].append(time)
                        

                    else:
                        errorsByDate[tim] = {}
                        errorsByDate[tim]['name'] = []
                        errorsByDate[tim]['msg'] = []
                        errorsByDate[tim]['emsg'] = []              
                        errorsByDate[tim]['line'] = []
                        errorsByDate[tim]['file'] = []
                        errorsByDate[tim]['title'] = []
                        errorsByDate[tim]['stitle'] = []
                        errorsByDate[tim]['4x4'] = []
                        errorsByDate[tim]['uid'] = []
                        errorsByDate[tim]['time'] = []
                        

                        errorsByDate[tim]['name'].append(name)
                        errorsByDate[tim]['msg'].append(msg)
                        errorsByDate[tim]['emsg'].append(emsg)            
                        errorsByDate[tim]['line'].append(line)
                        errorsByDate[tim]['file'].append(file)
                        errorsByDate[tim]['title'].append(titl)
                        errorsByDate[tim]['stitle'].append(stitle)
                        errorsByDate[tim]['4x4'].append(w4x4)
                        errorsByDate[tim]['uid'].append(uid)
                        errorsByDate[tim]['time'].append(time)
                        



                    if name in errorsByName:
                            errorsByName[name]['time'].append(tim)
                            errorsByName[name]['msg'].append(msg)
                            errorsByName[name]['line'].append(line)
                            errorsByName[name]['file'].append(file)
                            errorsByName[name]['title'].append(titl)
                    else:
                        errorsByName[name] = {}
                        errorsByName[name]['time'] = []
                        errorsByName[name]['msg'] = []
                        errorsByName[name]['line'] = []
                        errorsByName[name]['file'] = []
                        errorsByName[name]['title'] = []

                        errorsByName[name]['time'].append(tim)
                        errorsByName[name]['msg'].append(msg)
                        errorsByName[name]['line'].append(line)
                        errorsByName[name]['file'].append(file)
                        errorsByName[name]['title'].append(titl)

#                 except Exception as err:
#                     print(err)
#                     print(line)
    return errorsByDate,errorsByName

#################################################

def getRecentErrors():
    global ids,errorsByDate
    files = []
    print(path)
    ids={}
    for x in os.listdir(path):
            if re.findall("^log.json*",x):
                 # files2Process.append(x)
                 files.append(x)

    x = datetime.today() - timedelta(days=30)
    monthM = x.month  
    yearM = x.year
    ff=f"log_backup_{yearM}_{monthM}.json"
    files.append(ff)
    # files=["log.json.0"]
    errorsByDate = {}
    errorsByName = {}
    print(files)
    bad = []
    for file in files:
        print(file)
        try:
            jsf = open(f"{path}/{file}")
            found=True
        except:
            print(f"File not found {path}/{file}")
            sg.Popup(f"File NOT FOUND, Please Download it {path}/{file}")
            found=False
           

        if found:  
                log=[]
                nline=0
                for line in jsf:
                    try: 
                         xl=line.lower()

                         if "error" in xl and "metadata" not in xl:
                    #     if "error" in xl :
                             log.append(ast.literal_eval(line))
                    except Exception as err:
                       print("ERROR ",err)
                       bad.append(line)
                       print("BAD ",line)
                    nline+=1

                for line in log:
                  #  print(line['time'],line['name'])
                    tim = line['time']

                    spl = tim.split("T")
                    tim = spl[0]
                    name = line['name'].strip()

                    msg= line['msg'].strip()

                    if "err" in line:
                        err = line['err']
                        msg+= f"\n\n-------------\n{err}"


                    uid = f"{line['time']}{msg[1:20]}"
                    if uid in ids:
                        ids[uid]+=1
                    else:
                        ids[uid]=1

                    stitle=""
                    xm = msg.find("Full ETL failure for ")
                    if xm > -1:
                       stitle = msg[xm+20:].split(":")[0]
                       stitle=stitle.replace(" at load","")

                    xm = msg.find("Error Loading ")
                    if xm > -1:
                       stitle = msg[xm+14:]

                    xm = msg.find("Error Extracting ")
                    if xm > -1:
                       stitle=msg[xm+16:]

                    xm = msg.find("Error Transforming ")
                    if xm > -1:
                       stitle=msg[xm+18:]

                #   
                    titl=""
                    s4x4=""
                    w4x4=""
                    try:
                        s4x4s = re.findall("[\w]{3,4}-[\w]{3,4}",line['msg'])


                        if len(s4x4s) > 0:
                          for s4x4 in s4x4s:
                             if s4x4 in xrefsBy4x4:
                                titl = xrefsBy4x4[s4x4]
                                w4x4=s4x4


                    except:
                        titl=""


                    if tim in errorsByDate:
                        errorsByDate[tim]['name'].append(name)
                        errorsByDate[tim]['msg'].append(msg)
                        errorsByDate[tim]['line'].append(line)
                        errorsByDate[tim]['file'].append(file)
                        errorsByDate[tim]['title'].append(titl)
                        errorsByDate[tim]['stitle'].append(stitle)
                        errorsByDate[tim]['4x4'].append(w4x4)
                        errorsByDate[tim]['uid'].append(uid)

                    else:
                        errorsByDate[tim] = {}
                        errorsByDate[tim]['name'] = []
                        errorsByDate[tim]['msg'] = []
                        errorsByDate[tim]['line'] = []
                        errorsByDate[tim]['file'] = []
                        errorsByDate[tim]['title'] = []
                        errorsByDate[tim]['stitle'] = []
                        errorsByDate[tim]['4x4'] = []
                        errorsByDate[tim]['uid'] = []

                        errorsByDate[tim]['name'].append(name)
                        errorsByDate[tim]['msg'].append(msg)
                        errorsByDate[tim]['line'].append(line)
                        errorsByDate[tim]['file'].append(file)
                        errorsByDate[tim]['title'].append(titl)
                        errorsByDate[tim]['stitle'].append(stitle)
                        errorsByDate[tim]['4x4'].append(w4x4)
                        errorsByDate[tim]['uid'].append(uid)



                    if name in errorsByName:
                            errorsByName[name]['time'].append(tim)
                            errorsByName[name]['msg'].append(msg)
                            errorsByName[name]['line'].append(line)
                            errorsByName[name]['file'].append(file)
                            errorsByName[name]['title'].append(titl)
                    else:
                        errorsByName[name] = {}
                        errorsByName[name]['time'] = []
                        errorsByName[name]['msg'] = []
                        errorsByName[name]['line'] = []
                        errorsByName[name]['file'] = []
                        errorsByName[name]['title'] = []

                        errorsByName[name]['time'].append(tim)
                        errorsByName[name]['msg'].append(msg)
                        errorsByName[name]['line'].append(line)
                        errorsByName[name]['file'].append(file)
                        errorsByName[name]['title'].append(titl)

#                 except Exception as err:
#                     print(err)
#                     print(line)
    return errorsByDate,errorsByName

####################################################################

def getXrefs():
    '''Reads the Inventory google sheet and gets the datasets title and cross-refs it to the Socrata 4x4 id.  Also
    gets the fields by 4x4 dataset id and by the title'''
    scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
             "https://www.googleapis.com/auth/drive.file",
                  "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name('/home/joe/work/client_secret.json',
     scope)
    client = gspread.authorize(creds)

    gc = gspread.service_account("/home/joe/work/client_secret.json")
    # for gg in gc.list_spreadsheet_files():
    #      print("GGGGG ",gg)
    # https://docs.google.com/spreadsheets/d/1WTaOglzbSsYiHhAGguGxHQXmAGmOhfFHkGkMLowxAOA/edit?usp=sharing
    sheet = client.open('BIC Data Inventory and Metadata').worksheet(
        'Maintenance_Framework')
    repo_sheet = client.open('BIC Data Inventory and Metadata').worksheet(
        'MetadataRepository')
    fields_sheet = client.open('BIC Data Inventory and Metadata').worksheet(
        'Field Descriptions')
    
    
#     sheet = client.open('https://docs.google.com/spreadsheets/d/1Xc7oYpdCLwHmUCaokpfXkF4bzkwRW0xUbvBZwruF0ZI/').worksheet(
#         'Maintenance_Framework')
#     repo_sheet = client.open('https://docs.google.com/spreadsheets/d/1Xc7oYpdCLwHmUCaokpfXkF4bzkwRW0xUbvBZwruF0ZI/').worksheet(
#         'MetadataRepository')
    
#     fields_sheet = client.open('https://docs.google.com/spreadsheets/d/1Xc7oYpdCLwHmUCaokpfXkF4bzkwRW0xUbvBZwruF0ZI/').worksheet(
#         'Field Descriptions')

    dfRepo = pd.DataFrame(repo_sheet.get_all_records(head=3))
    xrefsBy4x4 = {}
    xrefsByTitle = {}

    for index,row in dfRepo[['Dataset Title','Socrata Link']].iterrows():
        xrefsByTitle[row['Dataset Title']] = row['Socrata Link']
        xrefsBy4x4[row['Socrata Link']] = row['Dataset Title']
        
    dfFields = pd.DataFrame(fields_sheet.get_all_records(head=1))
    fields = {}
    for index,row in dfFields.iterrows():
        s4x4 = row["Socrata ID"]
        of = row["Source Field Name"]
        tf = row["Full Field Name"]
        af = row["API Field Name"]
        des = row["Description"]
        if s4x4 in fields:
            fields[s4x4]["source"].append(of)
            fields[s4x4]["cim"].append(tf)
            fields[s4x4]["api"].append(af)
            fields[s4x4]["description"].append(des)
        
        else:
            fields[s4x4] = {}
            fields[s4x4]["source"] = []
            fields[s4x4]["cim"] = []
            fields[s4x4]["api"] = []
            fields[s4x4]["description"] = []
            
            
            fields[s4x4]["source"].append(of)
            fields[s4x4]["cim"].append(tf)
            fields[s4x4]["api"].append(af)
            fields[s4x4]["description"].append(des)
            
        
        
        
    return xrefsBy4x4,xrefsByTitle,fields

############################################################

def toGoogleSheet(row):
    '''Reads the Inventory google sheet and gets the datasets title and cross-refs it to the Socrata 4x4 id.  Also
    gets the fields by 4x4 dataset id and by the title'''
    # scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
    #          "https://www.googleapis.com/auth/drive.file",
    #               "https://www.googleapis.com/auth/drive"]

    path='/home/joe/work/client_secret.json'
    gc=pygsheets.authorize(service_account_file=path)
    sh=gc.open('Changes/Fixes Requested by BIC')
    wk1=sh[0]
    ret = wk1.append_table(row)
    return ret

#########################################################

def markDone(row):
    '''Reads the Inventory google sheet and gets the datasets title and cross-refs it to the Socrata 4x4 id.  Also
    gets the fields by 4x4 dataset id and by the title'''
    # scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
    #          "https://www.googleapis.com/auth/drive.file",
    #               "https://www.googleapis.com/auth/drive"]

    path='/home/joe/work/client_secret.json'
    gc=pygsheets.authorize(service_account_file=path)
    sh=gc.open('ETL Errors Accounted For')
    wk1=sh[0]
    ret = wk1.append_table(row)
    return ret

#################################################################

def getErrorStatus():
    '''Reads the Inventory google sheet and gets the datasets title and cross-refs it to the Socrata 4x4 id.  Also
    gets the fields by 4x4 dataset id and by the title'''
    # scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
    #          "https://www.googleapis.com/auth/drive.file",
    #               "https://www.googleapis.com/auth/drive"]

    path='/home/joe/work/client_secret.json'
    gc=pygsheets.authorize(service_account_file=path)
    sh=gc.open('ETL Errors Accounted For')
    wk1=sh[0]
    df = wk1.get_as_df()
    x=df[["Unique ID","Status"]].values.tolist()
    
    return {y[0]:y[1] for y in x}

#################################################################

def getLogSummary():
    '''Reads the Inventory google sheet and gets the datasets title and cross-refs it to the Socrata 4x4 id.  Also
    gets the fields by 4x4 dataset id and by the title'''
    # scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
    #          "https://www.googleapis.com/auth/drive.file",
    #               "https://www.googleapis.com/auth/drive"]

    path='/home/joe/work/client_secret.json'
    gc=pygsheets.authorize(service_account_file=path)
    sh=gc.open('Changes/Fixes Requested by BIC')
    wk1=sh[0]
    df = wk1.get_as_df()
    x=df.values.tolist()
    
    return x,list(df.columns)

#################################################################

def showError(row):
    layout = [
        [sg.Button("Quit")],
        [sg.Button("Write Log")],
        [sg.Button("Mark Done"),sg.Button("Mark Skip")],
        [sg.Multiline("",s=(50,10),key="-ERRORSINGLE-",font="CENTAUR 15 bold")],
        [sg.Text("Title: ",font="CENTAUR 15 bold"),
         sg.Multiline("",s=(50,2),key="-ERRORTITLE-",font="CENTAUR 15 bold",text_color="black")],
         [sg.Multiline("JIRA BIC-",s=(10,2),key="-ERRORJIRA-",font="CENTAUR 15 bold")],
        [sg.Text("NOTES: ",font="CENTAUR 15 bold"),
         sg.Multiline("",s=(20,10),key="-ERRORNOTES-",font="CENTAUR 15 bold")]
        
    ]
    window = sg.Window('Show Error', layout, finalize=True,metadata=row)
    window["-ERRORSINGLE-"].print(f"Date: {row[0]}", text_color='black')
    window["-ERRORSINGLE-"].print(f"Dataset: {row[1]}", text_color='black')
    window["-ERRORSINGLE-"].print(f"4x4: {row[2]}", text_color='black')
    window["-ERRORSINGLE-"].print(f"Title: {row[3]}", text_color='black')
    window["-ERRORSINGLE-"].print(f"Stitle: {row[5]}", text_color='black')
    
    window["-ERRORSINGLE-"].print(f"\nMessage:\n{row[4]}", text_color='red')
    if len(row[3]) > 10:
       window["-ERRORTITLE-"].print(f"{row[3]}", text_color='black')
    elif len(row[5]) > 10:
       window["-ERRORTITLE-"].print(f"{row[5]}", text_color='black')
        
##############################################################################       
                                  
def showRecentLogs(errorsByDate):
    xx = []
    colWidths = (10,10,10,80)
    rowColors = []
    count=0
    date0=list(errorsByDate.keys())[0]
    cols=("plum4")
    bg="white"
    bgs=[]
    count2=0
    order = {}
    for nn in errorsByDate.keys():
        order[nn]= min(errorsByDate[nn]["time"])
    
    order = sorted(order.items(), key=lambda x:x[1], reverse=True)

    
    
    errorStatus = getErrorStatus()
 #   for date in sorted(errorsByDate,reverse=True):
    for mrec in order:
        date = mrec[0]
        
        string=f"Date: {date};;\n\n"
        msg=""
        for nn in range(len(errorsByDate[date]["name"])):
    #        print(f'    {errorsByDate[date]["name"][nn]}\n      M {errorsByDate[date]["msg"][nn]}\n      F{errorsByDate[date]["file"][nn]}\n      L {errorsByDate[date]["line"][nn]}\n')
        
          #  msg = textwrap.fill(errorsByDate[date]["msg"][nn],75)
            if nn > 0:
                msg+="\n-----------------------------------\n"
            msg+= errorsByDate[date]["msg"][nn]
            uid = errorsByDate[date]["uid"][nn]
            if uid not in errorStatus:
           ##     yy = [date,errorsByDate[date]["name"][nn],errorsByDate[date]["4x4"][nn],errorsByDate[date]["title"][nn],msg,errorsByDate[date]["stitle"][nn],errorsByDate[date]["uid"][nn]]
           ##     xx.append(yy)
                if date != date0:
                    count+=1
                    if count%2 == 0:
                        cols = ("plum4")
                        bg="white"
                    else:
                        cols = ("SteelBlue3")
                        bg="black"
                if count2%2 == 0:
                    cols="plum4"
                else:
                    cols="SteelBlue3"
                count2+=1
                date0=date
                rowColors.append(cols)
                bgs.append(bg)
        yy = [errorsByDate[date]["time"][0],errorsByDate[date]["name"][0],errorsByDate[date]["4x4"][0],errorsByDate[date]["title"][0],msg,errorsByDate[date]["stitle"][nn],errorsByDate[date]["uid"][0]]
        xx.append(yy)

    rowNums = [num for num in range(0,len(rowColors)+1)]
    colrw = list(zip(rowNums,rowColors))
    colrw=list(zip(rowNums,bgs,rowColors))
   
 #   print("XX XX XX",xx)

    header = ["Date","Dataset","4x4","Title","Message","Title Guess","UID"]

    layout = [
        [sg.Button("Quit",font="CENTAUR 15 bold")],
        [sg.Button("Include Completed",visible=True,font="CENTAUR 15 bold"),
         sg.Button("Hide Completed",visible=False,font="CENTAUR 15 bold")],
        [sg.Text("Errors for the Last 2 Months",font="CENTAUR 15 bold")],
        [sg.Table(values=xx,headings=header,visible_column_map=[True,True,True,True,True,False,False], size=(120, 30),row_height=40,row_colors=colrw,vertical_scroll_only=False,max_col_width=60,enable_events=True, key='-DAILY-',col_widths=colWidths)],
        [sg.Push(), sg.Button('Update')],
    ]
    window = sg.Window('Title', layout, finalize=True,metadata=xx)
    table = window["-DAILY-"]  
    table.bind('<Button-1>', "Click")
    window["-DAILY-"].Widget.column('#4', anchor='w') 
    return window

##############################################################################

def updateLogs(how=1):
    #  how    1 = update just this month (log.json.nn
    #         2 = update Last Months file (log_backup_year_mo.json
    #         3 = update all this years log files 
    pw=os.environ["OIT_PW"]
    #  compute previous month
    x = datetime.today() - timedelta(days=30)
    monthM = x.month  
    yearM = x.year
    print("Updating ETL Error Logs", flush=True)
    year = datetime.today().year
    
    string = f'''sshpass -p {pw} sftp -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa  giddensm@165.127.62.8 << !'''

    if how == 1:  #  update this month
        string+= f"\nmget /usr/local/cim/bic_etl/general/logs/log.json* {path}"
##  remove all of this months logs first to account for month changes
        print("\nCleaning Up Old FIles for THIS Month\n", flush=True)
        for x in os.listdir(path):
            if  re.findall("^log.json\.\d+",x):
                 file=f"{path}/{x}"
                 print("Removing Local Log File",file, flush=True)
                 os.remove(file)
        file=f"{path}/log.json"
        print("Removing Local Log File",file, flush=True)
        os.remove(file)
        
    elif how == 2: 
        string+=f"\nmget /usr/local/cim/bic_etl/general/logs/log_backup_{yearM}_{monthM}*.json {path}"
    elif how == 3:
        string+=f"\nmget /usr/local/cim/bic_etl/general/logs/log_backup_{year}*.json {path}"
    
    string+="\n!'''"

 #   print(string)
    result=subprocess.run([string], shell=True, stdout=subprocess.PIPE)
    x = str(result.stdout)
    nfiles=0
    files=x.split("\\n")
    filesOut=[]
    for line in files:
     #   print(line)
        if "fetch" in line.lower():
            nfiles+=1
            filesOut.append(line)      
            
    return nfiles,filesOut
    
##################################################

def orderErrors(errorsByDate,errorStatus,flag):
    xx=[]
    bgs=[]
    rowColors=[]
    date0=list(errorsByDate.keys())[0]
    count=0
    count2=0
    cols=("plum4")
    bg="white"
    for date in sorted(errorsByDate,reverse=True):
        string=f"Date: {date};;\n\n"
        for nn in range(len(errorsByDate[date]["name"])):
            msg = errorsByDate[date]["msg"][nn]
            uid = errorsByDate[date]["uid"][nn]
            if uid not in errorStatus or flag==1:
                yy = [date,errorsByDate[date]["name"][nn],errorsByDate[date]["4x4"][nn],errorsByDate[date]["title"][nn],msg,errorsByDate[date]["stitle"][nn],errorsByDate[date]["uid"][nn]]
                xx.append(yy)
                if date != date0:
                    count+=1
                    if count%2 == 0:
                        cols = ("plum4")
                        bg="white"
                    else:
                        cols = ("SteelBlue3")
                        bg="black"
                if count2%2 == 0:
                    cols="plum4"
                else:
                    cols="SteelBlue3"
                count2+=1
                date0=date
                if uid in errorStatus:
                    cols="grey"
                rowColors.append(cols)
                bgs.append(bg)


    rowNums = [num for num in range(0,len(rowColors)+1)]
  # colrw = list(zip(rowNums,rowColors))
    colrw=list(zip(rowNums,bgs,rowColors))
    return xx,colrw
   
#####################################################################

def showLogSummary(values,columns):
    layout = [[sg.Text(f"Log Summary",font="CENTAUR 15 bold")],
              [sg.Button("Quit")],
               [sg.Table(values=values,text_color="black", auto_size_columns=False,enable_events=True,num_rows=10,font="CENTAUR 10",
                   justification='left',vertical_scroll_only=False,background_color="#F8C471",
                   alternating_row_color="#FAE5D3",key='-LOGSUMMARY-',headings = columns)]
               ]
    

#    sg.theme(colorTheme)     
    window2 = sg.Window("Log Summary",layout,finalize=True,resizable=True)
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
    tableFile1 = window2['-LOGSUMMARY-']
    tableFile1.bind('<Button-1>', "Click")
   # headerStore[tableFile1] = columns
   # statsStore[tableFile1] = stats1
   
    return window2

############################################

def reorderList(string:str,a:list):
    ''' If string exists in list a, it will be moved to the top of the list '''
    b = a.copy()
    if string in b:
        ai = b.index(string)
        b.pop(ai)
        c = [string]
        c[1:] = b
    else:
        c=a.copy()
        
    return c

############################################

def getMostLike(a:str,b:list):
    '''Searchs a list of strings for the value that is most like input the string a
       Returns the string most like a
       
       col = getMostLike("someString",someList)
    '''
    rmax = SequenceMatcher(None,a.lower(),b[0].lower()).ratio()
    column=b[0]
    if len(b) > 1:
        for col in b[1:]:
            r=SequenceMatcher(None,a.lower(),col.lower()).ratio()
            if r > rmax:
                rmax=r
                column=col
    return column

#####################################################

def writeFieldFile(w4x4,values,tmp,dirr):
    mapped = {}
    mapped[w4x4] = {}
    xrefs = {}
    notes = {}
    dates = {}
    print("DDIR ",dirr)
    for key,val in values.items():
        print(key,val)
        if isinstance(key,str) and ":" in key:
       #     'LISTBOX:entityId': 'Entity Id', 0: 'Entity Id', 'NOTES:entityId':
            spl = key.split(":")
            val = val.strip()
            spl[1]=spl[1].strip()
            spl[0]=spl[0].strip()


            if spl[0] == "LISTBOX":  
                if val not in mapped[w4x4]:                        
                    mapped[w4x4][val] = {}  
                mapped[w4x4][val]["xref"] =spl[1]
                mapped[w4x4][val]["desc"] = tmp[spl[1]]
                xrefs[spl[1]] = val
            elif spl[0] == "NOTES":
                notes[spl[1]] = val
            elif spl[0] == "DATE":
                dates[spl[1]] = val
    for id in notes:
        xrf = xrefs[id]
        mapped[w4x4][xrf]["notes"] = notes[id]
        mapped[w4x4][xrf]["date"] = dates[id]

#    print("MAP ",mapped) 
    out = f"{dirr}/{w4x4}_fields.json"
    with open(out,"w") as jfile:
        jfile.write(json.dumps(mapped))


##########################################################

def createFieldFile(w4x4,orig,trans):
    todayDate=f"{today.year}-{today.month}-{today.day}"    
    tmp = {}
# create a dictionary of the descripitons of the transform fields for easy lookup
    for nn,fld in enumerate(fields[w4x4]['cim']):
        tmp[fld] = fields[cim4x4]['description'][nn]
    tmpT2O = {}
    for col in trans:
        cc = getMostLike(col,orig)
        tmpT2O[col]=cc
    col1 = []
    col2 = []
    col3 = []
    rows = []
    origTmp = orig.copy()
    for col in trans:
        if col in tmp:
          row=[]
          origTmp = reorderList(tmpT2O[col],sorted(origTmp))
          row.append(sg.Combo(origTmp,default_value=tmpT2O[col],enable_events=True,  
                                font='Courier 15 bold ',key=f"LISTBOX:{col}",
                         #       select_mode="LISTBOX_SELECT_MODE_SINGLE",
                                size=(20,6)))
          row.append(sg.Text(col,font='Courier 15 bold ',size=(30,1)))
          row.append(sg.Multiline(tmp[col],font='Courier 12',size=(30,2)))
          row.append(sg.Multiline("",font='Courier 12',size=(30,2),key=f"NOTES:{col}"))
          row.append(sg.Input(todayDate,font='Courier 15 bold ',size=(10,1),key=f"DATE:{col}"))
        
          rows.append([sg.Frame("",[row])])
            
    layout = [[sg.Button("Quit"),sg.Button("Write Fields")],rows]
             
    sg.theme("LightBrown6")     
    window2 = sg.Window("Log Summary",layout,finalize=True,resizable=True)
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
    
##########################################################
    
def tkPopup(string,title,bgColor="grey"):
    toWrite=False
    def close():
       popup.destroy()
       popup.quit()

    popup = tk.Tk()
    popup.wm_title(title)
    label = Label(popup, text=string,font=('Courier',20),justify="left", relief="groove")
    label.configure(bg=bgColor)
    label.pack(side="top", fill="x", pady=10)
    my_button= Button(popup, text= "OK", font=('Courier',25),
    borderwidth=2, command= close)
    my_button.pack(pady=20)
    popup.mainloop()
      
##########################################################
    
def tkPopupWrite(w4x4,string,title,bgColor="grey"):
    toWrite=False
    def close():
       popup.destroy()
       popup.quit()
    
    def toFile():
       with open(f"{w4x4}_source_field_defintions.json","w") as jfile:
            jfile.write(json.dumps(mapping))

       popup.destroy()
       popup.quit()
        
    popup = tk.Tk()
    popup.wm_title(title)
    label = Label(popup, text=string,font=('Courier',20),justify="left", relief="groove")
    label.configure(bg=bgColor)
    label.pack(side="top", fill="x", pady=10)
    my_button_w= Button(popup, text= "Write", font=('Courier',25),
    borderwidth=2, command= toFile)
    my_button_w.pack(pady=20)
    
    my_button= Button(popup, text= "Cancel", font=('Courier',25),
    borderwidth=2, command= close)
    my_button.pack(pady=20)
    popup.mainloop()

###################################################################################

def tkPopScroll(string,someFunc,outF,mapping):
    def close():
       root.destroy()
       root.quit()

    
    
    root = tk.Tk()
    root.resizable(False, False)
    root.title("Scrollbar Widget Example")

    # apply the grid layout
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    # create the text widget
    text = tk.Text(root, height=10)
    text.grid(row=0, column=0, sticky=tk.EW)

    # create a scrollbar widget and set its command to the text widget
    scrollbar = ttk.Scrollbar(root, orient='vertical', command=text.yview)
    scrollbar.grid(row=0, column=1, sticky=tk.NS)

    #  communicate back to the scrollbar
    text['yscrollcommand'] = scrollbar.set

    # add sample text to the text widget to show the screen
    # for i in range(1,50):
    #     position = f'{i}.0'
    for nn,val in enumerate(string.split("\n")):
       m = float(nn+1)
       text.insert(f"{m}",f"{val}\n")

    my_button= Button(root, text= "Cancel", font=('Courier',15),
    borderwidth=2, command= close)
    my_button.grid(row=nn+2, column=0, sticky=tk.EW)
    
    my_buttonW= Button(root, text= "Write", font=('Courier',15),
    borderwidth=2, command= lambda: someFunc(root,outF,mapping))
    my_buttonW.grid(row=nn+2, column=1, sticky=tk.EW)
    
 #   my_button.pack(pady=20)
    root.mainloop()
     
###################################################################################

def tkPopScrollSimple(string):
    def close():
       root.destroy()
       root.quit()

    root = tk.Tk()
    root.resizable(False, False)
    root.title("Scrollbar Widget Example")

    # apply the grid layout
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    # create the text widget
    text = tk.Text(root, height=10)
    text.grid(row=0, column=0, sticky=tk.EW)

    # create a scrollbar widget and set its command to the text widget
    scrollbar = ttk.Scrollbar(root, orient='vertical', command=text.yview)
    scrollbar.grid(row=0, column=1, sticky=tk.NS)

    #  communicate back to the scrollbar
    text['yscrollcommand'] = scrollbar.set

    # add sample text to the text widget to show the screen
    # for i in range(1,50):
    #     position = f'{i}.0'
    for nn,val in enumerate(string.split("\n")):
       m = float(nn+1)
       text.insert(f"{m}",f"{val}\n")

    my_button= Button(root, text= "OK", font=('Courier',15),
    borderwidth=2, command= close)
    my_button.grid(row=nn+2, column=0, sticky=tk.EW)
    
    root.mainloop()
        
###########################################################################

def toFile(win,outF,mapping):
       print("writing out file")
       with open(outF,"w") as jfile:
            jfile.write(json.dumps(mapping))
        
       win.destroy()
       win.quit()

######################################################################################
    
def writeSoureFieldList(w4x4,values,targDir,datasetCharId):      
    mapping = {}
    for k,v in values.items():
        if k[:4] == "DEFS":
           if v not in mapping:
              mapping[v] = []
           mapping[v].append(k[6:].strip())
    stringGood=""
    stringBad=""
    nbad=0
    finalMap = {}
    for col,v in mapping.items():
        if len(v) > 1:
           for val in v:
                stringBad+= f"{col}  -> {val}\n"
           nbad+=1
           stringBad+= f"\n"
        else:
           stringGood+= f"{col}  -> {v[0]}\n\n"
           finalMap[col] = v[0]
        
    if len(stringBad) > 0:
        stringAll = f"Dataset: w4x4\nError Inputing Definitions for Source Fields\n"
        stringAll+= f"{nbad} out of {len(mapping)} Fields have Multiple Definitions\n\n"
        print(f"Bad {nbad} out of {len(mapping)} ",stringBad)
        stringAll+=stringBad
        tkPopup(stringAll,"Errors in Creating Source Definitions","pink")
    else:
        print("Good",stringGood)
        outFile = os.path.join(targDir,f"{w4x4}_{datasetCharId}_src_fld_defs.json")
        print("OUTFILE ",outFile)
 #       tkPopupWrite(w4x4,stringGood,"Creating Source Definitions","white")
        tkPopScroll(stringGood,toFile,outFile,finalMap)
    return outFile
    
################################################################

def createDir(targDir):
    '''Creates a directory (targDir) if it does not exist
    '''
    print(targDir)
    if os.path.isdir(targDir):
        string=f"{targDir}\nAll Ready Exists"
        sg.popup(string)
    else:
        os.mkdir(targDir)
        string=f"Created Directory {targDir}"
        sg.popup(string)
        
##################################################################

def createSrcTransFieldXref(w4x4,orig,trans,srcDefFile,targDir):
    '''
    This function creates a Cross Reference List between the 
    Source Field List and Transform Field list for a dataset
    A form will be created and seeded with the Source Field list and 
    Descriptions found in the srcDefFile.  This will thne use the trans
    column listsing for the Transformed Fields to  guess a best match
    for each Source Field.  Users will then be able to fix the guesses 
    for the Transformed Fields.
    The Form allows users to create a new Transform Field if needed.
    The Form also allows for the creation of totally NEW Source and Transform
    listings    
    '''
    todayDate=f"{today.year}-{today.month}-{today.day}"    
    tmp = {}
# create a dictionary of the descripitons of the transform fields for easy lookup
## If there is a source definition file, use it to seed the defintion/descriptions
    if len(srcDefFile) > 4:
        fin = open(sourceDefFile,"r")
        tmp=json.load(fin)
    else:
        # for nn,fld in enumerate(fields[w4x4]['cim']):
        #     tmp[fld] = fields[cim4x4]['description'][nn]
        sg.popup("No Source Definition File Found")
        return "  "
    tmpO2T = {}
    for col in orig:
        cc = getMostLike(col,trans)
        tmpO2T[col]=cc
    col1 = []
    col2 = []
    col3 = []
    rows = []
    transTmp = trans.copy()
    row=[]
    rowC=[]
    
 #   ["Source Field","Transformed Field","Description","Date","Notes"]
    row.append(sg.Text("Source Field",font='Courier 15 bold ',text_color="black",justification="left",size=(30,1))) 
    rowC.append(sg.Text("Source Field",font='Courier 15 bold ',text_color="black",key="HC1",justification="center",size=(30,1))) 

    row.append(sg.Text("Transformed Field",font='Courier 15 bold ',text_color="black",justification="left",size=(30,1)))    
    rowC.append(sg.Text("Transformed Field",font='Courier 15 bold ',text_color="black",key="HC2",justification="center",size=(30,1)))    

    row.append(sg.Text("Description",font='Courier 15 bold ',text_color="black",justification="left",size=(30,1)))    
    rowC.append(sg.Text("Description",font='Courier 15 bold ',text_color="black",key="HC3",justification="center",size=(30,1)))    

    row.append(sg.Text("Notes",font='Courier 15 bold ',text_color="black",justification="left",size=(30,1)))    
    rowC.append(sg.Text("Notes",font='Courier 15 bold ',text_color="black",key="HC4",justification="center",size=(30,1)))    

    row.append(sg.Text("Change Date",font='Courier 15 bold ',text_color="black",justification="left",size=(15,1)))   
    rowC.append(sg.Text("Change Date",font='Courier 15 bold ',text_color="black",key="HC5",justification="center",size=(15,1)))   

    #   frameCustHead = sg.Frame("",[row],key="FRAME:CUSTHEAD",visible=False)
    rows.append([sg.Frame("",[row],key="HEADER")])
    
    for col in orig:
        
          row=[]
          row.append(sg.Input(col,key=f"SOURCE:{col}",font='Courier 15 bold ',size=(30,1)))
##  put the most likely matching string on top of list, so it appears as first
##  option ins combo box
          transTmp = reorderList(tmpO2T[col],sorted(transTmp))
##  Add NONE as an option to account for No Matches in terms of a new field
          a=transTmp.copy()
          a.append("NONE")    
          row.append(sg.Combo(a,default_value=tmpO2T[col],enable_events=True,  
                                font='Courier 15 bold ',key=f"LISTBOX:{col}",
                         #       select_mode="LISTBOX_SELECT_MODE_SINGLE",
                                size=(30,6)))
          row.append(sg.Multiline(tmp[col],font='Courier 15',key=f"DESC:{col}",size=(30,2)))
          row.append(sg.Multiline("",font='Courier 15',size=(30,2),key=f"NOTES:{col}"))
          row.append(sg.Input(todayDate,font='Courier 15 bold ',size=(15,1),key=f"DATE:{col}"))
        
          rows.append([sg.Frame("",[row])])
        
    rowsC = []
    rowsC.append([sg.Frame("",[rowC],key="someFrame",visible=False)])

##  Add custom fields, make them invisible until needed, one by one    
    for nn in range(1,6):
          row=[]
         
          row.append(sg.Input("",
                                font='Courier 15 bold ',key=f"SOURCEC:CUST:{nn}",visible=True,
                         #       select_mode="LISTBOX_SELECT_MODE_SINGLE",visible=False,
                                size=(21,1),enable_events=False))
          row.append(sg.Input("",font='Courier 15 bold ',visible=True,key=f"TRANSC:CUST:{nn}",size=(31,1)))
          row.append(sg.Input("",font='Courier 15',size=(31,1),visible=True,key=f"DESCC:CUST:{nn}"))
          row.append(sg.Multiline("",font='Courier 15',size=(31,2),visible=True,key=f"NOTESC:CUST:{nn}"))
          row.append(sg.Input(todayDate,font='Courier 15 bold ',visible=True,size=(11,1),key=f"DATEC:CUST:{nn}"))
        
          rowsC.append([sg.Frame("",[row],visible = False,key=f"FRAME:CUST:{nn}")])
  #  rows.append([sg.Frame("Custom Fields",[rowsC])])
        
        
    layout = [[sg.Button("Quit"),sg.Button("Add XREF Field")],
               [sg.Button("Write XREF File")],
               [sg.Column(rows,scrollable=True)],
               [sg.Frame("Custom Fields",rowsC,font='Courier 15 bold ',visible=False,relief="sunken",key="secondFrame")]]
             
    sg.theme("LightBrown6")     
    window2 = sg.Window("Log Summary",layout,finalize=True,resizable=True)
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
      
    return transTmp

###############################################################

def showSrc2TransXrefs(file):
    '''  Display the Source to Transformed Fields Dictionary for the Dataset
    '''
    if not os.path.isfile(file):
       sg.popup(f"Source-Transform Dictionary File Does NOT EXIST..")
       return
    todayDate=f"{today.year}-{today.month}-{today.day}"    
    
    fin = open(file,"r")
    info = json.load(fin)
    rows=[]
    row=[]
    row.append(sg.Text("Source Field",font='Courier 15 bold ',background_color="#c2c2d6",text_color="black",justification="left",size=(30,1))) 
    row.append(sg.Text("Transformed Field",font='Courier 15 bold ',background_color="#c2c2d6",text_color="black",justification="left",size=(30,1)))    
    row.append(sg.Text("Description",font='Courier 15 bold ',background_color="#c2c2d6",text_color="black",justification="left",size=(31,1)))    
    row.append(sg.Text("Notes",font='Courier 15 bold ',background_color="#c2c2d6",text_color="black",justification="left",size=(31,1)))    
    row.append(sg.Text("Change Date",font='Courier 15 bold ',background_color="#c2c2d6",text_color="black",justification="left",size=(15,1)))   
    rows.append([row])
    nrows=0
    colors = ["#6699ff","#66ccff"]
    for w4x4,data in info.items():
        for col,defs in data.items():
              nrows+=1
              colr = colors[nrows%2]
              row=[]
              row.append(sg.Input(col,key=f"SOURCE:{col}",font='Courier 15 bold ',background_color=colr,size=(30,1)))
              row.append(sg.Input(defs['xref'],key=f"LISTBOX:{col}",background_color=colr,font='Courier 15 bold ',size=(30,1)))  
              row.append(sg.Multiline(defs['desc'],key=f"DESC:{col}",background_color=colr,font='Courier 15',size=(30,2)))
              row.append(sg.Multiline(defs['notes'],key=f"NOTES:{col}",background_color=colr,font='Courier 15',size=(30,2)))
              row.append(sg.Input(defs['date'],key=f"DATE:{col}",background_color=colr,font='Courier 15 bold ',size=(15,1)))
              rows.append(row)

        for nn in range(1,6):
              row=[]

              row.append(sg.Input("",
                                    font='Courier 15 bold ',key=f"SOURCEC:CUST",visible=True,
                             #       select_mode="LISTBOX_SELECT_MODE_SINGLE",visible=False,
                                    size=(21,1),enable_events=False))
              row.append(sg.Input("",font='Courier 15 bold ',visible=True,key=f"TRANSC:CUST:{nn}",size=(31,1)))
              row.append(sg.Multiline("",font='Courier 15',size=(31,2),visible=True,key=f"NOTESC:CUST:{nn}"))
              row.append(sg.Multiline("",font='Courier 15',size=(31,2),visible=True,key=f"NOTESC:CUST:{nn}"))
              row.append(sg.Input(todayDate,font='Courier 15 bold ',visible=True,size=(11,1),key=f"DATEC:CUST:{nn}"))



    header = ["Source Field","Transformed Field","Description","Notes","Date"]
    layout = [[sg.Text(f"Source-Transformed Field XREFS",font="CENTAUR 15 bold")],
              [sg.Text(f"{file}",font="CENTAUR 15 bold")],
              [sg.Button("Quit"),sg.Button("Add XREF Fields")],
              [sg.Button("Write XREF File")],
              rows     
               ]
    

#    sg.theme(colorTheme)     
    window2 = sg.Window("Source-Transform Field XREFS",layout,background_color="white",finalize=True,resizable=True)
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
    
#######################################################

def analyzeFieldDefs(file):
    global dfExtract
    '''
    Compares a datasets Field Definition Library to a Source Datafile 
    for that dataset and reports discrepancies
    '''
    fin = open(file,"r")
    info = json.load(fin)
    colsLib = set(info.keys())
    colsDat = set(dfExtract.columns)
    
    
    notInLib = colsDat - colsLib
    notInDat = colsLib - colsDat
    
    string="Analysis of Source Fields Library vs Source Data Fields\n\n\n"
    string+="Fields in LIBRARY not found in DATA\n"
    if len(notInDat) > 0:
        for field in notInDat:
            string+=f"{field}\n"
    else:
        string+="----\n"
    string+="\n\n"
    
    string+="Fields in LIBRARY not found in LIBRARY\n"
    if len(notInLib) > 0:
        for field in notInLib:
            string+=f"{field}\n"
    else:
        string+="----\n"
    string+="\n\n"
    
    sg.popup(string)

######################################################################

def createSrcTransFieldXrefScratch(w4x4):
    '''
    This function creates a Cross Reference List between the 
    Source Field List and Transform Field list for a dataset
    A form will be created and seeded with the Source Field list and 
    Descriptions found in the srcDefFile.  This will thne use the trans
    column listsing for the Transformed Fields to  guess a best match
    for each Source Field.  Users will then be able to fix the guesses 
    for the Transformed Fields.
    The Form allows users to create a new Transform Field if needed.
    The Form also allows for the creation of totally NEW Source and Transform
    listings    
    '''
    todayDate=f"{today.year}-{today.month}-{today.day}"    
    tmp = {}
# create a dictionary of the descripitons of the transform fields for easy lookup
## If there is a source definition file, use it to seed the defintion/descriptions
    
    col1 = []
    col2 = []
    col3 = []
    rows = []
    row=[]
    rowC=[]
    
 #   ["Source Field","Transformed Field","Description","Date","Notes"]
    rowC.append(sg.Text("Source Field",font='Courier 15 bold ',text_color="black",key="HC1",justification="center",size=(30,1))) 
    rowC.append(sg.Text("Transformed Field",font='Courier 15 bold ',text_color="black",key="HC2",justification="center",size=(30,1)))    
    rowC.append(sg.Text("Description",font='Courier 15 bold ',text_color="black",key="HC3",justification="center",size=(30,1)))    
    rowC.append(sg.Text("Notes",font='Courier 15 bold ',text_color="black",key="HC4",justification="center",size=(30,1)))    
    rowC.append(sg.Text("Change Date",font='Courier 15 bold ',text_color="black",key="HC5",justification="center",size=(15,1)))   

    #   frameCustHead = sg.Frame("",[row],key="FRAME:CUSTHEAD",visible=False)
    row.append(sg.Text("Change Date",font='Courier 15 bold ',text_color="black",justification="left",size=(15,1)))   
    row.append(sg.Text("Change Date",font='Courier 15 bold ',text_color="black",justification="left",size=(15,1)))   
    rows.append([sg.Frame("",[row],key="HEADER")])
    
    rowsC = []
    rowsC.append([sg.Frame("",[rowC],key="someFrame",visible=True)])

##  Add custom fields, make them invisible until needed, one by one    
    for nn in range(1,31):
          row=[]
         
          row.append(sg.Input("",
                                font='Courier 15 bold ',key=f"SOURCEC:CUST:{nn}",visible=True,
                         #       select_mode="LISTBOX_SELECT_MODE_SINGLE",visible=False,
                                size=(21,1),enable_events=False))
          row.append(sg.Input("",font='Courier 15 bold ',visible=True,key=f"TRANSC:CUST:{nn}",size=(31,1)))
          row.append(sg.Input("",font='Courier 15',size=(31,1),visible=True,key=f"DESCC:CUST:{nn}"))
          row.append(sg.Input("",font='Courier 15',size=(31,2),visible=True,key=f"NOTESC:CUST:{nn}"))
          row.append(sg.Input(todayDate,font='Courier 15 bold ',visible=True,size=(11,1),key=f"DATEC:CUST:{nn}"))
        
          rowsC.append([sg.Frame("",[row],visible = True,key=f"FRAME:CUST:{nn}")])

            
            
#     for nn in range(11,31):
#           row=[]
         
#           row.append(sg.Input("",
#                                 font='Courier 15 bold ',key=f"SOURCEC:CUST:{nn}",visible=True,
#                          #       select_mode="LISTBOX_SELECT_MODE_SINGLE",visible=False,
#                                 size=(21,1),enable_events=False))
#           row.append(sg.Input("",font='Courier 15 bold ',visible=True,key=f"TRANSC:CUST:{nn}",size=(31,1)))
#           row.append(sg.Input("",font='Courier 15',size=(31,1),visible=True,key=f"DESCC:CUST:{nn}"))
#           row.append(sg.Multiline("",font='Courier 15',size=(31,2),visible=True,key=f"NOTESC:CUST:{nn}"))
#           row.append(sg.Input(todayDate,font='Courier 15 bold ',visible=True,size=(11,1),key=f"DATEC:CUST:{nn}"))
        
#           rowsC.append([sg.Frame("",[row],visible = False,key=f"FRAME:CUST:{nn}")])            
            
            
  #  rows.append([sg.Frame("Custom Fields",[rowsC])])
        
    layout = [[sg.Button("Quit"),sg.Button("Add XREF Field",key="Add XREF Field SCR")],
               [sg.Button("Write XREF File")],
               [sg.Column(rowsC,visible=True,scrollable=True)]]
             
    sg.theme("LightBrown6")     
    window2 = sg.Window("Source-Transform XREF from Scratch",layout,finalize=True,resizable=True)
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
      
    return 

#########################################################################

def writeFieldFileN2(w4x4,title,values,targDir,datasetCharId):
    ''' Read the Form created for mapping Source Fields to Transformed Fields, 
        write out to a json file, called  w4x4_fields.json
        This checks all the fiels for proper mapping b/w source fields and 
        transformed fields
    '''
    global mapped
    mapped = {}
    mapped["info"] = {"4x4":w4x4,"Title":title}
    mapped["data"] = {}
    
    xrefs = {}
    notes = {}
    dates = {}
    hold = {}
    print("OH YEah... WRITING SOME XREFS")
## Get Values read from Field List Form, put them into a dictionary for output 
## as a JSON
    for key,val in values.items():
        
        if isinstance(key,str) and ":" in key:
       #     'LISTBOX:entityId': 'Entity Id', 0: 'Entity Id', 'NOTES:entityId':
            spl = key.split(":")
            val = val.strip()
            spl[1]=spl[1].strip()
            spl[0]=spl[0].strip()
            
            if spl[0] == "SOURCE":  
                if spl[1] != "CUST":
                    if spl[1] not in mapped[w4x4]:                        
                        mapped[w4x4][spl[1]] = {}  
            elif spl[0] == "LISTBOX":
                if spl[1] not in mapped[w4x4]:                        
                    mapped[w4x4][spl[1]] = {}  
                mapped['data'][spl[1]]["xref"] = val 
            elif spl[0] == "DESC":
                if spl[1] != "CUST":
                   if spl[1] not in mapped[w4x4]:                        
                        mapped['data'][spl[1]] = {}  
                   mapped['data'][spl[1]]["desc"] = val        
            elif spl[0] == "NOTES":
                if spl[1] != "CUST":
                    if spl[1] not in mapped[w4x4]:                        
                        mapped['data'][spl[1]] = {}  
                    mapped['data'][spl[1]]["notes"] = val 
            elif spl[0] == "DATE":
                if spl[1] != "CUST":
                    if spl[1] not in mapped[w4x4]:                        
                        mapped['data'][spl[1]] = {}  
                    mapped['data'][spl[1]]["date"] = val 
                    
            elif spl[1] == "CUST" and spl[0] in ["SOURCEC","TRANSC","DESCC","NOTESC","DATEC"] and len(val) > 0:
                nn = spl[2]
                if nn not in hold:
                    hold[nn] = {}
                hold[nn][spl[0]] = val

##  Add any custom Fields to mapped
    for k,v in hold.items():
    #    print("KK,VV ",k,v)
        if "SOURCEC" in v and len(v["SOURCEC"]) > 0 :
            mapped['data'][v["SOURCEC"]] = {}
            mapped['data'][v["SOURCEC"]]["xref"]=v["TRANSC"]
            if "NOTESC" in v:
                mapped['data'][v["SOURCEC"]]["notes"]=v["NOTESC"]
            else:
                mapped['data'][v["SOURCEC"]]["notes"]=""
            
            if "DESCC" in v:
                mapped['data'][v["SOURCEC"]]["desc"]=v["DESCC"]
            else:
                mapped['data'][v["SOURCEC"]]["desc"]=""
                
            mapped['data'][v["SOURCEC"]]["date"]=v["DATEC"]
                       
    try: 
##  Check mapped fields for duplicates
        statsT2O = {}
        statsO = {}
        oFCount=0
        tFCount=0
        stringMap = ""
        stringBad = ""
        print("checking mapped data")
#        for  w4x4,dct in mapped.items():
        dct=mapped["data"]
        for oF,info in dct.items():
                tF = info['xref']
                if tF not in statsT2O:
                    statsT2O[tF] = []
                statsT2O[tF].append(oF)
                if oF not in statsO:
                    statsO[oF] = 0
                statsO[oF]+=1
        print("Checking Transformed fields")
    ## Check that Transformed Fields are only being referenced by 1 Original Field            
        for tF,xrfs in statsT2O.items():
            if len(xrfs) > 1:
                print(f"{tF} too many X-Refs")
                for val in xrfs:
                    stringBad+= f" {tF} -> {val}\n"
                stringBad+=f"\n"
            elif tF == "NONE":
                    stringBad+="Transformed Fields is set to NONE... Please set a Legitimate X-ref\n"
                    stringBad+=f"  {tF} -> {xrfs[0]}\n\n"
            else:
                stringMap+= f" {xrfs[0]} -> {tF}\n"
                tFCount+=1

        for oF,count in statsO.items():
            if count > 1:
                print(f"Roh-Roh... Mulitple listings for {oF}   Found {count} times")
            else:
                oFCount+=1
    ##  Used to close tkinter window               
        def close():
            popup.destroy()
            popup.quit()


        if len(stringBad) == 0:
            print("GOOD GOOD GOOD")
            stringAll = f"Dataset {w4x4}\n Source Fields {oFCount}\nTransformed Fields {tFCount}\n\n\n"
            stringAll+=stringMap
            tkPopScrollSimple(stringAll)
   #         sg.popup(stringAll)
        else:
            stringAll = "Errors were Found... file will NOT be written\n\n"
            stringAll+= "Please FIX ERRORS , then retry writing the file\n\n"
            stringAll+= "Transformed Field xrefed to Multiple Source Fields and/or Transformed Fields are set to NONE\n\n"
            stringAll+= " Transformed Field  ->  Source Field\n\n"
            stringAll+= stringBad
            print("BAD BAD BAD",stringAll)
            popup = tk.Tk()
            popup.wm_title("Field List Error")
            label = Label(popup, text=stringAll,font=('Courier',20),justify="left", relief="groove")
            label.configure(bg="pink")
            label.pack(side="top", fill="x", pady=10)
            # B1 = ttk.Button(popup, text="Okay", command = popup.destroy)
            # B1.pack()
            my_button= Button(popup, text= "OK", font=('Courier',25),
            borderwidth=2, command= close)
            my_button.pack(pady=20)
            popup.mainloop()
            return

        outFile = os.path.join(targDir,f"{w4x4}_src_trns_xrefs.json")
        print("WRITING XREF FIELDS TO ",outFile)
        with open(outFile,"w") as jfile:
            jfile.write(json.dumps(mapped))
    except Exception as err:
         exceptionLog(err,inspect.currentframe().f_code.co_name)

#########################################################################
xrefsBy4x4,xrefsByTitle,fields = getXrefs()


# ## Functions 2

# In[3]:


## compareWindow -> ExtractAnal   -> TABLEFILE-Click(showDFUNwindow) -> TABLE-CLICK (showDFRecswindow)
#                 TransformAnal
#
## sourceDefs2Fields -> writeSoureFieldList -> tkPopScroll -> toFile
#
#
## createSrcTransFieldXref -> writeFieldFileN -> 
#############################################################   

def sourceDefs2Fields(dfile,fields): 
    '''Reads a csv with the definition listings,and gets the fields listings from
       the Extract process, and creates a form for creating a Source Field list to Source
       Definition file
    '''
    global mapping
    dfF = pd.read_csv(dfile,delimiter="\t")
    defs = dfF["Description"].values.tolist()
    string=f"Dictionary Defination File: {dfile}\n"
    string += f"{dfF.shape[0]} Fields in Dictionary File\n{len(fields)} Fields from Source DATA File"
    rows = []
    fieldsTmp = fields.copy()
    tmpD2F = {}
    mapping = {}
    for col in defs:
        cc = getMostLike(col,fields)
        tmpD2F[col]=cc
    
    for nn,col in enumerate(defs):
        row=[]
        fieldsTmp = reorderList(tmpD2F[col],sorted(fieldsTmp))
        row.append(sg.Combo(fieldsTmp,default_value=tmpD2F[col],enable_events=True,  
                            font='Courier 15 bold ',key=f"DEFS::{col}",
                     #       select_mode="LISTBOX_SELECT_MODE_SINGLE",
                            size=(30,6)))
        row.append(sg.Text(col,font='Courier 15',key=f"{col}",size=(30,3)))
        rows.append([sg.Frame("",[row])])
        
    layout = [[sg.Text(string,font='Courier 15')],
              [sg.Button("Quit")],
              [sg.Button("Source Analysis",key="-EXTRACTANAL-",font='Courier 15')],
              [sg.Button("Write Source Defs",font='Courier 15',tooltip="File will be written to the Datsets bic_etl directory under defs/file_name, where file_name is is created from datasets run_etl.json info")],
              [sg.Column(rows,scrollable=True)]
             ]
  
    sg.theme("LightBrown4")     
    window2 = sg.Window("Input Source Definitions",layout,finalize=True,resizable=True)
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)

##########################################################

def compare2Data(df,xrefs):
    global dcols,pcols,rowColors,values,dnotpLines
    dcols = list(df.columns)
    pcols = list(xrefs.keys())
    
    wid = windowsStore["columnAnalysis"]
    rowColors = wid["-TABLECOLUMN-"].metadata[1]
    values = wid["-TABLECOLUMN-"].metadata[0]
   
    colr1 = rowColors[0][1]
    colr2 = rowColors[1][1]
    
    pnotd = []
    dnotp = []
    dnotpLines = {}

    for col in pcols:
        if col not in dcols:
            pnotd.append(col)

    for col in dcols:
        if col not in pcols:
            dnotp.append(col)
            for line in transformProgram:
                if line.find(col) > -1:
                   if col in dnotpLines:
                     dnotpLines[col].append(line)
                   else:
                     dnotpLines[col] = []
                     dnotpLines[col].append(line)
                                 
    for nn,value in enumerate(values):    
        if nn%2 == 0:
            rowColor= colr1
        else:
            rowColor= colr2

        col = value[0]

        if col in pnotd:
            rowColor = "pink"

        colr = (nn,rowColor)
        rowColors.append(colr)

        
    sp = "\n".join(pnotd)
    sd = "\n".join(dnotp)
    
        
    wid["-TABLECOLUMN-"].update(row_colors=rowColors)  
    wid["-PNOTD-"].update(pnotd)    
    wid["-DNOTP-"].update(dnotp)    
    
    
##########################################################

def compareWindow(parentWindow,stats1,df1,file1,title="Compare",colorTheme="'Dark Green 5'"):
    global color1,color2,compWindow
    header_list = ["Column","% Missing","Missing","string","integer","float","boolean"]
  
    col_widths = [8]*len(header_list)
    col_widths[0] = 25
    columnSortStateTable1 = {}
  

    ## set up sort state for the column in both tables
    for col in header_list:
         columnSortStateTable1[col] = -1
       
            
    valsFile1 = getValues(stats1,header_list)
   
    
    rowFile1Colors = setRowColors(valsFile1,color1,color2,"pink",header_list)
    
    layCol1 = [[sg.Text(f"File 1 {file1}",font="CENTAUR 15")],[sg.Text(f"File 1 Shape {df1.shape}",font="CENTAUR 15")],
               [sg.Button("Output Columns"),sg.Button("Output Text Table"),sg.Button("Output CSV File")],
               [sg.Table(values=valsFile1,text_color="black", auto_size_columns=False,enable_events=True,num_rows=20,col_widths=col_widths,font="CENTAUR 10",
                   justification='center',pad=(5,5),vertical_scroll_only=False,
                   key='-TABLEFILE-',row_colors=rowFile1Colors,headings = header_list,metadata=columnSortStateTable1)]
               ]
    

    layout = [[sg.Button("Quit")],
    layCol1]  
              
    sg.theme(colorTheme)     
    window2 = sg.Window(title,layout,finalize=True,resizable=True,metadata=[colorTheme,df1,title,valsFile1,header_list,file1])
    if parentWindow not in windowsReset:
        windowsReset[parentWindow] = {}
    if window2 not in  windowsReset[parentWindow]:
         windowsReset[parentWindow][window2] = {}
    compWindo = window2
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
    tableFile1 = window2['-TABLEFILE-']
    tableFile1.bind('<Button-1>', "Click")
    headerStore[tableFile1] = header_list
    statsStore[tableFile1] = stats1
#    print("STATS ",stats1)
    return window2,tableFile1,valsFile1,rowFile1Colors

#############################################

def dfAnalyze(df):
    stats = {}
    
    for col in df.columns:
        typs = df[col].apply(type).value_counts().to_dict()
        stats[col] = {}
        if str in typs:
           stats[col]["string"] = typs[str]
        else:
           stats[col]["string"] = 0

        if int in typs:
           stats[col]["integer"] = typs[int]
        else:
           stats[col]["integer"] = 0

        if float in typs:
           stats[col]["float"] = typs[float]
        else:
           stats[col]["float"] = 0

        if bool in typs:
           stats[col]["boolean"] = typs[bool]
        else:
           stats[col]["boolean"] = 0

        stats[col]["Missing"] = df[col].isna().sum()
        stats[col]["% Missing"] = round(df[col].isna().sum()/df.shape[0]*100,1)
        
    return stats

############################################# 

def exceptionLog(exception,funCall):
  exception_message = str(exception)
  exception_type, exception_object, exception_traceback = sys.exc_info()
  filename = os.path.split(exception_traceback.tb_frame.f_code.co_filename)[1]
  print(f"{exception_message} {exception_type} {funCall}, Line {exception_traceback.tb_lineno}")

###############################################################

def fullDataColumnMap(cim4x4):
    '''Map the data fields found in the source data file to all the other sources  '''
    global missed
    if cim4x4 in fields:
        invc = fields[cim4x4]["source"].copy()
    else:
        invc = []
    tfc = transformColumns.copy()
    exc = extractColumns.copy()
    excMissed = []
    tfcsij = transformSijColumns.copy()
    loadsij = loadSijColumns.copy()
    cim = cimColumns.copy()
    xrfo2t = xrefsO2T.copy()
    names = []
    columnDict = {}
    names.append("BIC Inventory")
    names.append("Transform Program")

    names.append("Transform - Data")
    names.append("CIM - Data")
    names.append("Transform - SIJ")
    names.append("Load - SIJ")

    for k in exc:
       # print("MAP ",k)
    #for k,v in xrefsO2T.items():
        columnDict[k] = []
        nhit=0
        v=""
        if k in invc:
            v=k
            vv=k
            invc.remove(k)
            nhit+=1
        else:
            vv=""
        columnDict[k].append(vv)
        
        if k in xrfo2t:
            v = xrfo2t[k]
            vv=v
            del xrfo2t[k]
            nhit+=1
        else:
            vv = ""
        columnDict[k].append(vv)  

   
        if v in tfc:
           tfc.remove(v)
           cc = v
           nhit+=1
        else:
            cc=""
        columnDict[k].append(cc)


        if v in cim:
           cim.remove(v)
           cc = v
           nhit+=1            
        else:
            cc=""
        columnDict[k].append(cc)



        if v.lower() in tfcsij:
           tfcsij.remove(v.lower())
           cc = v.lower()
           nhit+=1            
        else:
            cc=""
        columnDict[k].append(cc)

        if v.lower() in loadsij:
           loadsij.remove(v.lower())
           cc = v.lower()
           nhit+=1
        else:
            cc=""
        columnDict[k].append(cc)
        
        if nhit == 0:
            excMissed.append(k)
        

    a = pd.DataFrame(columnDict).T
    a.columns = names
    a.reset_index(inplace=True)
    values = a.values.tolist()
    cols = list(a.columns)
   
    missed = {}
    missed["Extract - Data"] = excMissed
    missed["BIC Inventory"] = invc
    missed["Transform Program"] = list(xrfo2t.keys())
    missed["Transform - Data"] = tfc
    missed["CIM - Data"] = cim
    missed["Transform - SIJ"] = tfcsij
    missed["Load - SIJ"] = loadsij
    
    
 #   missed = [invc,list(xrfo2t.keys()),tfc,cim,tfcsij,loadsij]
    return cols,values,missed
        

###############################################################
def getFilesClicked(file,window):
#         if len(values["-FILE1-"]) > 0:
#             file = values["-FILE1-"]
#         elif len(values["-WEB1-"]) > 0:
#             file = values["-WEB1-"]
      
        df = getFile("Local",file,window)
        stats = dfAnalyze(df)

        return df,stats

####################################################################
       
def getFile(how,file,WindowP):
    print("Getting file ",file,how)
    if how == "Local":
        if file[-3:].lower() == "tsv":
            delim = "\t"
            df=pd.read_csv(file,encoding="latin",delimiter=delim)
        elif file[-4:].lower() == "xlsx":
            df=pd.read_excel(file,engine="openpyxl")
        else:
            try:
                df=pd.read_csv(file)
            except Exception as err:
                print("Error, trying with encoding=latin")
                df=pd.read_csv(file,encoding="latin")
    elif how == "Fetch":
      
  #      file=values["-WEB-"]
      #  getPrevFiles(2,file)

  #      windowP["-PINFO-"].update(f"START reading WEB File:{file}:")
        df=pd.read_csv(file)
      
  #      windowP["-PINFO-"].update(f"FINISHED reading WEB File:{file}:")
   
    stats = dfAnalyze(df)
        
    return df,stats

############################################################

def getRowClicked(table,columns):
    col=""
    print("RC TABLE ",table)
    e = table.user_bind_event 
    print("e ",e)
    region = table.Widget.identify('region', e.x, e.y)
    print("region ",region)
    if region == 'heading':
        row = 0
    elif region == 'cell':
        row = int(table.Widget.identify_row(e.y))  
        col = columns[row-1][0]
    print("R,C ",row,col)
    return row,col    

#####################################################################

def getRowClickedUN(table):
    val=""
    data = dataStore[table]
    e = table.user_bind_event 
    region = table.Widget.identify('region', e.x, e.y)
    if region == 'heading':
        row = 0
    elif region == 'cell':
        row = int(table.Widget.identify_row(e.y))  
        val = data[row-1][0]
      #  print("Un VAL CLICKED ",val)
    return row,val    

##########################################################

def getSijColumns(file):
    '''Get the fields for both teh contrile file content and the ftp control file content '''
    global transformSijColumns,loadSijColumns
    with open("/home/joe/bic_etl/cdos/business/nonprofit/scripts/datasync/char_paid_solicitors.sij") as fin:
        lines = fin.readlines()
        line = lines[0]
        ss = json.loads(line)
        cfc = json.loads(ss["controlFileContent"])
        transformSijColumns = cfc["csv"]["columns"]
        ftp = json.loads(ss["ftpControlFileContent"])
        loadSijColumns = ftp['csv']['columns']

#         for col in transformColumns:
#             if col in loadColumns:
#                 hit+=1
#             else:
#                 miss+=1

#         for col in loadColumns:
#             if col in transformColumns:
#                 hit+=1
#             else:
#                 miss+=1

# ##########################################################

def getValues(stats,header):

    statsVals=[]
    for col in sorted(stats.keys()):
         vals=[]
         vals.append(col)
         for k in header[1:]:
            vals.append(stats[col][k.strip()])
         statsVals.append(vals)
    return statsVals     

##############################################################

# def getXrefs():
#     '''Reads the Inventory google sheet and gets the datasets title and cross-refs it to the Socrata 4x4 id.  Also
#     gets the fields by 4x4 dataset id and by the title'''
#     scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
#              "https://www.googleapis.com/auth/drive.file",
#                   "https://www.googleapis.com/auth/drive"]

#     creds = ServiceAccountCredentials.from_json_keyfile_name('../client_secret.json',
#      scope)
#     client = gspread.authorize(creds)

#     gc = gspread.service_account("../client_secret.json")
#     # for gg in gc.list_spreadsheet_files():
#     #      print("GGGGG ",gg)
#     # https://docs.google.com/spreadsheets/d/1WTaOglzbSsYiHhAGguGxHQXmAGmOhfFHkGkMLowxAOA/edit?usp=sharing
#     sheet = client.open('BIC Data Inventory and Metadata').worksheet(
#         'Maintenance_Framework')
#     repo_sheet = client.open('BIC Data Inventory and Metadata').worksheet(
#         'MetadataRepository')
#     fields_sheet = client.open('BIC Data Inventory and Metadata').worksheet(
#         'Field Descriptions')
    
    
# #     sheet = client.open('https://docs.google.com/spreadsheets/d/1Xc7oYpdCLwHmUCaokpfXkF4bzkwRW0xUbvBZwruF0ZI/').worksheet(
# #         'Maintenance_Framework')
# #     repo_sheet = client.open('https://docs.google.com/spreadsheets/d/1Xc7oYpdCLwHmUCaokpfXkF4bzkwRW0xUbvBZwruF0ZI/').worksheet(
# #         'MetadataRepository')
    
# #     fields_sheet = client.open('https://docs.google.com/spreadsheets/d/1Xc7oYpdCLwHmUCaokpfXkF4bzkwRW0xUbvBZwruF0ZI/').worksheet(
# #         'Field Descriptions')

#     dfRepo = pd.DataFrame(repo_sheet.get_all_records(head=3))
#     xrefsBy4x4 = {}
#     xrefsByTitle = {}

#     for index,row in dfRepo[['Dataset Title','Socrata Link']].iterrows():
#         xrefsByTitle[row['Dataset Title']] = row['Socrata Link']
#         xrefsBy4x4[row['Socrata Link']] = row['Dataset Title']
        
#     dfFields = pd.DataFrame(fields_sheet.get_all_records(head=1))
#     fields = {}
#     for index,row in dfFields.iterrows():
#         s4x4 = row["Socrata ID"]
#         of = row["Source Field Name"]
#         tf = row["Full Field Name"]
#         af = row["API Field Name"]
#         if s4x4 in fields:
#             fields[s4x4]["source"].append(of)
#             fields[s4x4]["cim"].append(tf)
#             fields[s4x4]["api"].append(af)
#         else:
#             fields[s4x4] = {}
#             fields[s4x4]["source"] = []
#             fields[s4x4]["cim"] = []
#             fields[s4x4]["api"] = []
            
#             fields[s4x4]["source"].append(of)
#             fields[s4x4]["cim"].append(tf)
#             fields[s4x4]["api"].append(af)
        
        
        
#     return xrefsBy4x4,xrefsByTitle,fields

#############################################

def go_deeper(aDict,value,nit):
    nit+=1
    for k, v in aDict.items():
         if not bool(v):            
             aDict[k] = []
             aDict[k].append(value)
         elif isinstance(v,list):
             aDict[k].append(value)
         else:
             go_deeper(v,value,nit)
   
    return aDict

###################################################    

def init():
    global dataSetsEtl,datasets,groupMenu
    groups = []
    desktop = pathlib.Path("/home/joe/bic_etl")
    runEtls = []
    dataSets = []
    info = {}
    # .rglob() produces a generator too
    desktop.rglob("*")
    files = list(desktop.rglob("*"))
# Which you can wrap in a list() constructor to materialize
    for ff in files:

            if (str(ff).split("/")[-1] == "run_etl.json"):     
                a=str(ff).split("/")
                m = a.index("bic_etl")
                b = a[m+1:-1]
                ll = splitL(b)
                groups.append(ll)
                runEtls.append(ff)
            
 #   print(f"{len(runEtls)} run_etl.json files found")    
    
    dataSets = []
    groups = []
    for file in runEtls:
      f = open(file,"r")
      data = json.load(f)
      # print(file)
      # print("----")
      a=str(file).split("/")
      m = a.index("bic_etl")
      b = a[m+1:-1]
      group = b[0]
      ll = splitL(b)
      bdir = "/".join(b)  
    
      
    #  groups.append(ll)
      for val in data:
            if "title" in val:
                  title=val["title"]
                  if title in mapTitles:
                     title = mapTitles[title]
                  info[title]={}
                  info[title]["directory"] = bdir
                  info[title]["group"] = group
                
    #              print(title,ll)
                  nit=0
                  ll = go_deeper(ll,title,nit)
             #     info[title]["groups"] = ll
            
     #             print(ll)
     #             groups.append(ll)
            dataSets.append(val)
    #  print("FF ",ll) 
      groups.append(ll)

    datasets = []
    dataSetsEtl={}
    for val in dataSets:
        if "title" in val:
          datasets.append(val["title"])
          title=val["title"]
          if title in mapTitles:
            title = mapTitles[title]
          dataSetsEtl[title] = {}  
          dataSetsEtl[title]["info"] = {}
          dataSetsEtl[title]["info"]["directory"] = info[title]["directory"]
          dataSetsEtl[title]["info"]["group"] = info[title]["group"]
     #     dataSetsEtl[title]["info"]["groups"] = info[title]["groups"]
            
        
            
          for k,v in val.items():
          #      print(k,v)
                if k != "title":
                    dataSetsEtl[title][k] = {}
                    if isinstance(v,dict):
                        for k1,v1 in v.items():
                            dataSetsEtl[title][k][k1]=v1
                            
                            
                            
    groupMenu = ['Groups',
     ['boulder',
      ['Restaurant Inspections in Boulder Colorado'],
      'catalog',
      ['CIM Catalog Download'],
      'cdhe',
      ['Enrollment Demographics for Post-Secondary Graduates in Colorado',
       'Post-Secondary Financial Aid Demographics in Colorado'],
      'cdor',[
      'revenue_marijuana',
      ['Marijuana Sales by County in Colorado',
       'State Retail Marijuana Sales Tax Revenue by County in Colorado',
       'Marijuana Tax and Fee Revenue in Colorado',
       'Marijuana Sales Revenue in Colorado'],
      'retail_reports',
      ['Retail Sales Tax Return History in Colorado',
       'Retail Reports by City in Colorado',
       'Retail Reports by County in Colorado',
       'Retail Reports by Industry and City in Colorado',
       'Retail Reports by Industry and County in Colorado',
       'Retail Reports by Industry in Colorado'],
      'regulations_liquor',
      ['Liquor Permits for Special Events in Colorado',
       'Liquor Compliance Check Statistics in Colorado',
       'Liquor Licenses in Colorado',
       'Recently Approved Liquor Licenses in Colorado',
       'Recently Expired and Surrendered Liquor Licenses in Colorado',
       'Sales Rooms in Colorado',
       'Manufacturer Temporary Sales Room Permits in Colorado']
      ],
      'cdos',[
      'health',
      ['Durable Medical Equipment Suppliers in Colorado'],
      'government',
      ['Current Notaries in Colorado'],
      'business',[
      'ucc',
      ['Uniform Commercial Code (UCC) Collateral Information in Colorado',
       'Uniform Commercial Code (UCC) Debtor Information in Colorado',
       'Uniform Commercial Code (UCC) Filing Information in Colorado',
       'Secured Party Information in Colorado'],
      'business',
      ['Business Entities in Colorado',
       'Business Entity Transaction History',
       'Trademarks for Businesses in Colorado',
       'Trade Names for Businesses in Colorado',
       'Master List in Colorado'],
      'nonprofit',
      ['Federal Tax-Exempt Subsection Codes in Colorado',
       'Registration for Charities, Paid Solicitors, Professional Fundraising Consultants, and for-profit Public Benefit Corporations in Colorado',
       'Charitable Organizations’ Offices in Colorado',
       'Other State Solicitation of Charities’ Registrants in Colorado',
       'Charitable Purpose of the Charity in Colorado',
       'Paid Solicitor Solicitation Notices in Colorado',
       'Campaign Reports for Solicitation Notices to Charities in Colorado',
       'Solicitation Campaign Supervisors Listed on Solicitation Notices in Colorado',
       'Charity Extension Requests',
       'Persons Associated with Charitable Organizations, Paid Solicitors, and Professional Fundraising Consultants in Colorado',
       'Other Names a Registered Entity Uses to Solicit Contributions',
       'Paid Solicitors Disclosed on Charity Registration Forms in Colorado',
       'Charitable Solicitation Call Center Locations in Colorado',
       'Charities Solicitation Type by Solicitation in Colorado',
       'Communication Methods Used in Solicitation Campaigns in Colorado']
      ],
      'lobbyist',
      ['Directory of Lobbyists in Colorado',
       'Directory of Lobbyist Clients in Colorado',
       'Expenses for Lobbyists in Colorado',
       'Characterization of Lobbyist Clients in Colorado',
       'Subcontractors for Lobbyists in Colorado',
       'Bill Information and Position with Income of Lobbyist in Colorado']
      ],
      'cdot',[
      'transportation_road_attributes',
      ['Highway Milepoints in Colorado',
       'Highway Mileposts in Colorado',
       'Highway Routes in Colorado',
       'Highway Routes in Colorado',
       'Local Roads in Colorado',
       'Major Roads in Colorado',
       'Scenic Byways in Colorado'],
      'tops',
      ['CDOT Expenses', 'CDOT Revenues', 'CDOT Payroll'],
      'natural_resources',
      ['Lakes in Colorado', 'Streams in Colorado'],
      'transportation_infrastructure',
      ['Airports in Colorado',
       'Cities in Colorado',
       'Counties in Colorado',
       'Railroads in Colorado']
      ],
      'ceo',[
      'useia',
      ['Gasoline Prices in Colorado', 'Natural Gas Prices in Colorado']
      ],
      'denver',
      ['Temporary Outdoor Expansions for Restaurants in Denver, Colorado'],
      'dola',[
      'special_districts',
      ['Metro Districts in Colorado',
       'Parks and Rec Districts in Colorado',
       'Fire Districts in Colorado',
       'Hospital Districts in Colorado',
       'Water and Sanitation Districts in Colorado',
       'Library Districts in Colorado',
       'School Districts in Colorado',
       'Soil Districts in Colorado',
       'Cemetery Districts in Colorado',
       'All Special Districts in Colorado'],
      'boundaries',
      ['Municipal Annexations in Colorado', 'Municipal Boundaries in Colorado'],
      'demographics',
      ['Population Projections in Colorado',
       'Race Estimates in Colorado',
       'Race Forecast in Colorado']
      ],
      'dora',[
      'regulations',
      ['Licensed Real Estate Professionals in Colorado',
       'Professional and Occupational Licenses in Colorado']
      ],
      'dpa',
      ['DPA Tops Data'],
      'irs',
      ['Purpose and Operational Size of Charities Operating in Colorado',
       'Fundraising Revenue of Charities Operating in Colorado',
       'Total Revenue of Charities Operating in Colorado',
       'IRS Filing Information for Charities Operating in Colorado',
       'Total Revenue and Types of Art for Charities Operating in Colorado',
       'Conservation Easements for Charities Operating in Colorado',
       'Activities of Charities Operating in Colorado',
       'Expenses of Charities Operating in Colorado',
       'Expenses of Charities Operating in Colorado'],
      'tchd',
      ['Restaurant Inspections in Tri-County Colorado']]]

    return sorted(datasets)

######################################################################

def map4x4(row):
    
    if isinstance(row["Data Link"],str) and  len(row["Data Link"]) == 9 and re.findall( "\w{4}-\w{4}",row["Data Link"]):
  #      link = '<a href="https://data.colorado.gov/dataset/{}">{}</a>'.format(row["Data Link"],row["Data Link"])
        
        link = 'https://data.colorado.gov/dataset/{}'.format(row["Data Link"])
    else:
        link = ""
        
    return link
    
#####################################################################

def runETL(k):
    global extract,a,string,dataSetsEtl
    text2 = ""
 
    directory = ""
    group = ""
 #   print("dse ",sorted(list(dataSetsEtl.keys())))
    # for key in dataSetsEtl.keys():
    #     print(f"{len(key)}:{key}:")
        
    if "info" in dataSetsEtl[k]:
        if "directory" in dataSetsEtl[k]["info"]:
            directory = dataSetsEtl[k]["info"]["directory"]
            group = dataSetsEtl[k]["info"]["group"]
            print("D G",directory,group)
            
   
## Build Summary Text string
    for ky1 in dataSetsEtl[k].keys():
        text2+=f"{ky1}:\n" 
        for k2,v2 in dataSetsEtl[k][ky1].items(): 
            sl = 10 - len(k2)
            s = " "*sl
        
            if isinstance(v2,list) == False:
                text2+=f"    {k2:10s}{s} :  {v2}\n"
            else:
                text2+=f"    {k2:10s}{s} : {v2[0]}\n"
                if len(v2) > 1:
                    for val in v2[1:]:
                        text2+= f"                   {s} : {val}\n"
        text2+=f"\n\n"
## Build actions
    extract = ""
    datasetCharId=""
    if logging > 1:
        print(dataSetsEtl[ds])
    if 'extract' in dataSetsEtl[ds]:
      #  if isinstance(dataSetsEtl[ds]["extract"],"dict"):
           
            if ('language' in dataSetsEtl[ds]['extract'] and dataSetsEtl[ds]['extract']['language'] == 'node'):
                pgm =  dataSetsEtl[ds]['extract']['file']
                options=""
                print("Extract Level 2")

                if 'options' in dataSetsEtl[ds]['extract']:
                    for opts in dataSetsEtl[ds]['extract']['options']:
                        options+= f" {opts}" 
                        if opts[0:2] == "-f":
                            spl = opts.split("/")
                            spl = spl[1].split(".")
                            datasetCharId = spl[0]
                            print("DATASETCHARID 2",datasetCharId)
                extract = f"node {bicHome}{pgm} {options}"
                if logging > 0:
                    print("Extract ",extract)
    transform=""
    filetr = ""
    print("Get Transform")
    
    if 'transform' in dataSetsEtl[ds]:
        
        if dataSetsEtl[ds]["transform"]["language"] == "node":
             ff=dataSetsEtl[ds]["transform"]["file"]
             transform=f"node {bicHome}{directory}/{ff}"
        elif dataSetsEtl[ds]["transform"]["language"] == "py":
             ff=dataSetsEtl[ds]["transform"]["file"]
             transform=f"PIPENV_PIPFILE=/home/joe/bic_etl/cdor/regulations_liquor/scripts/Pipfile pipenv run python {bicHome}{directory}/{ff}"
     #   filetr=ff    
        options=""
        if 'options' in dataSetsEtl[ds]['transform']:
            for opts in dataSetsEtl[ds]['transform']['options']:
                options+= f" {opts}" 
                if isinstance(opts,str):
                    spl = opts.split(" ")
                    if "-i" in spl[0]:
                        filetr=spl[1]
                        if filetr[-4:] == "xlsx":
                            filetr=filetr.replace(".xlsx",".csv")
                        elif filetr[-3:] == "xls":
                            filetr=filetr.replace(".xls",".csv")
                        print("FFOUT ",filetr)
             #   print("TR OPTIONS",opts)
            transform+= f" {options}"
            
        else:
            filetr=""  
        if logging > 0:
            print("Transform: ",transform)
        
    text2+=f"\n\nActions Strings\nExtract\n{extract}\n\nTransform\n{transform}"
    if len(datasetCharId) == 0:
        datasetCharId = "na"
    return text2,extract,transform,filetr,directory,datasetCharId
    
#############################################

def setRowColors(lst,col1,col2,colsp,header):
    count=0
    colors = {}
    # print("SRC head ",header)
    # print("SRC list",lst)

    nrec = header.index("% Missing")
    for vals in lst:
        key = vals[0]
        if count%2 == 0:
            colors[key] = col1
        else:
            colors[key] = col2
        if vals[nrec] > 99.0:
           
            colors[key] = colsp
        count+=1
    colTab = []
    for key,colr in colors.items():
        colTab.append(colr)
    rowNums = [num for num in range(0,len(colTab)+1)]
    colText = ["black"]*len(colTab)
    colrw = list(zip(rowNums,colTab))
  
    return colrw

##########################################################

def setRowColorsGeneric(lst,col1,col2):
    count=0
    rowNums=[]
    colTab=[]

    for vals in lst:       
        if count%2 == 0:
            colTab.append(col1)
        else:
            colTab.append(col2)
        rowNums.append(count)
        count+=1
    colrw = list(zip(rowNums,colTab))
  
    return colrw

###########################################################

def showDfRecs(df1,colUn,val,windowP,title="DF Unique Record Values"):
    global color1,color2,showDFRecswindow
    header_list = list(df1.columns)
  
    col_widths = [8]*len(header_list)
 #   col_widths[0] = 25
    columnSortStateTable1 = {}
  

    ## set up sort state for the column in both tables
    for col in header_list:
        columnSortStateTable1[col] = -1
       
            
#    valsFile1 = getValues(stats1,header_list)
    values = df1.values.tolist()
    
    rowFile1Colors = setRowColorsGeneric(values,color1,color2)
    
    layout = [[sg.Text(f"Column: ",font="CENTAUR 10"),
               sg.Text(f"{colUn}",font="CENTAUR 15")],
              [sg.Text(f"Unique Value: ",font="CENTAUR 10"),
               sg.Text(f"{val}",font="CENTAUR 15")],
               [sg.Button("Quit")],
               [sg.Table(values=values,text_color="black", auto_size_columns=False,enable_events=True,num_rows=20,col_widths=col_widths,font="CENTAUR 10",
                   justification='center',pad=(5,5),vertical_scroll_only=False,
                   key='-TABLEFILE-',row_colors=rowFile1Colors,headings = header_list,metadata=columnSortStateTable1)]
               ]

    colorTheme = windowP.metadata[0]          
#    sg.theme(colorTheme)     
    window2 = sg.Window(title,layout,finalize=True,resizable=True,metadata=[colorTheme,df1])
    showDFRecswindow=window2
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
    tableFile1 = window2['-TABLEFILE-']
    tableFile1.bind('<Button-1>', "Click")
    headerStore[tableFile1] = header_list
    return window2,tableFile1,values,rowFile1Colors

###################################################

def splitL(data):
    if data:
        head, *tail = data  # This is a nicer way of doing head, tail = data[0], data[1:]
        return {head: splitL(tail)}
    else:
        return []

#############################################

def stringArgs(string):
#  This is set to decode the extract string to get the location and name of the 
#  extracted data file
 #   print("stringArg",string)
    h =split(string)
 #   print("HHH ",h)
    inf = h.index("-f")
    inf = h[inf+1]
    if "-a" in h:
        ot = h.index("-a")
        inf=inf.replace(inf[-4:],h[ot+1])
        of = inf.split("/")  
        of=of[-1]
    elif "-n" in h:
        of = h.index("-n")
        of=h[of+1]
        
    if "-u" in h:
        uf = h.index("-u")
        uf = h[uf+1]
        of=inf
        
#    ot = h[ot+1]
    if "-o" in h:
        od = h.index("-o")
        od = h[od+1]
    else:
        od=""

    finalFile = f"{bicHome}{od}{of}"
    print("finalFile ",finalFile)
    return finalFile

######################################################    

def sortTable(row,stats,table,event,header):
    
        e = table.user_bind_event 
        region = table.Widget.identify('region', e.x, e.y)
        if region == 'heading':
            row = 0
        elif region == 'cell':
            row = int(table.Widget.identify_row(e.y))
   
        if row == 0:
            colSortState = table.metadata
            colClicked = int(table.Widget.identify_column(e.x)[1:])
            header = headerStore[table]
            
            statClicked = header[colClicked-1].strip()
           
            colSortState[statClicked]*=-1
            if colSortState[statClicked] == -1:
                sortAsc=False
            else:
                sortAsc=True
            if colClicked > 1:  # user number sort
                statsS = dict(sorted(stats.items(), key=lambda x: x[1][statClicked],reverse=sortAsc))
            else:
                statsS = dict(sorted(stats.items(), key=lambda x: x[0],reverse=sortAsc))


            statsVals=[]
            for col in statsS:
                 vals=[]
                 vals.append(col)
                 for k in header[1:]:
                    vals.append(statsS[col][k.strip()])
                 statsVals.append(vals)
           # slen= len(statsVals)
#             colorsTable = setRowColors(statsVals,"#b3f0ff","#33d6ff","pink",header_list)

#             window['-TABLE-'].update(values=statsVals,row_colors=colorsTable)
        
        return statsVals,colSortState


####################################################################

def showDFUN(col,unq,windowParent,colr1,colr2,colorTheme,title=""):
    global dataStore,showDFUNwindow
    valuesUNQ = list(zip(unq.index.tolist(),unq.tolist()))
    hUNQ = []
    hUNQ.append("Values")
    hUNQ.append("Count")

    
    sortState = {}
    for val in hUNQ:
        sortState[val]=-1
    layout2 = [    
                   [sg.Text(f"Showing unique Values for Column"),sg.Text(f" {col}",text_color="white",font='Courier 15 bold '),sg.Text(f" and Reg Ex",text_color="white",font='Courier 10 bold ')],
                
                   [sg.Button('Quit')],
            
                   [sg.Button('Write Unique'),
                    sg.Table(values=valuesUNQ,
                       background_color=colr1,vertical_scroll_only=False,col_widths=60,font='Courier 10 bold ' ,
                       auto_size_columns=True,enable_events=True,def_col_width=25,text_color="black",
                       justification='right',alternating_row_color=colr2,
                       key='-TABLE-', headings = hUNQ,metadata=sortState)]
            ]
    sg.theme(colorTheme)    
    window2 = sg.Window(f"Unique for {title}", layout2,finalize=True,resizable=True, grab_anywhere=False,metadata=[windowParent,col])
    showDFUNwindow = window2
    table = window2['-TABLE-']
    table.bind('<Button-1>', "Click")
    dataStore[table]=valuesUNQ
    
    return window2,table,valuesUNQ,hUNQ

############################################################

def showColAnal(xrefsO2T,xrefsT2O,colr1,colr2):
    global dataStore
    values=[]
    header = ["Original Column","Transformed Column"]
    for col in sorted(xrefsO2T.keys()):
        tmp = [col,xrefsO2T[col]]
        values.append(tmp)
    
    rowColors = setRowColorsGeneric(values,colr1,colr2)
    
    sortState = {}
    for val in header:
        sortState[val]=-1
        
    
    a = [[sg.Text("Columns in Program NOT in Data",font='Courier 10 bold ',justification="left")],
         [sg.Listbox("",font='Courier 15 bold ',horizontal_scroll=True ,size=(20,5),key="-PNOTD-")]] 
    
    d = sg.Column(a)
    
    b = [[sg.Text("Columns in Data NOT in Program",font='Courier 10 bold ',justification="left")],
         [sg.Listbox("",font='Courier 15 bold ' ,enable_events=True,horizontal_scroll=True ,size=(20,5),key="-DNOTP-")]] 
    e = sg.Column(b)
    
    c = [d,sg.VerticalSeparator(color="black"),e]
    layout2 = [    
                   [sg.Text(f"Original COlumns Transformed to Columns")],
                   [sg.Button("Compare 2 Data"),sg.Button("Get SIJ Cols"),sg.Button("Full Data Column Map")],
                   [sg.Button('Quit')],
                   [c],
                   [ sg.Table(values=values,
                       vertical_scroll_only=False,col_widths=60,font='Courier 10 bold ' ,
                       auto_size_columns=True,enable_events=True,def_col_width=25,text_color="black",
                       justification='right',row_colors=rowColors,
                       key='-TABLECOLUMN-', headings = header,num_rows=20,
                       metadata=[values,rowColors,sortState])]
                ]
#    sg.theme(colorTheme)    
    window2 = sg.Window(f"Orig vs Trans Column Analysis", layout2,finalize=True,resizable=True, grab_anywhere=False,metadata="nothing")

    table = window2['-TABLECOLUMN-']
    table.bind('<Button-1>', "Click")
    dataStore[table]=values
    headerStore[table]=header
    windowsStore["columnAnalysis"] = window2   
    return window2,table,values,header

##########################################################

def showFullDataColMap(cols,vals):
    
    layout2 = [    
                   [sg.Text(f"Full Data Columns Map")],
                   [sg.Button('Quit')],
                   [sg.Button('Show Missing Fields')],
                   [ sg.Table(values=vals,
                       vertical_scroll_only=False,col_widths=60,font='Courier 15 bold ' ,
                       auto_size_columns=True,enable_events=True,def_col_width=25,text_color="black",
                       justification='right',row_colors=rowColors,
                       key='-TABLEDCMAP-', headings = cols,num_rows=20,
                       metadata=[vals])]
                ]
        
    window2 = sg.Window(f"Orig vs Trans Column Analysis", layout2,finalize=True,resizable=True, grab_anywhere=False,metadata="nothing")

    table = window2['-TABLEDCMAP-']
    table.bind('<Button-1>', "Click")
    dataStore[table]=values
    headerStore[table]=cols
    windowsStore["fullDataColMap"] = window2  

###########################################################

def showMissingColumns():
    global missed

    header_list = ["Column","% Missing","Missing","string","integer","float","boolean"]
    stats1Ex = {}
    
    stats1Tr = {}
    stats1Ci = {}
    
    for col in missed['Extract - Data']:
     #   print(col,stats1Extract[col])
        stats1Ex[col]= stats1Extract[col]

    
    for col in missed['Transform - Data']:
      #  print(col,stats1Transform[col])
        stats1Tr[col]= stats1Transform[col]

    for col in missed['CIM - Data']:
      #  print(col,stats1Cim[col])
        stats1Ci[col]= stats1Cim[col]
  
    valsExtract = getValues(stats1Ex,header_list)
    valsTransform = getValues(stats1Tr,header_list)
    valsCim = getValues(stats1Ci,header_list)
    
    
    
    layout = [
               [sg.Button("Quit")],
               [sg.Listbox(values=missed["BIC Inventory"],size=(10,5),font="CENTAUR 10"),
                sg.Listbox(values=missed["Transform Program"],size=(10,5),font="CENTAUR 10"),
                sg.Listbox(values=missed["Transform - SIJ"],size=(10,5),font="CENTAUR 10")],
                [sg.Table(values=valsExtract,text_color="black", auto_size_columns=False,enable_events=True,num_rows=10,font="CENTAUR 10",
                    justification='center',pad=(5,5),vertical_scroll_only=False,
                    key='-TABLEMISSEXTR-',headings = header_list)],
                [sg.Table(values=valsTransform,text_color="black", auto_size_columns=False,enable_events=True,num_rows=10,font="CENTAUR 10",
                    justification='center',pad=(5,5),vertical_scroll_only=False,
                    key='-TABLEMISSTRANS-',headings = header_list)],
                [sg.Table(values=valsCim,text_color="black", auto_size_columns=False,enable_events=True,num_rows=10,font="CENTAUR 10",
                    justification='center',pad=(5,5),vertical_scroll_only=False,
                    key='-TABLEMISSCIM-',headings = header_list)]
               ]

#    colorTheme = windowP.metadata[0]  
    theme = "LightBrown 3"
    sg.theme("LightBrown 3")     
    window2 = sg.Window("Missing Fields",layout,finalize=True,resizable=True,metadata=[theme])
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
    tableex = window2['-TABLEMISSEXTR-']
    tableex.bind('<Button-1>', "Click")
    tabletr = window2['-TABLEMISSTRANS-']
    tabletr.bind('<Button-1>', "Click")
    tableci = window2['-TABLEMISSCIM-']
    tableci.bind('<Button-1>', "Click")
    
    dataStore[tableex] = valsExtract
    dataStore[tabletr] = valsTransform
    dataStore[tableci] = valsCim
    
    
    return window2,tableex,tabletr,tableci
    # headerStore[tableFile1] = header_list
    
 
###########################################################

def sortUniqe(table,window,dataStore,headerStore):
    global color1,color2
    try:
        e = table.user_bind_event
        region = table.Widget.identify('region', e.x, e.y)
        sortAsc = {}
        sortAsc[1] =False
        sortAsc[-1]=True
   #     print("R ",region)
        if region == 'heading':
            values = dataStore[table]
            
           
            header = headerStore[table]
            # print("SU header ",header)
            column = int(table.Widget.identify_column(e.x)[1:])
            col=header[column-1]
            
            sortState = table.metadata
           
            sortState[col]*=-1
            table.metadata = sortState
          
            values = sorted(values, key=lambda element: (element[column-1]),reverse=sortAsc[sortState[col]]) 
#            rowFile1Colors = setRowColors(values,color1,color2,"pink",header)
            rowFile1Colors = setRowColorsGeneric(values,color1,color2)

            window["-TABLE-"].update(values=values)
            dataStore[table] = values
    except Exception as err:
        exceptionLog(err,inspect.currentframe().f_code.co_name)
                    
#####################################################        

def tranfColXref(file):
    global transformProgram
 #   fin = open("/home/joe/bic_etl/cdos/business/nonprofit/scripts/reg_finan.js","r")
    fin = open(file,"r")
    
    lines = fin.readlines() 
    transformProgram = lines
    fout = open("output.txt","w")
    org = []
    xrefsO2T = {}
    xrefsT2O = {}

    for line in lines:
        if re.findall("row",line.lower()) and re.findall("=",line.lower()) and not re.findall("^//",line.lstrip()):
            st1=line.find("[")
            ed1=line.find("]")
            st2=line.rfind("[")
            ed2=line.rfind("]")
            org.append(line[st2+2:ed2-1])
    #        print(line)
    #        print(line[st1+1:ed1],line[st2+1:ed2])
            fout.write(f"{line[st1+1:ed1]}  {line[st2+1:ed2]}\n")
            og = line[st2+1:ed2].replace("'","")
            og = og.replace('"','')
            
            og = og.replace("].toLowerCase()","")


            tr = line[st1+1:ed1].replace(".toLowerCase()","")
            tr = tr.replace('"','')
            tr = tr.replace("'","")
            



            # tr = line[st1+1:ed1]
            # og = line[st2+1:ed2]

            xrefsT2O[tr]  = og
            xrefsO2T[og]  = tr
    return xrefsO2T,xrefsT2O
                
############################################################

def wrap(string, lenght=60):
    if isinstance(string,str):
       return '\n'.join(textwrap.wrap(string, lenght))
    else:
        return ""
        
        
def getDefinitionFile():

    layout = [
               [sg.Button("Quit")],
               [sg.Text("Choose Library Definition Listing:",font="CENTAUR 15"),sg.FilesBrowse(button_text="Local File",initial_folder="/home/joe/work/CDOS/nonprofit",font="CENTAUR 15",file_types=[("CSV Files","*.csv"),("TSV Files","*.tsv"),("Excel Files","*.xlsx")],enable_events=True,key='-FILEDEF-')],
               [sg.Button("Get Defition File")]
             ]

#    colorTheme = windowP.metadata[0]  
    theme = "LightBrown 3"
    sg.theme(theme)     
    window2 = sg.Window("Library Defintion File",layout,finalize=True,resizable=True,metadata=[theme])
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)


# ## GUI

# In[4]:


def cronGUI():
    global ds,text2,a,string,numWindows,color1,color2,file,transform,dataStore,statsStore
    global windowsStore,xrefsBy4x4,groupMenu,windowsReset
    global transformProgram,dnotpLines,rowToWrite
    global extractColumns,transformColumns,cimColumns
    global transformSijColumns,loadSijColumns,xrefsO2T,xrefsT2O
    global dfExtract,dfTransform,dfCim,missed,fields
    global stats1Extract,stats1Transform,stats1Cim
    global vals,cols,wid,dfoutput,mfShort,dataSetsEtl,cim4x4
    global dfExtract,dfTransform,directory
    global sourceDefFile,nfieldsadded,nfieldsAddedS
    
    dataStore = {}
    statsStore = {}
    windowsStore = {}
    windowsReset = {}
    
    datasets = init()
    cimColumns = []
    transformColumns = []
    extractColumns = []
    transformSijColumns = []
    loadSijColumns = []
    nfieldsAddedS=0
    errorsByDate,errorsByName=getRecentErrorsNew()
    
##  get xrefs b/w 4x4 ids and datasert titles...yay   
    xrefsBy4x4,xrefsByTitle,fields = getXrefs()

    mf = pd.read_excel("BICDataInventoryandMetadata.xlsx",skiprows=0,sheet_name="Inventory_Active",engine="openpyxl")
    
    mf["CIM Link"] = mf.apply(map4x4,axis=1)

    mf=mf.loc[~mf["Standardized Title for Dataset"].isna()]
    mfShort = mf[['Standardized Title for Dataset', 'Data Link','CIM Data Type','GoCodePublishYear','Standardized Short Description','CIM Link']]
    mfShort["Standardized Title for Dataset"] = mfShort["Standardized Title for Dataset"].astype(str).str.strip()  
    
    header_list = list(mfShort.columns)
    # mfV = []
    # a = ["","",nan,nan,""]
    # mfV.append(a)
    layout = [
              [sg.Text("BIC Cron DataSets")],
              [sg.Combo(datasets,enable_events=True,key="-DATASET-",font='Courier 10 bold ')],
              [sg.ButtonMenu('Groups', menu_def=groupMenu, key='Group Menu',font='Courier 15 bold')],
              [sg.Text("4x4",font='Courier 15 bold '),sg.Input("",size=[8,1],key="-4x4-",font='Courier 10 bold '),
               sg.Button("4x4")],
              [sg.Button('Close',font='Courier 15 bold '),sg.Button("ReSet",font='Courier 15 bold '),sg.Button('STDOUT',font='Courier 15 bold')],
              [sg.Button('Recent Errors',font='Courier 15 bold '),sg.Button("Update Logs",font='Courier 15 bold '),sg.Button("View Log Summary",font='Courier 15 bold ')],
              [sg.FilesBrowse(button_text="Local File",initial_folder="/home/joe/bic_etl",font="CENTAUR 15",file_types=[("CSV Files","*.csv"),("TSV Files","*.tsv"),("Excel Files","*.xlsx")],enable_events=True,key='-FILE1-')],
              [sg.Button("Column Analysis",font='Courier 15 bold '),sg.Button("Inv Fields",font='Courier 15 bold ')],
   #          [sg.Button("GO")],
              [sg.Button("Extract",font='Courier 15 bold ',key="-EXTRACT-",visible=True),
               sg.Button("Analyze-Extr",font='Courier 15 bold ',key="-EXTRACTANAL-",visible=False),
               sg.Text("",visible=False,font='Courier 15 bold ',key="-EXTRACTINFO-")],
              [sg.Button("Transform",visible=True,font='Courier 15 bold ',key="-TRANSFORM-"),
               sg.Button("Ananlyze-Trans",font='Courier 15 bold ',key="-TRANSFORMANAL-",visible=False),
               sg.Button("View-Transform",font='Courier 15 bold ',key="-TRANSFORMVIEW-",visible=False),
               sg.Text("",visible=False,font='Courier 15 bold ',key="-TRANSFORMINFO-")
              ],
              [sg.Button("CIM API",font='Courier 15 bold ',key="-CIMAPI-",visible=True),sg.Text("",visible=False,font='Courier 15 bold ',key="-CIMINFO-")],
              [sg.Button("Create Source Defs",font='Courier 15 bold ',visible=False),sg.Button("Analyze Source Defs",font='Courier 15 bold')],
              [sg.Button("Create Field Xrefs",font='Courier 15 bold '),sg.Button("Show Field Xrefs",font='Courier 15 bold'),sg.Button("Src-Trns XREFS Scratch",font='Courier 15 bold ')],
              [sg.Multiline(default_text="Dataset Summary",enable_events=True,font='Courier 15 bold ',background_color="blue",key="-OUTPUT-",size=[70,10]),
               sg.Multiline(default_text="ETL Summary",key="-ETL-",size=[70,20],font='Courier 15 bold ')]             
            ]

       
    # Create the Window
    sg.theme('Dark Green 5')
    window2 = sg.Window('ETL', layout,finalize=True,resizable=True)
    #window = sg.Window('Window Title', layout, web_port=2222, web_start_browser=False)
    #table = window2['-TABLE2-']

    #window2.move(window.current_location()[0]+600, window.current_location()[1])
    try: 
        while True:

         #   event, values = window2.read()
            wid, event, values = sg.read_all_windows()
            print("\n\n-----------------------------------\n")
            print('event: ',event)
            print(wid.Title)
            print(wid)
            if event == sg.WIN_CLOSED or event == 'Close':
                window2.close()
                break
            elif event ==  event == 'Quit':
                wid.close()
### DATASET                
            elif event == "-DATASET-" or event == "4x4" or event == "Group Menu":
                window2["-EXTRACTANAL-"].update(visible=True)
                window2["-TRANSFORMANAL-"].update(visible=True)
                window2["-EXTRACTINFO-"].update("")
                window2["-TRANSFORMINFO-"].update("")
                window2["-OUTPUT-"].update("")
                window2["-ETL-"].update("")  
                window2["-TRANSFORMVIEW-"].update(visible=False)
            
      #      elif event == "GO":#
                if event == "-DATASET-":
                    (ds)  = list(values.items())
                    ds=ds[0][1]
                elif event == "4x4":
                    ds = xrefsBy4x4[values["-4x4-"]]
                  #  print("XREF DS ",values["-4x4-"],ds)
                elif event == "Group Menu":
                    ds = values["Group Menu"]
              
#                ds = ""
                dstitle = ds 
                if ds in mapTitles:
                    ds = mapTitles[ds]
                print("Daetaset ",ds)
                datasetTitle = ds
                try: 
                    mmf = mfShort.loc[mfShort["Standardized Title for Dataset"].str.strip() == ds.strip()]
                    print("MMF ",mmf.shape[0])
                    cim4x4 = mmf['Data Link'].values.tolist()[0]
                    cimApi = f"https://data.colorado.gov/api/views/{cim4x4}/rows.csv?accessType=DOWNLOAD"
                    if mmf.shape[0] > 0:
                    #            mmf["Standardized Short Description"] = mmf["Standardized Short Description"].map(wrap)          
                        text = f"Title             : {mmf['Standardized Title for Dataset'].values.tolist()[0]}\nSocrata        : {mmf['Data Link'].values.tolist()[0]}\nData Type    : {mmf['CIM Data Type'].values.tolist()[0]}\nPublish Year: {mmf['GoCodePublishYear'].values.tolist()[0]}\nCIM Link : {mmf['CIM Link'].values.tolist()[0]}\nDescription  : {mmf['Standardized Short Description'].values.tolist()[0]}"            
                       # display(mmf)
                    else:
                        text = "None"
                    if ds.strip() in dataSetsEtl:
                          text2,extract,transform,trfile,directory,datasetCharId = runETL(ds.strip())
                          print("HIT HIT HIT ",text2,extract)
                          print("DATASETCHARID 2",datasetCharId)
                    else:
                          text2=""
                          extract = ""
                    if len(extract) > 10:
                        window2["-EXTRACT-"].update(visible=True)
                    if len(transform) > 10:
                        window2["-TRANSFORM-"].update(visible=True)
                     #   window2["-TRANSFORM-"].update(visible=True)

                    if len(cimApi) > 10:                 
                        text2+=  f"\n\nCIM API\n{cimApi}"
                        window2["-CIMAPI-"].update(visible=True)
                    if len(transform) > 4:
                        spl = transform.split()
                        a= spl[1]
                        trfile=a
                    print("TRFILE ",trfile)
                    if len(trfile) > 4:
                        window2["-TRANSFORMVIEW-"].update(visible=True)
                    window2["-OUTPUT-"].update(text)
                    window2["-ETL-"].update(text2)
                    link =  mmf['CIM Link'].values.tolist()[0]
                    string = "\n\nCLI Update\n"
                    string+= f"node /home/joe/bic_etl/general/scripts/bic_etl.js"
                    string+= f"\n-t '{ds}'\n"
                    string+= "-p ?"
                    window2["-ETL-"].update(string,append=True)
                except Exception as err:
                    print(f"Dataset Not Found: {ds}")
                    exceptionLog(err,inspect.currentframe().f_code.co_name)
                
           #     print("Link ",mmf['CIM Link'],link.find("http"))
                
                # if link.find("http") > -1:
                #      window2["-LINK-"].update (visible=True)
                # else:
                #      window2["-LINK-"].update (visible=False)
### LINK                
               
            elif event == "-LINK-":
                  #  print("Going To: ",link) 
                    if len(link) > 10:
                        webbrowser.open(link)
                        
### ReSet
            elif event == "ReSet":
                for wid,val in windowsReset.items():
                    print("RES ",type(wid),type(val),wid)

### Create Source-Transform X-ref from Scratch
            elif event == "Src-Trns XREFS Scratch":
                createSrcTransFieldXrefScratch(cim4x4)
    
### Analyze Source Defs
            elif event == "Analyze Source Defs":   
                targDir = os.path.join(bicHome, directory,definitionDir)
                defFile = os.path.join(targDir,f"{cim4x4}_{datasetCharId}_src_fld_defs.json")
                analyzeFieldDefs(defFile)

        
### Write Source Defs
            elif event == "Write Source Defs":
                print("DATASETCHARID ",datasetCharId)
                targDir = os.path.join(bicHome, directory,definitionDir)
                createDir(targDir)
                sourceDefFile = writeSoureFieldList(cim4x4,values,targDir,datasetCharId)

### GET DEFINITION FILE
            elif event == "Source Defs":
                getDefinitionFile()

### SOURCE Defs              
            elif event == "Get Defition File":  
                dfile = values["-FILEDEF-"]
                sourceDefs2Fields(dfile,dfExtract.columns)
            
### Create Field XREFS
            elif event == "Create Field Xrefs":
                targDir = os.path.join(bicHome, directory,definitionDir)
#                createDir(targDir)

                if len(sourceDefFile) < 4:
                    sourceDefFile = os.path.join(targDir,f"{cim4x4}_{datasetCharId}_src_fld_defs.json")                    
                print("SDF ",sourceDefFile)
                transTmp = createSrcTransFieldXref(cim4x4,dfExtract.columns,dfTransform.columns,sourceDefFile,targDir)

### Show Field XREFS
            elif event == "Show Field Xrefs":
                targDir = os.path.join(bicHome, directory,definitionDir)
                file = os.path.join(targDir,f"{cim4x4}_{datasetCharId}_src_trns_xrefs.json")
                showSrc2TransXrefs(file)
                
### ADD XREF FIELD Scratch          
            elif event == "Add XREF Field SCR":
                nfieldsAddedS+=1
                #if nfieldsAddedS == 1:
                 #    wid[f"secondFrame"].update(visible=True)
                 #    wid[f"someFrame"].update(visible=True)

                wid[f"FRAME:CUST:{nfieldsAddedS+10}"].update(visible=True)

### ADD XREF FIELD            
            elif event == "Add XREF Field":
                nfieldsAdded+=1
                if nfieldsAdded == 1:
                     wid[f"secondFrame"].update(visible=True)
                     wid[f"someFrame"].update(visible=True)

                wid[f"FRAME:CUST:{nfieldsAdded}"].update(visible=True)

### Write XREF FILE   (write source to Transformed XREF file)                
            elif event == "Write XREF File":
                try:
                    targDir = os.path.join(bicHome, directory,definitionDir)
                    createDir(targDir)
                    writeFieldFileN2(cim4x4,datasetTitle,values,targDir,datasetCharId)
                except Exception as err:
                    print("ERROR ",err)
                    
### LISTBOX    (selection made in SOURCE to Transformed XREF list)
            elif event.find("LISTBOX") > -1 and values[event] == "NONE":
                newname = sg.popup_get_text("Input Transform Field Name in Camel-Case",font='Courier 25 bold')
    ##  Force user to input a variable with NO Spaces..
                while newname and (newname.find(" ") > -1 or newname[0].isupper()):
                    if newname.find(" ") > -1:
                        sg.popup("No Spaces Allowed",font='Courier 25 bold')
                    elif newname[0].isupper():
                        sg.popup("Please us Camel-Case (i.e. First letter NOT Capitalized)",font='Courier 25 bold')

                    newname = sg.popup_get_text("Input Field Name in Camel Case",font='Courier 25 bold')

                if newname:
                    transTmp.append(newname)
                    transTmp = reorderList(newname,sorted(transTmp))
                    a=transTmp.copy()
                    a.append("NONE")
                    wid[event].update(values=a,set_to_index=0)
                    wid.refresh()         


### Output Text Table
            elif event == "Output Text Table" or event == "Output CSV File":    
                vals = wid.metadata[3]
                cols = wid.metadata[4]
                ff = wid.metadata[5]
                df = pd.DataFrame(vals,columns=cols)
                dfoutput = df.copy()
                ofile = sg.popup_get_text("Output File?",font='Courier 15 bold') 
                if event == "Output Text Table":
                    fout = open(ofile.strip(),"w+")
                    fout.write(f"\nDataset: {dstitle}")
                    fout.write(f"\nFile: {ff}\n\n")
                    fout.write(f"Shape: {df.shape}\n\n")
                    string=tabulate(df, headers='keys', tablefmt='fancy_outline')
                    fout.writelines(string)
                    fout.close()
                    sg.popup(f"Text Table written to {ofile}")
                else:
                    c1 = []
                    c2 = []
                    c3 = []
                    c1.append(f"Dataset: {dstitle}")
                    c2.append(f"File: {ff}")                  
                    c3.append(f"Shape: {df.shape}")
                    for nn in range(1,len(dfoutput.columns)):
                        c1.append("")
                        c2.append("")
                        c3.append("")
                        
                    columns = pd.MultiIndex.from_arrays([
                        c1,c2,c3,dfoutput.columns
                    ])
                    df.columns = columns
                    df.to_csv(ofile.strip(),index=False)
                    
### Output Columns
            elif event == "Output Columns":
                 df = wid.metadata[1]
               
                
                 ctitle = wid.metadata[2]
                 columns = sorted(list(df.columns))
                 fout = open(f"/tmp/columns.txt","a+")
                 fout.write(f"\n{datetime.today()} -> {cim4x4} -> {ctitle} - {datasetTitle}\n")
                 for col in columns:
                     fout.write(col+"\n")
                 fout.close()
                 print(f"{len(columns)} columns written to /tmp/columns.txt")

                    ### STDOUT
            elif event == "STDOUT":
                layouto = [[sg.Button("Quit")],
                          [sg.Multiline(s=(90,30),font='Courier 15 bold ',background_color="#F7DC6F",text_color="black",key="-STDOUT-")]
                          ] 
                wind = sg.Window('STDOUT STDERR', layouto,finalize=True,resizable=True)
### View Log Summary
            elif event == 'View Log Summary':
                vals,cols = getLogSummary()
                showLogSummary(vals,cols)
        
### Local File
            elif event == '-FILE1-':
                    file=values["-FILE1-"]
                    dfLocal,stats1Local = getFile("Local",file,window2)
                    LocalColumns = list(dfLocal.columns)
                    color1 = colorPairs[numWindows][0]
                    color2 = colorPairs[numWindows][1]
                  
                    numWindows+=1
                    if numWindows > len(colorPairs):
                        numWindows=0

                    WindowC,tabl1,valsFile1,rowFile1Colors = compareWindow(wid,stats1Local,dfLocal,file,"Local File Analysis","DarkPurple")
                    dataStore[tabl1]=valsFile1
                    windowsOpen["main"].append(WindowC)    
        
### Recent Errors
            elif event == 'Recent Errors':
                w = showRecentLogs(errorsByDate)
            
### Include Completed Errors
            elif event == "Include Completed":
                errorStatus = getErrorStatus()
                values,rowColrs = orderErrors(errorsByDate,errorStatus,1)
                wid["-DAILY-"].update(values=values,row_colors=rowColrs)
        
            
### Update Logs
            elif event == "Update Logs":
                nfiles,files = updateLogs(1)
                print(f"Downloaded {nfiles} for THIS month")
                nfiles,files = updateLogs(2)
                print(f"Downloaded {nfiles} for Last month")
                errorsByDate,errorsByName=getRecentErrorsNew()
                string=f"{nfiles} Downloaded\n"
            
### Daily-click
            elif event == '-DAILY-Click':
                xx=wid.metadata

                table=wid["-DAILY-"]
                e = table.user_bind_event
                region = table.Widget.identify('region', e.x, e.y)
                if region == 'heading':
                    row = 0
                elif region == 'cell':
                    row = int(table.Widget.identify_row(e.y))
                elif region == 'separator':
                    continue
                else:
                    continue

             #   print(row,xx[row-1])

                string = f"Date: {xx[row-1][0]}\n\nDataset: {xx[row-1][1]}\n\nMessage: {xx[row-1][3]}\n"
                showError(xx[row-1])

### Show Missing Columns
            elif event == "Show Missing Fields":
                  window2,tableex,tabletr,tableci = showMissingColumns()
            
###  Write Log
            elif event == "Write Log":
                row=wid.metadata
            #    print(row)
                rowToWrite = [row[0],"Joe Comeaux",row[1],row[2],values["-ERRORTITLE-"],
                              row[4],values["-ERRORNOTES-"],values["-ERRORJIRA-"],row[-1]]
                count=0
                for val in rowToWrite:
                  #  print(count,val)
                    count+=1
    #            yy = [date,errorsByDate[date]["name"][nn],errorsByDate[date]["4x4"][nn],errorsByDate[date]["title"][nn],msg,errorsByDate[date]["stitle"][nn]]
                ret = toGoogleSheet(rowToWrite)
                sg.Popup(f"Result of {event}\n{ret}",font='Courier 10 bold ')
               
### Mark Done
            elif event == "Mark Done" or event == "Mark Skip":
                row=wid.metadata
        
                status="Fixed"
                if event == "Mark Skip":
                    status="Skipped"
                toMark = [row[-1],row[1],row[3],row[2],status]
                ret = markDone(toMark)
                sg.Popup(f"Result of {event}\n{ret}",font='Courier 10 bold ')

### Full Data Column Map
            elif event == "Full Data Column Map":
                cols,vals,missed = fullDataColumnMap(cim4x4)
                showFullDataColMap(cols,vals)
            
### Get SIJ Cols
            elif event == "Get SIJ Cols":
                getSijColumns("")
              #  print("Tr SIJ ",transformSijColumns)
              #  print("LD SIJ ",loadSijColumns)
                 
### DNOTP

            elif event == "-DNOTP-":
                col = values["-DNOTP-"][0]
                if col in dnotpLines:
                    string=""
                    string = "\n".join(dnotpLines[col])
                else:
                    string="NOTHING FOUND"
                sg.Popup(string)
                    
             #   print("DNOTP STRai",string)
### Column Analysis                
            elif event == "Column Analysis":
           #     trfile = dataSetsEtl[ds]["transform"]["file"]
                if transform[0:4] == "node":
                    trfile = transform[5:]
        
                
                xrefsO2T,xrefsT2O = tranfColXref(trfile)
                color1 = colorPairs[numWindows][0]
                color2 = colorPairs[numWindows][1]
                
                numWindows+=1
                if numWindows > len(colorPairs):
                    numWindows=0
                showColAnal(xrefsO2T,xrefsT2O,color1,color2)
                
### Inv Fields 
            elif event == "Inv Fields":
                showInvFields(cim4x4)
        
             
### Compare 2 Data                 
            elif event == "Compare 2 Data":   
              #  print("HERE We GO")
                ww = windowsStore["extract"]
                wdf = ww.metadata[1]
                
                compare2Data(wdf,xrefsO2T)
                         
### CIMAPI                
            elif event == "-CIMAPI-":
                  #  df1,stats1 = getFilesClicked(cimApi,window2)
                    dfCim,stats1Cim = getFile("Fetch",cimApi,window2)
                    cimColumns = list(dfCim.columns)
                    color1 = colorPairs[numWindows][0]
                    color2 = colorPairs[numWindows][1]

                    numWindows+=1
                    if numWindows > len(colorPairs):
                        numWindows=0

                    WindowC,tabl1,valsFile1,rowFile1Colors = compareWindow(wid,stats1Cim,dfCim,cimApi,"CMI Analysis","DarkRed")
                    dataStore[tabl1]=valsFile1
                    
                    windowsOpen["main"].append(WindowC)  
                    
### TRANSFORM               
            elif event == "-TRANSFORM-":
                print("TRANSFORM ")
                print("tr ",transform)
                a=subprocess.run(transform,shell=True,capture_output=True,text=True)
                string= "\n\n-------------------------------------\n"
                string+= "TRANSFORM Output\n"
                tfile=""
                if len(a.stderr) > 0:
                    string+= f"Error:\n {a.stderr}"
                elif len(a.stdout) > 0 or len(trfile) > 0:
                    if len(a.stdout) > 0:
                        for msg in a.stdout.split("debug msg:"):    
                            if msg.find("final file is at:") > -1:
                                tmp = msg.split(" ")
                                tfile = tmp[-3]
                            elif "Output File" in msg:
                                il = msg.index("Output File")
                                tmp = msg[il+13:]
                                tfile = tmp
                            tfile=tfile.strip()
                        #    print(f"TTTFILE {tfile}:")   
                    elif len(trfile) > 0:
                        tfile=trfile
                    if os.path.isfile(tfile):

                        window2["-TRANSFORMANAL-"].update(visible=True)
                        fileStats = os.stat(tfile)
                    #    print("FSTATS ",fileStats)
                        dt = datetime.fromtimestamp(fileStats.st_ctime)
                        string = f"{fileStats.st_size:,} bytes Created: {dt}  file: {tfile}"
                     #   print("STRING ",string)
                        window2["-TRANSFORMINFO-"].update(string,visible=True)
                            
                    string+=f"STDOUT: {a.stdout}"
                    window2["-ETL-"].update(string,append=True)
                    
### TRANSFORMANAL
            elif event == "-TRANSFORMANAL-":
                #    df1,stats1 = getFilesClicked(tfile,window2)
                    try: 
                        dfTransform,stats1Transform = getFile("Local",tfile,window2)
                        transformColumns = list(dfTransform.columns)
                        color1 = colorPairs[numWindows][0]
                        color2 = colorPairs[numWindows][1]

                        numWindows+=1
                        if numWindows > len(colorPairs):
                            numWindows=0
                        print("TFILE ",tfile)
                        WindowC,tabl1,valsFile1,rowFile1Colors = compareWindow(wid,stats1Transform,dfTransform,tfile,"Transform Analysis","DarkPurple")
                        dataStore[tabl1]=valsFile1
                        windowsOpen["main"].append(WindowC)    
                    except  Exception as err: 
                        exceptionLog(err,inspect.currentframe().f_code.co_name)
### TRANSFORMVIEW
            elif event == "-TRANSFORMVIEW-":
                showFile(trfile)
             
### CREATE FIELD LISTING
            elif event == "Field Xrefs":
                fieldXrefs = createFieldFile(w4x4,list(dfExtract.columns),list(dfTransform.columns))

### WRITE FIELD LIST FILE
            elif event == "Write Fields":
                writeFieldFile(w4x4,values,fieldXrefs,f"{bicHome}{directory}")
                                
### EXTRACT                  
            elif event == "-EXTRACT-":
                print("EXTACT: ",extract)
                a=subprocess.run(extract,shell=True,capture_output=True,text=True)
                print("RETURN ",a)
                string= "\n\n-------------------------------------\n"
                string+= "Extract Output\n"
                if len(a.stderr) > 0:
                    string+= "fError:\n {a.stderr}"
                string+=f"STDOUT: {a.stdout}"
                window2["-ETL-"].update(string,append=True)
                sx = string.find("successfully download to")
                string[sx+25:]
                sxo = string[sx+25:].find("!")
             
                file=f"/home/joe/bic_etl{string[sx+25:sx+25+sxo]}"
              
                if os.path.isfile(file):
                  
                    window2["-EXTRACTANAL-"].update(visible=True)
                    fileStats = os.stat(file)
                    dt = datetime.fromtimestamp(fileStats.st_ctime)
                    string = f"{fileStats.st_size:,} bytes Created: {dt}  file: {file}"
                    window2["-EXTRACTINFO-"].update(string,visible=True)
                    
### EXTRACTANAL                      
            elif event == "-EXTRACTANAL-":
                file=stringArgs(extract)
                sg.popup(f"Analyze File: {file}")
             #   df1,stats1 = getFilesClicked(file,window2)
                dfExtract,stats1Extract = getFile("Local",file,window2)
                extractColumns = list(dfExtract.columns)
                color1 = colorPairs[numWindows][0]
                color2 = colorPairs[numWindows][1]
                
                numWindows+=1
                if numWindows > len(colorPairs):
                    numWindows=0
                    
                WindowC,tabl1,valsFile1,rowFile1Colors = compareWindow(wid,stats1Extract,dfExtract,file,"Extract Analysis","DarkBlue16")
                dataStore[tabl1]=valsFile1
                windowsOpen["main"].append(WindowC)
                windowsStore["extract"] = WindowC
                window2["Create Source Defs"].update(visible=True)
                window2["Analyze Source Defs"].update(visible=True)
                
                
                
### TABLEFILE-CLICK
            elif event == "-TABLEFILE-Click":
                try:
                    tabl1 = wid["-TABLEFILE-"]
                    dat = wid.metadata[3]
                    
                    row,col=getRowClicked(tabl1,dat)
                    if row == 0:
                       tabl1 = wid["-TABLEFILE-"]
                       header = headerStore[tabl1]
                       stats1 = statsStore[tabl1]
                       valsFile1,columnSortStateTable1 = sortTable(row,stats1,tabl1,event,header)          
                       rowFile1Colors=setRowColors(valsFile1,color1,color2,"pink",header)
                       wid["-TABLEFILE-"].update(values=valsFile1,row_colors=rowFile1Colors)
                       wid["-TABLEFILE-"].metadata=columnSortStateTable1
                    else:
                        
                        df1 = wid.metadata[1]
                        unq = df1[col].value_counts()
                        colorTheme=wid.metadata[0]
                        
                        w,t,values,uHead = showDFUN(col,unq,wid,color1,color2,colorTheme)
                      #dataStore[t] = values
                        headerStore[t] = uHead
                        windowsOpen["main"].append(w)
                except  Exception as err: 
                       exceptionLog(err,inspect.currentframe().f_code.co_name)
                    
                    
### TABLE-Click
            elif event == "-TABLE-Click":  # This is the Unique Values tables
                try: 
                    table = wid['-TABLE-']                              
                    row,val =getRowClickedUN(table)
                    if row == 0:
                        sortUniqe(table,wid,dataStore,headerStore)
                    else:
                        widP = wid.metadata[0]
                        col = wid.metadata[1]
                        df = widP.metadata[1]
                        tmp = df.loc[df[col] == val]
                        showDfRecs(tmp,col,val,widP,title="DF Unique Record Values")
                except  Exception as err: 
                   exceptionLog(err,inspect.currentframe().f_code.co_name)

###  -TABLEMISSEXTR-Click                   
            elif event in ["-TABLEMISSEXTR-Click","-TABLEMISSTRANS-Click","-TABLEMISSCIM-Click"] :
                if event == "-TABLEMISSEXTR-Click":
                   tabl1 = wid["-TABLEMISSEXTR-"]
                   title = "EXTRACT"
                   df = dfExtract
                elif event == "-TABLEMISSTRANS-Click":
                   tabl1 = wid["-TABLEMISSTRANS-"]
                   df =  dfTransform
                   title = "TRANSFORM"
                elif event == "-TABLEMISSCIM-Click":
                   tabl1 = wid["-TABLEMISSCIM-"]
                   df =  dfCim
                   title="CIM"
                 
                
                vals = dataStore[tabl1]
                row,col=getRowClicked(tabl1,vals)
                unq = df[col].value_counts()
                colorTheme=wid.metadata[0]
                w,t,values,uHead = showDFUN(col,unq,wid,color1,color2,colorTheme,title)
                  #dataStore[t] = values
                headerStore[t] = uHead
                windowsOpen["main"].append(w)
                   
         
    except  Exception as err: 
       exceptionLog(err,inspect.currentframe().f_code.co_name)
 
    for wid in windowsOpen["main"]:
      #  print("window MA",wid)
        if wid:
          #  print("cosing ",wid)
            wid.close()
            wid = None

cronGUI()



### Bottom


# # Bottom
