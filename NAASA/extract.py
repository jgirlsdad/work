#!/usr/bin/env python
# coding: utf-8

# # IRS EXEMPT ORGANIZATIONS BUSINESS MASTER FILE EXTRACT

# So the IRS nicely provide a file of Exempt Organizations for just Colorado.  So, what we can to do is extract out just the non-profits realted 
# to Art, Culture and Humanities.  This is fairly straight forward, because we can the NTEEE Code column.  All of those codes that start with an A are what we needed (taken from the eo_info.pdf file provided).  

# As is often the case, this turns out to be not quite as straight forward.  So there are 34,211 total records and 9,700 do not have an NTEE code, about 28%. There are 2,171 non-profits related to the Arts, or about 6%. If roughly that amount (6%) of the 9,700 are also related to Art, then we would be missing about 580 non-profit.

# So we peformed a word-analysis of the  Names of the existing non-profit and try and extract out entitites out of the 9,700 w/o a NTEE code.  This is described below..
# We were able to add more than 200 non-profits to the list.  Visual inspection of the 200 confirmed this seemed reasonable.  The NTEE codes was NOT changed on these, so they are easily identifiable. That gave us a final total count of 2,384

# The only other changes to the data were to make the columns names Camel Case.  

# No Actual Data was changed and ALL columns and data were kept for the entitities related to Arts, Culture and Humanities

import pandas as pd
import io
import requests
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)


##  Read in Original data
#df = pd.read_csv("data/eo_co.csv")
url = "https://www.irs.gov/pub/irs-soi/eo_co.csv"
s = requests.get(url).content
df = pd.read_csv(io.StringIO(s.decode('utf-8')))

##  What does it look like
df.shape

## Lets see it
#  Get just the Arts Non-Proifits (NTEE Code starts with A)
dfArts = df.loc[(df["NTEE_CD"].notna()) & (df["NTEE_CD"].str.contains("^A"))]

# ## Recover NoN-Profits from Entities with No NTEE Code

# So there are 34,211 total records and 9,700 do not have an NTEE code, about 28%.  There are 2,171 non-profits related to the Arts, or about 6%.  If roughly that amount (6%) of the 9,700 are also related to Art, then we would be missing about 580 non-profit. 
# 
# To try and account for some of these, a word-analysis was performed on Names of the 2,171 Art related non-profits to see if we could come up with a list of words in the names of the Art ones to maybe cull as many as possible out of the 9,700.   The word-analsis was a manual inspection.  It is likely possible to use NLP processing to automate this or do a more accurate job, but for now, I will just use the manual list.  
# 
# The list of words used is: "ARTS","MUSEUM","MUSIC","THEATRE","ART","DANCE","ORCHESTRA","BALLET","BAND","CHORALE",            "SYMPHONY","ENSEMBLE","JAZZ","FILM","ARTISTS","CULTURE","OPERA","CHOIR","EDUCATION","CONCERT","ARTIST","CHORAL","PHILHARMONIC","SINGERS","LEARNING","CHORUS","STORYTELLERS","STORYTELLERS","STORYTELLERS","QUILTERS","DRUMS","GALLERY"
# 
# So, if any of these words are in the Names of the 9,700 without an NTEE code, they were extracted and added to the Art related non-profits.  Note that teh NTEE was NOT CHANGED.  This way, they can be easily identified. 

## extract out the records with no NTEE code

dfNoNtee = df.loc[df["NTEE_CD"].isna()]

## Need to break down the sentences into individual words, then explode each of these words so we can easily do our search
dfNoNteeExpl = dfNoNtee.copy()  # make a copy...we need to use dfNoNtee again later
## split each word in the name, and store the results back into NAME, which will now hold a list
dfNoNteeExpl["NAME"] = dfNoNteeExpl["NAME"].str.split()
##  Explode out the list in NAME..this will create a new row for each word in NAME 
dfNoNteeExpl = dfNoNteeExpl.explode("NAME")

## Use this if you want to see all the words we found
## dfNoNteeExpl["NAME"].value_counts()

## Now, cross reference all of teh words in the NAME column against our list from above, and store the EIN numbers we found
## 
eins = dfNoNteeExpl.loc[(dfNoNteeExpl["NAME"].isin( ["ARTS","MUSEUM","MUSIC","THEATRE","ART",
                                                                              "DANCE","ORCHESTRA","BALLET","BAND","CHORALE",
                                              "SYMPHONY","ENSEMBLE","JAZZ","FILM","ARTISTS","CULTURE","OPERA","CHOIR","CONCERT",
"ARTIST","CHORAL","PHILHARMONIC","SINGERS","CHORUS","STORYTELLERS",
"QUILTERS","DRUMS","GALLERY","PERCUSSION","CULTURES","MUSICA","FLAMENCO","KNITTING","ENTERTAINMENT","METALSMITHING","ACTORS","CRAFTS",
"MUSE","SCULPTURE","STRINGS","CREATIVES","GARDENS","INSTRUMENTAL","ARTISTRY","DANCERS","SONG","PIANO","BRASS","ACOUSTIC","BOOKS",
"LIBRARY","CONSERVATORY","MUSEUMS","MUSICIANS","GUITAR","WRITING", "MUSICAL","IRISH","CONCERTS"])),"EIN"].to_list()


##  This shows all the record we found
## dfNoNtee.loc[dfNoNtee["EIN"].isin(eins)]
dfNoNtee.loc[dfNoNtee["EIN"].isin(eins),"TAX_PERIOD"].value_counts()
#dfNoNtee.loc[dfNoNtee["EIN"].isin(eins),"RULING"].value_counts()

dfNoNtee.loc[dfNoNtee["EIN"].isin(eins)].shape

##  If you want to see the recovered records
## display(dfNoNtee.loc[dfNoNtee["EIN"].isin(eins)])


# ## Merge In Recovered  Non-profits 

## Big Step... Add all the ones we found to the dfArts dataframe
dfArts = pd.concat([dfArts,dfNoNtee.loc[dfNoNtee["EIN"].isin(eins)]])

dfArts.shape

## No duplicate EIN numbers... that is a good sign
dfArts["EIN"].nunique()

# do we have new ones at the end?
dfArts.tail()

## Replace the % sign in the ICO String name with nothing
dfArts["ICO"] = dfArts["ICO"].replace("\%","",regex=True)

# ## Change Column Names

# Ok, we have to deal with the hideous column names.  Change the All Cap column names to camel Case:

## Lets see the columns
dfArts.columns

## Convert column names to lower case
dfArts.columns = dfArts.columns.str.lower()


## How did that go
dfArts.columns

## Make CamelCase where needed
dfArts.rename(columns={ 'tax_period':'taxPeriod', 'asset_cd':'assetCd', 'income_cd':'incomeCd', 'filing_req_cd':'filingReqCd',
       'pf_filing_req_cd':'pfFilingReqCd', 'acct_pd':'acctPd', 'asset_amt':'assetAmt', 'income_amt':'incomeAmt', 'revenue_amt':'revenueAmt',
       'ntee_cd':'nteeCd', 'sort_name':'sortName'},inplace=True)

## Last check 
dfArts.columns


# ## Output Data

## Write output file, with No Index
dfArts.to_csv("data/eoCoArts.csv",index=False)