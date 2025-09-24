#!/usr/bin/env python
# coding: utf-8

# In[139]:


import pandas as pd

import os,sys
import json,csv
import argparse
import os.path
bic_etl_home = os.getenv('bic_etl_home')
## Add the bic_etl/general/script directory to path 
sys.path.insert(0, os.path.join(bic_etl_home, 'general', 'scripts'))
import custom_log
import jcLib
import gspread
from oauth2client.service_account import ServiceAccountCredentials

## Parse Input Arguments
parser = argparse.ArgumentParser(description='generic BIC transform script')
parser.add_argument('-t', '--title', help='-t is the dataset title')
parser.add_argument('-w', '--w4x4', help='-w is the CIM 4x4 identifier of the dataset')
parser.add_argument('-p', '--parent', help='-p is the parent director under bic_etl for the dataset')

args, leftovers = parser.parse_known_args()
pdir = args.parent
print(f"processing dataset {args.title}")
print(f"parent directory {pdir}")

dirTarget = f'{bic_etl_home}/{pdir}'
print("target directory",dirTarget)

def getInfo():
    '''Reads the Inventory google sheet and gets the datasets title and cross-refs it to the Socrata 4x4 id.  Also
    gets the fields by 4x4 dataset id and by the title'''
    scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
             "https://www.googleapis.com/auth/drive.file",
                  "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name('/home/joe/work/client_secret.json',
     scope)
    client = gspread.authorize(creds)

    tracker = client.open('cdos datasets for Python ETL transition').worksheet('datasets')
   
    df = pd.DataFrame(tracker.get_all_records(head=1))

    return  df

def getEtlInfo(dirTarget):
    etlInfoFile=open(f'{dirTarget}/run_etl_new.json')
    etlInfoTmp=json.load(etlInfoFile)
    etlInfoFile.close()
    etlInfo={}
    opts = {}
    for etl in etlInfoTmp:
        if etl['title'] == args.title :
            w4x4 = etl['4x4']
            etlInfo['4x4'] = w4x4
            trans=etl['transform']
            outputFile=trans['outputFile']
            inputFile=trans['inputFile']
            delimiter=trans['delimiter']
            dictionary=trans['dictionary']
            if "options" in trans:
                opt= trans['options'][0]
                spl = opt.split("=")
                opts[spl[0]] = int(spl[1])
                etlInfo['options']=opts
            etlInfo['outputFile']=outputFile
            etlInfo['inputFile']=inputFile
            etlInfo['delimiter']=delimiter
            etlInfo['dictionary']=dictionary
            print(trans)
    return etlInfo   

#df=getInfo()
etlInfo=getEtlInfo(dirTarget)
dictFile=etlInfo['dictionary']
inFile=etlInfo['inputFile']
outFile=etlInfo['outputFile']
delimiter=etlInfo['delimiter']
if "options" in etlInfo:
    options=etlInfo['options']
    print("Options: ",options)
else:
    options=""
w4x4=etlInfo['4x4']

print(etlInfo)

logger2 = custom_log.setupNew(args.title)
logger2.info("Starting: {arg.title}",extra={"s4x4":w4x4})

#inFile=inFile.split(".")[0]+".tsv"
dictFile=open(f'{dirTarget}/{dictFile}')


dictLookup = json.load(dictFile)
dictFile.close()
fieldXrefs={srcField:refs['xref'] for srcField,refs in dictLookup[w4x4].items()}

# In[151]:
quoting=0
if "quoting" in options:
    quoting=options["quoting"]

#df = pd.read_csv(f'{dirTarget}/{inFile}',quoting=quoting,delimiter=delimiter,encoding='latin',keep_default_na=False)

with open(f'{dirTarget}/{inFile}','r',encoding="latin") as fin:
    with open(f'{dirTarget}/{outFile}','w') as fout:
        header=fin.readline().strip().split(delimiter)
     #   header.append("TEST")
        headerNew=""
        for nn,col in enumerate(header):
            if col in fieldXrefs:
               colNew = fieldXrefs[col]
               headerNew+=f"{colNew}{delimiter}"
     #          headerNew+=f"{colNew},"

            else:
                
                logger2.error(f"Column mis-match for column :{col}:",extra={"s4x4":w4x4})
                logger2.error(f"Transform Failed....Transform Failed",extra={"s4x4":w4x4})
                sys.exit(1)
        headerNew=headerNew.strip(delimiter)
    #    headerNew=headerNew.strip(",")


        fout.write(f"{headerNew}\n")
        for line in fin:
          #  spl=line.split(delimiter)
          #  lineNew= ",".join(spl)
          #  fout.write(f"{lineNew}\n")
            line=line.strip("\n")
            fout.write(f"{line}\n")

        fout.close()
        fin.close()


#print(df.shape)

# for col in df.columns:
#     if col not in fieldXrefs:
#         print("Error ",col)
        
# df.rename(columns=fieldXrefs,inplace=True)
# df.to_csv(f'{dirTarget}/{outFile}',index=False)


# %%
