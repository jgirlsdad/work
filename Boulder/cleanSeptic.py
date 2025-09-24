#!/usr/bin/env python
# coding: utf-8

# In[20]:


import pandas as pd
import sys
# sys.path.insert(0, 'Z:\\mnt\\c\\users\\cojoe\\Python-Stuff')
# import JCLib

pd.set_option('display.max_rows', 500)

pd.set_option('display.max_columns', None)


# ## Septic Systems

# ### Read Original Data

# In[21]:



septicOrig = pd.read_csv("~/bic_etl/boulder/data_source/Septic_Export_from_Accela.csv",encoding="latin")


# In[22]:


nrowsOrig = septicOrig.shape[0]
septicOrig.shape


# In[23]:


septicOrig.columns


# In[24]:


print(f'Unique Zips before cleaning: {septicOrig["ZipCode"].nunique()}') 


# In[25]:


print(f'# of ZipCode records that contain "-" {septicOrig.loc[(~septicOrig["ZipCode"].isna()) & (septicOrig["ZipCode"].str.contains("-"))].shape[0]}')


# In[26]:


print(f'# of ZipCode records > 5 characters: {septicOrig.loc[(~septicOrig["ZipCode"].isna()) & (septicOrig["ZipCode"].str.len() > 5)].shape[0]}')
print(f'# of ZipCode records < 5 characters: {septicOrig.loc[(~septicOrig["ZipCode"].isna()) & (septicOrig["ZipCode"].str.len() < 5)].shape[0]}')


# In[27]:


def fixZip(row):
    
    zipCode = row["ZipCode"]
    if pd.isna(zipCode):
        return zipCode
    else:
        zipCode = str(zipCode)[0:5]
    
    return zipCode
    
    
    
septicOrig["ZipCode"] = septicOrig.apply(fixZip,axis=1)


# In[28]:


print(f'# of Unique ZipCodes after Cleaning {septicOrig["ZipCode"].nunique()}')


# ## Duplicates

# In[29]:


a = septicOrig.loc[septicOrig.duplicated(subset=['B1_ALT_ID'],keep=False)]


# In[30]:


print(f'# of B1_ALT_ID with one or more duplicates {a["B1_ALT_ID"].nunique()}')
print(f'Total # of duplicate records: {a.shape[0]}')


# In[31]:


## Drop duplicates, keep the first duplicate record found
septicOrig.drop_duplicates(subset=['B1_ALT_ID'],keep="first",inplace=True)
nrowsNew = septicOrig.shape[0]


# In[32]:


print(f"# of Original records: {nrowsOrig}")
print(f"# of Records after duplicate removal {nrowsNew}")
print(f"# duplicated removed: {nrowsOrig-nrowsNew}")


# In[34]:


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


# In[35]:


septicOrig.rename(columns=cols,inplace=True)


# In[36]:


for col in septicOrig.columns:
    print(col)


# In[38]:


septicOrig.to_csv("~/bic_etl/boulder/data_transformed/Septic_Export_from_Accela_cleaned.csv",index=False)


# In[ ]:




