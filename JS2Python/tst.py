import os,sys
import json,csv,math
import argparse
import os.path
bic_etl_home = os.getenv('bic_etl_home')
## Add the bic_etl/general/script directory to path 
sys.path.insert(0, os.path.join(bic_etl_home, 'general', 'scripts'))
import custom_log
#import jcLib
from jcLib import checkMissing
# import gspread
# from oauth2client.service_account import ServiceAccountCredentials

## Parse Input Arguments
parser = argparse.ArgumentParser(description='generic BIC transform script')
parser.add_argument('-t', '--title', help='-t is the dataset title')
parser.add_argument('-w', '--w4x4', help='-w is the CIM 4x4 identifier of the dataset')
args, leftovers = parser.parse_known_args()
print(args)