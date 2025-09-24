import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def getFields(w4x4=""):
    '''Reads the Inventory google sheet and getsthe fields by 4x4 dataset id and by the title'''

    
    scope = ['https://www.googleapis.com/auth/spreadsheets.readonly',
             "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name('../client_secret.json',
     scope)
    client = gspread.authorize(creds)

    fields_sheet = client.open('BIC Data Inventory and Metadata').worksheet(
        'Field Descriptions')
    

    dfFields = pd.DataFrame(fields_sheet.get_all_records(head=1))
    fields = {}
    print("Only : ",w4x4)
    for index,row in dfFields.iterrows():
        
        s4x4 = row["Socrata ID"].strip()
        if len(w4x4) > 0 and s4x4 != w4x4:
            continue
        
        of = row["Source Field Name"]
        tf = row["Full Field Name"]
        af = row["API Field Name"]
        if s4x4 in fields:
            fields[s4x4]["source"].append(of)
            fields[s4x4]["cim"].append(tf)
            fields[s4x4]["api"].append(af)
        else:
            fields[s4x4] = {}
            fields[s4x4]["source"] = []
            fields[s4x4]["cim"] = []
            fields[s4x4]["api"] = []
            
            fields[s4x4]["source"].append(of)
            fields[s4x4]["cim"].append(tf)
            fields[s4x4]["api"].append(af)   
    return fields