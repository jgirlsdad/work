import pandas as pd
import sys
import argparse
import os.path
bic_etl_home = os.getenv('bic_etl_home')
## Add the bic_etl/general/script directory to path 
sys.path.insert(0, os.path.join(bic_etl_home, 'general', 'scripts'))
import custom_log
import jcLib

## Parse Input Arguments
parser = argparse.ArgumentParser(description='Clean the raw Boulder Septic Data File')
parser.add_argument('-i', '--inputFile', help='-i is the option for adding the input file name, in "" and inluding extension')
parser.add_argument('-t', '--title', help='-t is the dataset title')

parser.add_argument('-w', '--w4x4', help='-w is the CIM 4x4 identifier of the dataset')
args, leftovers = parser.parse_known_args()


w4x4 = args.w4x4
print("4x4",w4x4)           

## Logger
# logger = custom_log.setup(args.title)
# logger.info("Starting: Septic Systems in Boulder County Colorado")


logger2 = custom_log.setupNew(args.title)
logger2.info("Starting: Septic Systems in Boulder County Colorado",extra={"s4x4":w4x4})


## Input and Output Files
inputFile = args.inputFile
inputPathFile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data_source', inputFile)
b = inputFile.split(".")
outputFile = f"{b[0]}_cleaned.{b[1]}"
outputPathFile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data_source', outputFile)


print("reading files: ",inputPathFile)
print("writing  files: ",outputPathFile)



##  Main Program
septicOrig = pd.read_csv(inputPathFile,encoding="latin")

nrowsOrig = septicOrig.shape[0]

colsOrig = list(septicOrig.columns)

logger2.debug(f'Unique Zips before cleaning: {septicOrig["ZipCode"].nunique()}',extra={"s4x4":w4x4}) 

logger2.debug(f'# of ZipCode records that contain "-" {septicOrig.loc[(~septicOrig["ZipCode"].isna()) & (septicOrig["ZipCode"].str.contains("-"))].shape[0]}',extra={"s4x4":w4x4})

logger2.debug(f'# of ZipCode records > 5 characters: {septicOrig.loc[(~septicOrig["ZipCode"].isna()) & (septicOrig["ZipCode"].str.len() > 5)].shape[0]}',extra={"s4x4":w4x4})
logger2.debug(f'# of ZipCode records < 5 characters: {septicOrig.loc[(~septicOrig["ZipCode"].isna()) & (septicOrig["ZipCode"].str.len() < 5)].shape[0]}',extra={"s4x4":w4x4})

def fixZip(row):
    
    zipCode = row["ZipCode"]
    if pd.isna(zipCode):
        return zipCode
    else:
        zipCode = str(zipCode)[0:5]
    
    return zipCode
        
septicOrig["ZipCode"] = septicOrig.apply(fixZip,axis=1)

logger2.debug(f'# of Unique ZipCodes after Cleaning {septicOrig["ZipCode"].nunique()}',extra={"s4x4":w4x4})

a = septicOrig.loc[septicOrig.duplicated(subset=['B1_ALT_ID'],keep=False)]

logger2.debug(f'# of B1_ALT_ID with one or more duplicates {a["B1_ALT_ID"].nunique()}',extra={"s4x4":w4x4})
logger2.debug(f'Total # of duplicate records: {a.shape[0]}',extra={"s4x4":w4x4})

## Drop duplicates, keep the first duplicate record found
septicOrig.drop_duplicates(subset=['B1_ALT_ID'],keep="first",inplace=True)
nrowsNew = septicOrig.shape[0]

logger2.debug(f"# of Original records: {nrowsOrig}",extra={"s4x4":w4x4})
logger2.debug(f"# of Records after duplicate removal {nrowsNew}",extra={"s4x4":w4x4})
logger2.debug(f"# duplicated removed: {nrowsOrig-nrowsNew}",extra={"s4x4":w4x4})

##  Change column names to camel case
cols = {"B1_APPL_STATUS":"b1ApplStatus",
"B1_APP_TYPE_ALIAS":"b1AppTypeAlias",
"B1_ALT_ID":"b1AltId",
"TypeofSystem":"typeOfSystem",
"DwellingType":"dwellingType",
"AreaofLot":"areaOfLot",
"Bedrooms":"bedrooms",
"LimitingLayer":"limitingLayer",
"treatmentDepth":"treatmentDepth",
"InstallerName":"installerName",
"InstallingFirm":"installingFirm",
"EngineerName":"engineerName",
"EngineeringFirm":"engineeringFirm",
"AddressNumber":"addressNumber",
"StreetDirection":"streetDirection",
"StreetName":"streetName",
"StreetSuffix":"streetSuffix",
"b1_UNIT_START":"b1UnitStart",
"City":"city",
"ZipCode":"zipCode"}


septicOrig.rename(columns=cols,inplace=True)

## Column Check



colsConv = list(septicOrig.columns)




jcLib.checkFields(colsOrig,w4x4,logger2)


## Output new datafile
print(f"Output File : {outputPathFile} ")  # for the etl gui

septicOrig.to_csv(outputPathFile,index=False)



