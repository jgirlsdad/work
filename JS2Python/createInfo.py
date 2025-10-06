#!/usr/bin/env python
# coding: utf-8

# # Create Info

# This programs was used to create the comparison statistics when we removed all the transformations from the CDOS Datasets.  It compares a data file with the transformations to a new data file with the transformations removed.  This is not trivial and lots of different complications can arise.  The programs does a record to record, then field to field comparison, so the trick is making certain the correct 2 recrods are being compared.  Some of the datasets have a unique set of identifiers that can be used (like entity id, document id,...) that can be combined for unique single occurances.  However, this appeared to be rare.  The other, more common option, was to sort both datasets using the unix sort before running the program, the comparing the 2 sorted files.  This works well, but occassionaly there are 2 records that are not exact duplicates, but close, and they might be slightly out of order, however, this does not appear to cause too many issues, outside of a few spurious cases of records failing the analysis (i.e. elevated bad counts)

# In[2]:


import sys
import argparse
import os.path,inspect
bic_etl_home = os.getenv('bic_etl_home')
## Add the bic_etl/general/script directory to path 
sys.path.insert(0, os.path.join(bic_etl_home, 'general', 'scripts'))
import pandas as pd
import re
import csv
import datetime
import urllib.request as urllib
import urllib.request as urlRequest
import json
#from sodapy import Socrata
import json
import os

pd.set_option('display.max_rows', 1500)
pd.set_option('display.max_columns', None)


# ### Change Type Cross Refs

# In[3]:


##  This is used as a lookup table for the types of transformations we were performing.  As we were 
##  transforming the original source fields, that is what is put in the lists/dicts below.  THen, you provide the 
##  source-transform dictionary and these field names will be converted to the CIM field names in the reports.  One 
##  reason for doing it this way, and not using the CIM field names in the lists/dict below is this serves as a secondar
##  check of the source-transform xref dictionary.  
##
##  The lists/dict are then converterted to the appropriate flags that indicate what type of transformation was being
##  performed.

## Current Notaries in Coloarod
xrefUse=False
caps = []


bools = []

cities = []

zips =  []

removeChars  = {"lastname":"/"}
#
removeColumns = []

phones = []

web = []

dates = []

empty = []


xrefs = {} 
for col in caps:
    xrefs[col]="A"

for col in zips:
    xrefs[col]="B"

for col in bools:
    xrefs[col]="C"

for col in phones:
    xrefs[col]="D"

for col,val in removeChars.items():
    xrefs[col] = f"E ({val})"

for col in web:
    xrefs[col]="F"

for col in dates:
    xrefs[col]="G?"

for col in cities:
    xrefs[col]="H"

for col in empty:
    xrefs[col]="I"


## A source-transform xreference dictionary is needed b/c above, the field names abpve  are given as source fields, but
## we want to convert those to transform (CIM) field names for the reports and web pages.  This requirement could be 
## removed by using the transform field names above.  I did this as a check of the source-transform cross references
## and a way to kind of check if the old transforms were outputting the correct field name to CIM

#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/reg_finan_37wu-kn3g_src_trns_xrefs.json")

#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/persons_entity_mr4v-jz8u_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/purpose_7jm9-f28m_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/states_5wyf-xqw7_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/offices_3qtu-edua_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/sn_cmpgn_rpts_fdcw-ei67_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/sol_ntcs_locs_wwhd-vg25_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/sol_ntcs_locs_wwhd-vg25_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/char_orgs_ext_icqv-mi3c_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/sol_typ_entity_w6kb-3vsj_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/doing_bus_as_q2av-rpr5_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/char_orgs_sol_wwbh-7bpa_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/nonprofit/defs/tax_exempt_cds_2z9k-uy4q_src_trns_xrefs.json")
#fin = open("/home/joe/bic_etl/cdos/business/business/defs/bus_trns_casm-dbbj_src_trns_xrefs.json")
dateCols = []  # used to identify columns with dates later in the analysis  
if xrefUse:
  #  dateCols = []  # used to identify columns with dates later in the analysis
    xx = json.load(fin)
    w4 = list(xx.keys())[0]
    print("4x4: ",w4) 
    xrefs2={}
    for col,val in xrefs.items():
        xrefs2[xx[w4][col]['xref']]=val
        if val == "G?":
            dateCols.append(xx[w4][col]['xref'])
else:
    xrefs={}


# ## Functions

# In[ ]:
import sys

def top_vars(scope, n=10):
    """Show the largest objects in a scope (globals/locals) with names."""
    sizes = []
    for name, obj in scope.items():
        try:
            sizes.append((sys.getsizeof(obj), name, type(obj)))
        except Exception:
            pass
    for size, name, typ in sorted(sizes, reverse=True)[:n]:
        print(f"{name:<20} | {typ} | {size/1024:.2f} KB")


def getOpts(opts):
    ''' This is used to decipher the options input in the extract and transform sections of the run_etl.json files '''
    spl=opts.split(",")
    ops = {}
    for opt in spl:
       k,v = opt.split("=")   
       if v.isdigit():
          v=int(v)
       else:
          v=v.replace("'","")

       ops[k]=v
    return ops

###################################################################################################

def createStats(fileO,fileT,optsOOp,optsORd,optsTOp,optsTRd):
    ''' This is the first attempt at creating the stats and was used for some/most of the cods/business 
    datasets. I keep this in case we need to cross-reference and update the business datasets using the later functionality
    This does NOT assign the change type categories that we used for later datasets and replaced by createStatsSequentialNew
    '''
    print("Processing First File")
    dOOp={}
    if len(optsOOp) > 0: 
        dOOp = getOpts(optsOOp)
        print("dOOp ",dOOp)
    fO = open(fileO,**dOOp)

    dORd={}
    if len(optsORd) > 0: 
        dORd = getOpts(optsORd)
        print("dORd ",dORd)
    readerO = csv.DictReader(fO,**dORd)  

    linesOrg=[]
    for line in readerO:
        linesOrg.append(line)
    fO.close()  
    print(f"Read {len(linesOrg)} records in first file")


    print("Processing Second file") 
    dTOp={}
    if len(optsTOp) > 0: 
        dTOp = getOpts(optsTOp)
        print("dTOp ",dTOp)
    fT = open(fileT,**dTOp)

    dTRd={}
    if len(optsTRd) > 0: 
        dTRd = getOpts(optsTRd)
        print("dTRd ",dTRd)
    readerT = csv.DictReader(fT,**dTRd)  

    linesTrn=[]
    for line in readerT:
        linesTrn.append(line)
    fT.close()        
    print(f"Read {len(linesTrn)} records in second file")


# Analyze files 
    print("Analyze Data")
    hist={}
    nbad=0
    total=0
    bads={}
    for nn,rowO in enumerate(linesOrg):
       total+=1
       rowT = linesTrn[nn]
       for colO,valO in rowO.items():

           valT = rowT[colO]
           if colO in hist: 
             hist[colO]["Total"]+=1
           else:
            hist[colO]={}
            hist[colO]["Total"]=1
            hist[colO]["Bad"]=0

           if valT != valO:
              nbad+=1
              hist[colO]["Bad"]+=1
              if colO not in bads:
                  bads[colO]={}
              if valO not in bads[colO]:
                 bads[colO][valO]=valT

              # if colO == "tradenameForm":
              #   print(nn,len(valO),len(valT),valO,valT)
    print("Finished")
    print("\nBad Columns")
    for col,dct in hist.items():
        if dct['Bad'] > 0 and col.lower().find("date") == -1:
            print(f"{col:30.30s}  {dct['Bad']:8d}")
    print("\n----------------\n")
    return hist,bads,total,linesOrg,linesTrn

############################################################################

def createHTML(link,title,hist,dateHist,notes,codes,tol,bads):
    ''' This creates the HMTL page.  It does NOT write an output file.  It returns the page as 1 long string.
    The input for this function is the output from the one of the stats functions''' 
    # set up initial html for dataset block
    print("codes ",codes)
    print("LENS ",len(hist),len(dateHist))
    if len(dateHist) == 0:
        bad=False
        for col,dct in hist.items():
            for flag,dct2 in dct.items(): 
                if isinstance(dct2,dict) and dct2['Bad'] > tol and col.lower().find("date") == -1 and flag != "Total":
                    bad=True
        if bad == False:
            string=f'''
                <!-- Start {title} -->
                <button type="button" class="collapsible">{title}</button>
                <div class="content">
                <p><a href="{link}" target="_blank">{title}</a>
                </p>
                <p><b>Notes</b><br>{notes}


            <!-- End {title} -->\n\n
            <p></p>'''

            print("NOTHINg FOUND NOTHING FOUND")
            return string



    string=f'''
    <!-- Start {title} -->

    <button type="button" class="collapsible">{title}</button>
    <div class="content">
    <p><a href="{link}" target="_blank">{title}</a>
    </p>
    <p><b>Notes</b><br>{notes}
    </p>
    <p>
    <table border="1" ">
        <tr style="text-align: center">
            <th>Field</th>
            <th>Change Type</th>
            <th># Records Affected</th>
            <th>Total Records</th>
            <th>% Records Affected</th>
        </tr>\n'''

    #  Create the table entries for each field
    badCols=[]
    for col,dct in hist.items():
        for flag,dct2 in dct.items(): 
            if isinstance(dct2,dict) and dct2['Bad'] > tol and col.lower().find("date") == -1 and flag != "Total":
         #   if dct['Bad'] > tol :
          #      print("Found Bad Col ",col,len(col),flag)
                badCols.append(col)
                pp = 100*dct2['Bad']/dct['Total']
                if col in codes:
                    cod=codes[col]
                else:
                    cod=""
                string+=f"    <tr style='text-align: center'><td>{col}</td><td>{flag}</td><td>{dct2['Bad']}</td><td>{dct['Total']}</td><td>{pp:5.1f}</td></tr>\n"

    for col,dct in dateHist.items():
        hit=0
        if dct["Date Good"] > 0:
            cod="G1"
            hit=1
            pp=100*dct["Date Good"]/dct["Total"]
            string+=f"    <tr style='text-align: center'><td>{col}</td><td>{cod}</td><td>{dct['Date Good']}</td><td>{dct['Total']}</td><td>{pp:5.1f}</td></tr>\n"
        if dct["No Good"] > 0 or dct["Just Bad"]["colOGR"] > 0:
            cod="G2"
            ng = dct["No Good"]
            ng+=dct["Just Bad"]["colOGR"]
            pp=100*ng/dct["Total"]
            if ng > 10:
               hit=1
               string+=f"    <tr style='text-align: center'><td>{col}</td><td>{cod}</td><td>{ng}</td><td>{dct['Total']}</td><td>{pp:5.1f}</td></tr>\n"
        if dct["Just Bad"]["colOG"] > 0:
            cod="G3"
            hit=1
            pp=100*dct["Just Bad"]["colOG"]/dct["Total"]
            string+=f"    <tr style='text-align: center'><td>{col}</td><td>{cod}</td><td>{dct['Just Bad']['colOG']}</td><td>{dct['Total']}</td><td>{pp:5.1f}</td></tr>\n"

        if hit > 0:
            badCols.append(col)

    string+='''        </table>
        </p>
        <button type="button" class="collapsible">Examples</button>
        <div class="content">
      '''


    # Write the Example Block and close out

    for col in badCols:
        print("Bad COL ",col)
        string+=f'''    <button type="button" class="collapsible">{col}</button>'''
        for flag in bads[col].keys():
         #   print("BADS ",col,flag)
            nrec=0 
            string+=f'''
              <div class="content">
                <table>
                    <tr>
                        <th>Old Record</th>
                        <th>New Record</th>
                    </tr>\n'''
            for valo,valt in bads[col][flag].items():
                string+= f"              <tr><td>{valo}</td><td>{valt}</td></tr>\n"
                nrec+=1
                if nrec > 10:
                    break

        string+='''
              </table>
            </div>\n'''

    string+=f'''
        </div>
    </div>\n

    <!-- End {title} -->\n\n
    <p></p>'''
    return string

 #   op = open(f'{dirTarget}/{inFile}','r',**d)
##############################################################################################

def createStatsSerial(fileO,fileT,optsOOp,optsORd,optsTOp,optsTRd):
    ''' Second attempt at computing stats which assumes the records for the datasets are in teh same seriel order, 
    which for many datasets turned out not to be true.  This was used for atleast 1 dataset, so I keep it in case I 
    need to update that dataset with the new methods.  This does NOT assign the change type categories that we used 
    for later datasets and replaced by createStatsSequentialNew
    '''
    print("Processing First File")
    dOOp={}
    if len(optsOOp) > 0: 
        dOOp = getOpts(optsOOp)
        print("dOOp ",dOOp)
    fO = open(fileO,**dOOp)

    dORd={}
    if len(optsORd) > 0: 
        dORd = getOpts(optsORd)
        print("dORd ",dORd)
    readerO = csv.DictReader(fO,**dORd)  

#     linesOrg=[]
#     for line in readerO:
#         linesOrg.append(line)
#     fO.close()  
#     print(f"Read {len(linesOrg)} records in first file")


    print("Processing Second file") 

    dTOp={}
    if len(optsTOp) > 0: 
        dTOp = getOpts(optsTOp)
        print("dTOp ",dTOp)
    fT = open(fileT,**dTOp)

    dTRd={}
    if len(optsTRd) > 0: 
        dTRd = getOpts(optsTRd)
        print("dTRd ",dTRd)
    readerT = csv.DictReader(fT,**dTRd)  



#     linesTrn=[]
#     for line in readerT:
#         linesTrn.append(line)
#     fT.close()        
#     print(f"Read {len(linesTrn)} records in second file")


# Analyze files 
    print("Analyze Data")
    hist={}
    nbad=0
    total=0
    bads={}
    for rowO in readerO:
       total+=1
  #     rowT = linesTrn[nn]
       try:
           rowT = next(readerT)
           if total%100000 == 0:
                print(total)

           for colO,valO in rowO.items():

               valT = rowT[colO]
               if colO in hist: 
                 hist[colO]["Total"]+=1
               else:
                hist[colO]={}
                hist[colO]["Total"]=1
                hist[colO]["Bad"]=0

               if valT != valO:
                  nbad+=1
                  hist[colO]["Bad"]+=1
                  if colO not in bads:
                      bads[colO]={}
                  if valO not in bads[colO]:
                     bads[colO][valO]=valT

                  # if colO == "tradenameForm":
                  if hist[colO]["Bad"] < 20:
                     print(total,colO,len(valO),len(valT),valO," :: ",valT)
       except Exception as err:
            print("ERR ",err)
            print("STOPPING STOPPING")
            print(hist)
            break
    print("Finished")
    print("\nBad Columns")
    for col,dct in hist.items():
        if dct['Bad'] > 0 and col.lower().find("date") == -1:
            print(f"{col:30.30s}  {dct['Bad']:8d}")
    print("\n----------------\n")
    return hist,bads,total

############################################################################

def createStatsSerialNew(fileO,fileT,optsOOp,optsORd,optsTOp,optsTRd,howO,howT,caseO,caseT):
    ''' An upgrate toe createStatSerial.  Used for atleast 1 dataset.  This function does not 
    categorize changes by type and is replaced by createStatsSequentialNew '''
    print("Processing First File")
    yesno = {}   #  contains columns that have Yes,Y,No,N as answers; for checking on CIM
    if howO == "L":
        dOOp={}
        if len(optsOOp) > 0: 
            dOOp = getOpts(optsOOp)
            print("dOOp ",dOOp)
        fO = open(fileO,**dOOp)

        dORd={}
        if len(optsORd) > 0: 
            dORd = getOpts(optsORd)
            print("dORd ",dORd)
        readerO = csv.DictReader(fO,**dORd)  

    elif howO == "W":   #  read web file
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"}
        req = urlRequest.Request(f"{fileO}?$limit=999999999", headers = headers)
        x = urlRequest.urlopen(req)
        sourceCode = x.read()
        sourceCode=sourceCode.decode("utf-8")
        readerO = csv.DictReader(sourceCode.splitlines())        

#     linesOrg=[]
#     for line in readerO:
#         linesOrg.append(line)
#     fO.close()  
#     print(f"Read {len(linesOrg)} records in first file")


    print("Processing Second file") 
    if howT == "L":  #  read local file
        dTOp={}
        if len(optsTOp) > 0: 
            dTOp = getOpts(optsTOp)
            print("dTOp ",dTOp)
        fT = open(fileT,**dTOp)

        dTRd={}
        if len(optsTRd) > 0: 
            dTRd = getOpts(optsTRd)
            print("dTRd ",dTRd)
        readerT = csv.DictReader(fT,**dTRd)  
    elif howT == "W":   #  read web file
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"}
        req = urlRequest.Request(f"{fileT}?$limit=999999999", headers = headers)
        x = urlRequest.urlopen(req)
        sourceCode = x.read()
        sourceCode=sourceCode.decode("utf-8")
        readerT = csv.DictReader(sourceCode.splitlines())        

#     linesTrn=[]
#     for line in readerT:
#         linesTrn.append(line)
#     fT.close()        
#     print(f"Read {len(linesTrn)} records in second file")


# Analyze files 
    print("Analyze Data")
    hist={}
    nbad=0
    total=0
    bads={}
    misses={}
    for rowO in readerO:
       total+=1
       if total > 10000:
              break
  #     rowT = linesTrn[nn]
       if total == 1:
           columns=list(rowO.keys())
       try:
           rowT = next(readerT)
           # if total < 10:
           #     print(rowO)
           #     print("---------------------")
           #     print(rowT)
           #     print("---------------------")

           if caseT.lower() == "l":   # convert keys to lower case
               rowTNew={}
               for key,val in rowT.items():
                   if isinstance(key,str):
                       keyN=key.lower()
                   else:
                       keyN=key
                   rowTNew[keyN]=val
               rowT=rowTNew


           if total%100000 == 0:
                print(total)
       #    print("ROW T",rowT)
           for colOO,valO in rowO.items():
               if caseO.lower() == "l": # make it lower case
                   colO = colOO.lower()
               else:
                   colO=colOO

               if colO in rowT:
                   valT = rowT[colO]
                   if colO in hist: 
                     hist[colO]["Total"]+=1
                   else:
                    hist[colO]={}
                    hist[colO]["Total"]=1
                    hist[colO]["Bad"]=0

                   if isinstance(valO,str) and valO.strip().lower() in ["y","n","yes","no"]:
                      if colO not in yesno:
                            yesno[colO]=0
                      yesno[colO]+=1


                   if valT != valO:
                      nbad+=1
                      hist[colO]["Bad"]+=1
                      if colO not in bads:
                          bads[colO]={}
                      if valO not in bads[colO]:
                         bads[colO][valO]=valT

                      # if colO == "tradenameForm":
                      if hist[colO]["Bad"] < 20:
                         print(total,colO,len(valO),len(valT),valO," :: ",valT)
               else:
                    misses[colO]=1


       except Exception as err:
            print("ERR ",err)
            print("STOPPING STOPPING")
            print("O Cols",rowO.keys(),"\n")
            print("T Cols",rowT.keys(),"\n")

            print(hist)
            break
    print("Finished")
    print("\n----------------\n")

    print("\nBad Columns")
    for col,dct in hist.items():
        if dct['Bad'] > 0 and col.lower().find("date") == -1:
            print(f"{col:30.30s}  {dct['Bad']:8d}")
    print("\n----------------\n")
    print("\n-------------------------------")
    print("COLUMNS WITH YES/NO ANSWERS")
    print("COLUMNS WITH YES/NO ANSWERS")
    for col,cnt in yesno.items():
        print(col,cnt)
    if len(yesno) == 0:
        print("NO YES/NO Columns in Source Dataset")

    print("\n-------------------------------")
    if len(misses):
        print("SOURCE COLUMNS NOT FOUND IN OLD TRANSFORMED DATA")
        for col in misses:
            print(col)
        print("\n--------------------------------")
    return hist,bads,total,columns,yesno

#################################################################

def is_number(s):
    ''' returns True if input is a number and False if it is not a number '''
    try:
        float(s)
        return True
    except ValueError:
        return False

##############################################

def isn(s):
    ''' If s is a float, returns True and s as a float.  If s is an integer it return True and s as an int.  
    Otherwise, it returns False and just returns s
    ''' 
    try:
        float(s)
        if s.find(".") > -1:
           return True,float(s)
        else:
           return True,int(float(s))
    except Exception as err:

        return False,s


####################################################################

def exceptionLog(exception,funCall):
  ''' Returns the exception, the function in which it occurred and the line number '''
  exception_message = str(exception)
  exception_type, exception_object, exception_traceback = sys.exc_info()
  filename = os.path.split(exception_traceback.tb_frame.f_code.co_filename)[1]
  print(f"{exception_message} {exception_type} {funCall}, Line {exception_traceback.tb_lineno}")

####################################################################

def createStatsSequentialNew(xrefCols,fileO,fileT,optsOOp,optsORd,optsTOp,optsTRd,dateCols,xrefs,howO,howT,caseO,caseT):
    ''' The final stats program for datasets where the 2 files are in sequential order.  This function categorizes
    the differences by type of change.  
    The function 2 files that have mostly the same field names and looks for differences in each variable.  If you
    provide a list of the date fields in dateCols, then they will be compared as dates and not strings.  
    optsOOp and optsORd let you pass in directives for opening the 1st file and optsTOp and optsTRd let you pass
    in directives for opening the 2nd file.  howO and howT let you indicate wither you are reading a local file
    or web address.  caseO and caseT allow you to control the case of the fields names for analysis. (If reading an 
    API web address, the all field names will be lower-case, so you might need to tell the fuction to treat the other 
    files fields names as lower case. 
    '''

    print("Processing First File")
    yesno = {}   #  contains columns that have Yes,Y,No,N as answers; for checking on CIM
    if howO == "L":
        dOOp={}
        if len(optsOOp) > 0: 
            dOOp = getOpts(optsOOp)
            print("dOOp ",dOOp)
        fO = open(fileO,**dOOp)



        dORd={}
        if len(optsORd) > 0: 
            dORd = getOpts(optsORd)
            print("dORd ",dORd)
        readerO = csv.DictReader(fO,**dORd)  

        print("HEADER O ",readerO.fieldnames)
    elif howO == "W":   #  read web file
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"}
        req = urlRequest.Request(f"{fileO}?$limit=999999999", headers = headers)
        x = urlRequest.urlopen(req)
        sourceCode = x.read()
        sourceCode=sourceCode.decode("utf-8")
        readerO = csv.DictReader(sourceCode.splitlines())        

#     linesOrg=[]
#     for line in readerO:
#         linesOrg.append(line)
#     fO.close()  
#     print(f"Read {len(linesOrg)} records in first file")


    print("Processing Second file") 
    if howT == "L":  #  read local file
        dTOp={}
        if len(optsTOp) > 0: 
            dTOp = getOpts(optsTOp)
            print("dTOp ",dTOp)
        fT = open(fileT,**dTOp)
        dTRd={}
        if len(optsTRd) > 0: 
            dTRd = getOpts(optsTRd)
            print("dTRd ",dTRd)
        readerT = csv.DictReader(fT,**dTRd)  

    elif howT == "W":   #  read web file
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"}
        req = urlRequest.Request(f"{fileT}?$limit=999999999", headers = headers)
        x = urlRequest.urlopen(req)
        sourceCode = x.read()
        sourceCode=sourceCode.decode("utf-8")
        readerT = csv.DictReader(sourceCode.splitlines())  


# Analyze files 
    print("Analyze Data")
    hist={}
    nbad=0
    total=0
    bads={}
    badsT={}
    misses={}
    allLinesO={}
    allLinesT={}
    dateHist={}
    # dateCols = ['fiscalYearStartDate','fiscalYearEndDate','dateFormed','expirationDate','statusDate','authorizedOfficerSignedDate',
    #                            'cfoSignedDate','registrationApprovedDate','paymentProcessedDate','nextRenewalRegistrationDate']
    # dateCols= [ 'solicitationApprovedDate', 'paymentProcessedDate','campaignCommencementDate','campaignConclusionDate', 'charitySignedDate',
    #  'contractEffectiveDate','contractTerminationDate']
    for rowO in readerO:
 #      allLinesO[total]=rowO
       total+=1
       if total == 1:
           print("HEADER O ",readerO.fieldnames)
    #    if total > 400000:
    #        break
  #     rowT = linesTrn[nn]
       if caseO.lower() == "l":   # convert keys to lower case
   #        print("CONVERTING KEY CASEO",":",caseO.lower(),":")
           rowONew={}
           for key,val in rowO.items():
               if isinstance(key,str):
                   keyN=key.lower()
               else:
                   keyN=key
               rowONew[keyN]=val
           rowO=rowONew

       try:
     #      rowT = next(readerT)

           #eid = rowO["entityId"]

           rowT = next(readerT)
           if total == 1:
               print("HEADER T ",readerT.fieldnames)
    #       allLinesT[total-1]=rowT

           if total == 1:
              columns=list(rowO.keys())
              columnsT = list(rowT.keys())
           # if total < 10:
           #     # print(rowO)
           #     # print("---------------------")
           #     # print(rowT)
           #     print("---------------------")
           #     for k,v in rowO.items():
           #            print("HIT OOO ",k,v) 
           #     for k,v in rowT.items():
           #            print("HIT TTT ",k,v) 
           #     print("---------------------")
           #     print("O O O O ",rowO)
           #     print("T T T T ",rowT)

           if caseT.lower() == "l":   # convert keys to lower case
               rowTNew={}
               for key,val in rowT.items():
                   if isinstance(key,str):
                       keyN=key.lower()
                   else:
                       keyN=key
                   rowTNew[keyN]=val
               rowT=rowTNew


           if total%100000 == 0:
                print(total)
              #  top_vars(globals(), n=10)
       #    print("ROW T",rowT)

           for colOO,valO in rowO.items():
               if caseO.lower() == "l": # make it lower case
                   colO = colOO.lower()
               else:
                   colO=colOO

       #         if colO in xrefs:
       #            colT = xrefs[colO]
       # #           print("XREFS ",colO,colT)
       #         else:
       #            colT=colO 
               colT=colO
               if len(xrefCols) > 0: 
                   if colT in xrefCols:
                      colT=xrefCols[colT]


               if colT in rowT:
                   valT = rowT[colT]
                   if colO in hist: 
                     hist[colO]["Total"]+=1
                   else:
                     hist[colO]={}
                     hist[colO]["Total"]=1
               ##      hist[colO]["Bad"]=0

                   if isinstance(valO,str) and valO.strip().lower() in ["y","n","yes","no"]:
                      if colO not in yesno:
                            yesno[colO]=0
                      yesno[colO]+=1
                   # if total < 10:
                   #     print(type(valO),type(valT),valO,valT)
                   valO = valO.strip()
                   valT = valT.strip()
                   # if total < 3:
                   #     print(colO,colT,type(valO),valO,type(valT),valT)

                   aO,valO = isn(valO)
                   aT,valT = isn(valT)

          #         if is_number(valT) and is_number(valO):
           #       if aO and aT:
                       # valT=float(valT)
                       # valO=float(valO)
                       # if total < 10:
                       #     print("HIT HIT ",colO,colT,type(valT),type(valO))

                   if colO in dateCols: 
                       dateHit=False
                       valTs=valT
                       valOs=valO
                       if total < 1000:
                           print("DATe CHECK ",colO,colT,valO,valT)
                       if isinstance(valT,str) and isinstance(valO,str) and len(valT) > 9 and len(valO) > 9:
                           # if total < 10:
                           #     print("DTT",valT[:10])
                           # nt = len(valT)
                           # no = len(valO)
                           dt=valT
                           od=valO
                         # 12:00:00 AM
                         #  valT = datetime.datetime.strptime(valT[:10],"%Y-%m-%d")
                           try: 
                                valT = datetime.datetime.strptime(valT,"%m/%d/%Y %H:%M:%S %p")
                                valO = datetime.datetime.strptime(valO,"%m/%d/%Y %H:%M:%S %p")
                                valT = valT.date()
                                valO = valO.date()
                           except Exception as err:
                               print("Error parsing dates:", valO,valtT,err)
                               continue
                           if colO not in dateHist:
                              dateHist[colO] = {}
                              dateHist[colO]["Total"]=0
                              dateHist[colO]["All Good"]=0
                              dateHist[colO]["Date Good"]=0  
                              dateHist[colO]["No Good"]=0   
                              dateHist[colO]["Just Bad"]={}
                              dateHist[colO]["Just Bad"]["count"]=0

                              dateHist[colO]["Just Bad"]["colOG"]=0
                              dateHist[colO]["Just Bad"]["colOGR"]=0

                              dateHist[colO]["Just Bad"]["colTG"]=0
                              dateHist[colO]["Just Bad"]["both"]=0
                              dateHist[colO]["Just Bad"]["rohroh"]=0

                           if dt == od:
                              dateHist[colO]["All Good"]+=1

                           elif valT == valO:  # Simple formatting issues
                              dateHist[colO]["Date Good"]+=1
                              flag="G1"
                              dateHit=True 
                           else:   # Date replace with bad date 
                              dateHist[colO]["No Good"]+=1   
                              flag="G2"
                              dateHit=True
                           # if total < 10:
                           #     print("DQATE ",valO,valT)
                       else:
                            if colO not in dateHist:
                              dateHist[colO] = {}
                              dateHist[colO]["Total"]=0
                              dateHist[colO]["All Good"]=0
                              dateHist[colO]["Date Good"]=0  
                              dateHist[colO]["No Good"]=0   
                              dateHist[colO]["Just Bad"]={} 
                              dateHist[colO]["Just Bad"]["count"]=0
                              dateHist[colO]["Just Bad"]["colOG"]=0
                              dateHist[colO]["Just Bad"]["colOGR"]=0

                              dateHist[colO]["Just Bad"]["colTG"]=0
                              dateHist[colO]["Just Bad"]["both"]=0
                              dateHist[colO]["Just Bad"]["rohroh"]=0



                            dateHist[colO]["Just Bad"]["count"]+=1
                            # print("DATE CHK ",colO,valO," :: ",valT)
                            if len(valO) < 5 and len(valT) < 5: 
                                dateHist[colO]["Just Bad"]["both"]+=1
                            elif len(valO) > 9 and len(valT) < 5:  # date missing 
                               dateHist[colO]["Just Bad"]["colOG"]+=1
                               flag="G3"  
                               dateHit=True
                            elif len(valO) > 9 and len(valT) > 4: # date replace with month-day
                               dateHist[colO]["Just Bad"]["colOGR"]+=1
                               flag="G2"
                               dateHit=True
                            elif len(valT) > 9: 
                               dateHist[colO]["Just Bad"]["colTG"]+=1
                            else: 
                               dateHist[colO]["Just Bad"]["rohroh"]+=1

                       dateHist[colO]["Total"]+=1     
                       if dateHit:
                    #     print("BAD FLAG ",flag,valO," :: ",valT)
                         if colO not in bads:
                            bads[colO]={}
                         if flag not in bads[colO]:
                            bads[colO][flag]={}
                         if valOs not in bads[colO][flag]:
                            bads[colO][flag][valOs]=valTs

                   if valT != valO:
                      nbad+=1
             #         hist[colO]["Bad"]+=1
                      # if colO in dateCols: 
                      #     valT=valTs
                      #     valO=valOs
                      if colO not in dateCols:
                          # if colO not in bads:
                          #     bads[colO]={}
                          # if valO not in bads[colO]:
                          #    bads[colO][valO]=valT
                          if colO in xrefs:
                              flag=xrefs[colO]
                          else:
                             flag="None"
                          if colO == "city":
                              if valT.lower() == valO.lower():
                                  flag="A"
                              else:
                                  flag="H"
                          if flag not in hist[colO]:
                              hist[colO][flag]={}
                              hist[colO][flag]["Bad"]=0
                          hist[colO][flag]["Bad"]+=1

                          if colO not in bads:
                              bads[colO]={}
                          if flag not in bads[colO]:
                              bads[colO][flag]={}
                          if valO not in bads[colO][flag]:
                             bads[colO][flag][valO]=valT

                          if colO not in badsT:
                              badsT[colO]={}
                          if valT not in badsT[colO]:
                             badsT[colO][valT]={}
                             badsT[colO][valT]["value"] = valO
                             badsT[colO][valT]["count"]=1
                          else:
                             badsT[colO][valT]["count"]+=1

                      # if colO == "tradenameForm":
                          if hist[colO][flag]["Bad"] < 20:
                             print("Bad ",total,flag,colO,valO," :: ",valT)
               else:
                    misses[colO]=1
       except StopIteration:
           print("END OF FILE FOUND")
           print("END OF FILE FOUND")
           break
       except Exception as err:
            print("ERR ",err)
            print("COLUMN ",colO,valO)
  #         print("COLUMN ",colT,valT)
            print("STOPPING STOPPING")
            exceptionLog(err,inspect.currentframe().f_code.co_name)
            # print("O Cols",rowO.keys(),"\n")
            # print("T Cols",rowT.keys(),"\n")

            print(hist)
            break
    print("Finished")
    print("\n----------------\n")
    fO.close()
    fT.close()
    print("\nBad Columns")
    for col,dct in hist.items():
        for flag,dct2 in dct.items(): 
       #   print("D3 ",dct2)
    #    if dct['Bad'] > 0 and col.lower().find("date") == -1:
          if isinstance(dct2,dict) and dct2['Bad'] > 0:

            print(f"{col:30.30s}  {dct2['Bad']:8d}")

    print("\n----------------------------\n")
    print("Date Specific Counts")

    print("                        Column  All Good  Date Good  No Good          Just Bad     Both Bad     ColOG Good   ColTG Good    Both B ad")
    for col,dct in dateHist.items():
        print(f'{col:30.30s}  {dct["All Good"]:8d}  {dct["Date Good"]:8d}  {dct["No Good"]:8d}  \
        {dct["Just Bad"]["count"]:8d}  {dct["Just Bad"]["both"]:8d}   {dct["Just Bad"]["colOG"]:8d}   \
        {dct["Just Bad"]["colTG"]:8d}  {dct["Just Bad"]["rohroh"]:8d} {dct["Just Bad"]["colOGR"]:8d}')

    print("\n----------------\n")
    print("\n-------------------------------")
    print("COLUMNS WITH YES/NO ANSWERS")
    print("COLUMNS WITH YES/NO ANSWERS")
    for col,cnt in yesno.items():
        print(col,cnt)
    if len(yesno) == 0:
        print("NO YES/NO Columns in Source Dataset")

    print("\n-------------------------------")
    if len(misses):
        print("SOURCE COLUMNS NOT FOUND IN OLD TRANSFORMED DATA")
        for col in misses:
            print(col)
        print("\n--------------------------------")

    return hist,dateHist,bads,badsT,total,columns,columnsT,yesno,allLinesO,allLinesT





#######################################################################


def createStatsMisMatch(fileO,fileT,optsOOp,optsORd,optsTOp,optsTRd,dateCols,xrefs,howO,howT,caseO,caseT):
    ''' The final stats program for datasets where the 2 files arenot in sequential order AND there is a unique 
    combination of fields that can be used to identify each unique recrod.  
    This function categorizes the differences by type of change.  You will need to adjust the function to use
    the correct fields to create the combination of fields.
    The function 2 files that have mostly the same field names and looks for differences in each variable.  If you
    provide a list of the date fields in dateCols, then they will be compared as dates and not strings.  
    optsOOp and optsORd let you pass in directives for opening the 1st file and optsTOp and optsTRd let you pass
    in directives for opening the 2nd file.  howO and howT let you indicate wither you are reading a local file
    or web address.  caseO and caseT allow you to control the case of the fields names for analysis. (If reading an 
    API web address, the all field names will be lower-case, so you might need to tell the fuction to treat the other 
    files fields names as lower case. 
    '''
    id1="entityId"
    id2="documentId"

    print("Processing First File")
    yesno = {}   #  contains columns that have Yes,Y,No,N as answers; for checking on CIM
    if howO == "L":
        dOOp={}
        if len(optsOOp) > 0: 
            dOOp = getOpts(optsOOp)
            print("dOOp ",dOOp)
        fO = open(fileO,**dOOp)

        dORd={}
        if len(optsORd) > 0: 
            dORd = getOpts(optsORd)
            print("dORd ",dORd)
        readerO = csv.DictReader(fO,**dORd)  

    elif howO == "W":   #  read web file
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"}
        req = urlRequest.Request(f"{fileO}?$limit=999999999", headers = headers)
        x = urlRequest.urlopen(req)
        sourceCode = x.read()
        sourceCode=sourceCode.decode("utf-8")
        readerO = csv.DictReader(sourceCode.splitlines())        

#     linesOrg=[]
#     for line in readerO:
#         linesOrg.append(line)
#     fO.close()  
#     print(f"Read {len(linesOrg)} records in first file")


    print("Processing Second file") 
    if howT == "L":  #  read local file
        dTOp={}
        if len(optsTOp) > 0: 
            dTOp = getOpts(optsTOp)
            print("dTOp ",dTOp)
        fT = open(fileT,**dTOp)

        dTRd={}
        linesT={}
        if len(optsTRd) > 0: 
            dTRd = getOpts(optsTRd)
            print("dTRd ",dTRd)
        readerT = csv.DictReader(fT,**dTRd)  
        for lineT in readerT:
            # eid = lineT['entityId']
            # did = str(lineT['documentId']).strip()
            eid = lineT[id1]
            did = str(lineT[id2]).strip()

            if eid not in linesT:
                linesT[eid]={}
            if did in linesT[eid]:
                print("DUPLICATE",eid,did)
                # for key,val in linesT[eid][did].items():
                #     print(key,val,lineT[key])
                # print("--------------")
            linesT[eid][did]=lineT
    elif howT == "W":   #  read web file
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"}
        req = urlRequest.Request(f"{fileT}?$limit=999999999", headers = headers)
        x = urlRequest.urlopen(req)
        sourceCode = x.read()
        sourceCode=sourceCode.decode("utf-8")
        readerT = csv.DictReader(sourceCode.splitlines())  
        linesT = {}
        for lineT in readerT:
           # eid = lineT['entityid']
           # did = lineT['documentid']
            eid = lineT[id1]
            did = str(lineT[id2]).strip()
            if eid not in linesT:
                linesT[eid]={}
            if did in linesT[eid]:
                print("DUPLICATE",eid,did)
                # print(lines[eid][did])
                # print("--------------")
                # print(lineT)
                # print("--------------")
            linesT[eid][did]=lineT

#     linesTrn=[]
#     for line in readerT:
#         linesTrn.append(line)
#     fT.close()        
#     print(f"Read {len(linesTrn)} records in second file")

    print("Total Lines in Transformed File ",len(linesT))    
# Analyze files 
    print("Analyze Data")
    hist={}
    nbad=0
    total=0
    bads={}
    badsT={}
    misses={}
    allLinesO={}
    allLinesT={}
    dateHist={}
    # dateCols = ['fiscalYearStartDate','fiscalYearEndDate','dateFormed','expirationDate','statusDate','authorizedOfficerSignedDate',
    #                            'cfoSignedDate','registrationApprovedDate','paymentProcessedDate','nextRenewalRegistrationDate']
    for rowO in readerO:
       allLinesO[total]=rowO
       total+=1
       if total > 10000:
              print("LIMIT REACHED")
              break

  #     rowT = linesTrn[nn]
       if caseO.lower() == "l":   # convert keys to lower case
        #   print("CONVERTING KEY CASEO",":",caseO.lower(),":")
           rowONew={}
           for key,val in rowO.items():
               if isinstance(key,str):
                   keyN=key.lower()
               else:
                   keyN=key
               rowONew[keyN]=val
           rowO=rowONew

       try:
     #      rowT = next(readerT)

           #eid = rowO["entityId"]
           eid = rowO[id1]

           did = str(rowO[id2]).strip()
           if eid not in linesT:
               print("MISSED EID ",eid)
               continue
           if did not in linesT[eid]:
               print(f"FOR eid: {eid} MISSING DOCUMENT ID {did}")
               continue
           rowT = linesT[eid][did]
           allLinesT[total-1]=rowT

           if total == 1:
              columns=list(rowO.keys())
              columnsT = list(rowT.keys())
           # if total < 10:
           #     print(rowO)
           #     print("---------------------")
           #     print(rowT)
           #     print("---------------------")

           if caseT.lower() == "l":   # convert keys to lower case
               rowTNew={}
               for key,val in rowT.items():
                   if isinstance(key,str):
                       keyN=key.lower()
                   else:
                       keyN=key
                   rowTNew[keyN]=val
               rowT=rowTNew


           if total%100000 == 0:
                print(total)
       #    print("ROW T",rowT)

           for colOO,valO in rowO.items():
               if caseO.lower() == "l": # make it lower case
                   colO = colOO.lower()
               else:
                   colO=colOO

       #         if colO in xrefs:
       #            colT = xrefs[colO]
       # #           print("XREFS ",colO,colT)
       #         else:
       #            colT=colO 
               colT=colO 

               if colT in rowT:
                   valT = rowT[colT]
                   if colO in hist: 
                     hist[colO]["Total"]+=1
                   else:
                    hist[colO]={}
                    hist[colO]["Total"]=1
                    hist[colO]["Bad"]=0

                   if isinstance(valO,str) and valO.strip().lower() in ["y","n","yes","no"]:
                      if colO not in yesno:
                            yesno[colO]=0
                      yesno[colO]+=1
                   # if total < 10:
                   #     print(type(valO),type(valT),valO,valT)
                   valO = valO.strip()
                   valT = valT.strip()
                   # if total < 3:
                   #     print(colO,colT,type(valO),valO,type(valT),valT)

                   aO,valO = isn(valO)
                   aT,valT = isn(valT)

          #         if is_number(valT) and is_number(valO):
           #       if aO and aT:
                       # valT=float(valT)
                       # valO=float(valO)
                       # if total < 10:
                       #     print("HIT HIT ",colO,colT,type(valT),type(valO))

                   if colO in dateCols: 
                       dateHit=False
                       valTs=valT
                       valOs=valO
                       if isinstance(valT,str) and isinstance(valO,str) and len(valT) > 9 and len(valO) > 9:
                           # if total < 10:
                           #     print("DTT",valT[:10])
                           # nt = len(valT)
                           # no = len(valO)
                           dt=valT
                           od=valO

                         #  valT = datetime.datetime.strptime(valT[:10],"%Y-%m-%d")
                           valT = datetime.datetime.strptime(valT[:10],"%m/%d/%Y")
                           valO = datetime.datetime.strptime(valO,"%m/%d/%Y")
                           valT = valT.date()
                           valO = valO.date()
                           if colO not in dateHist:
                              dateHist[colO] = {}
                              dateHist[colO]["Total"]=0
                              dateHist[colO]["All Good"]=0
                              dateHist[colO]["Date Good"]=0  
                              dateHist[colO]["No Good"]=0   
                              dateHist[colO]["Just Bad"]={}
                              dateHist[colO]["Just Bad"]["count"]=0

                              dateHist[colO]["Just Bad"]["colOG"]=0
                              dateHist[colO]["Just Bad"]["colOGR"]=0

                              dateHist[colO]["Just Bad"]["colTG"]=0
                              dateHist[colO]["Just Bad"]["both"]=0
                              dateHist[colO]["Just Bad"]["rohroh"]=0

                           if dt == od:
                              dateHist[colO]["All Good"]+=1

                           elif valT == valO:  # Simple formatting issues
                              dateHist[colO]["Date Good"]+=1
                              flag="G1"
                              dateHit=True 
                           else:   # Date replace with bad date 
                              dateHist[colO]["No Good"]+=1   
                              flag="G2"
                              dateHit=True
                           # if total < 10:
                           #     print("DQATE ",valO,valT)
                       else:
                            if colO not in dateHist:
                              dateHist[colO] = {}
                              dateHist[colO]["Total"]=0
                              dateHist[colO]["All Good"]=0
                              dateHist[colO]["Date Good"]=0  
                              dateHist[colO]["No Good"]=0   
                              dateHist[colO]["Just Bad"]={} 
                              dateHist[colO]["Just Bad"]["count"]=0
                              dateHist[colO]["Just Bad"]["colOG"]=0
                              dateHist[colO]["Just Bad"]["colOGR"]=0

                              dateHist[colO]["Just Bad"]["colTG"]=0
                              dateHist[colO]["Just Bad"]["both"]=0
                              dateHist[colO]["Just Bad"]["rohroh"]=0



                            dateHist[colO]["Just Bad"]["count"]+=1
                            # print("DATE CHK ",colO,valO," :: ",valT)
                            if len(valO) < 5 and len(valT) < 5: 
                                dateHist[colO]["Just Bad"]["both"]+=1
                            elif len(valO) > 9 and len(valT) < 5:  # date missing 
                               dateHist[colO]["Just Bad"]["colOG"]+=1
                               flag="G3"  
                               dateHit=True
                            elif len(valO) > 9 and len(valT) > 4: # date replace with month-day
                               dateHist[colO]["Just Bad"]["colOGR"]+=1
                               flag="G2"
                               dateHit=True
                            elif len(valT) > 9: 
                               dateHist[colO]["Just Bad"]["colTG"]+=1
                            else: 
                               dateHist[colO]["Just Bad"]["rohroh"]+=1

                       dateHist[colO]["Total"]+=1     
                       if dateHit:
                    #     print("BAD FLAG ",flag,valO," :: ",valT)
                         if colO not in bads:
                            bads[colO]={}
                         if flag not in bads[colO]:
                            bads[colO][flag]={}
                         if valOs not in bads[colO][flag]:
                            bads[colO][flag][valOs]=valTs

                   if valT != valO:
                      if colO in xrefs:
                          flag=xrefs[colO]
                      else:
                          flag="None"
                      nbad+=1
                      hist[colO]["Bad"]+=1
                      # if colO in dateCols: 
                      #     valT=valTs
                      #     valO=valOs
                      if colO not in dateCols:
                          if colO not in bads:
                              bads[colO]={}
                              bads[colO][flag]={}
                          if valO not in bads[colO][flag]:
                             bads[colO][flag][valO]=valT

                          if colO not in badsT:
                              badsT[colO]={}
                          if valT not in badsT[colO]:
                             badsT[colO][valT]={}
                             badsT[colO][valT]["value"] = valO
                             badsT[colO][valT]["count"]=1
                          else:
                             badsT[colO][valT]["count"]+=1

                      # if colO == "tradenameForm":
                      if hist[colO]["Bad"] < 20:
                         print("Bad ",total,colO,valO," :: ",valT)
               else:
                    misses[colO]=1


       except Exception as err:
            print("ERR ",err)
            print("COLUMN ",colO,valO)
            print("COLUMN ",colT,valT)
            print("STOPPING STOPPING")
            exceptionLog(err,inspect.currentframe().f_code.co_name)
            # print("O Cols",rowO.keys(),"\n")
            # print("T Cols",rowT.keys(),"\n")

            print(hist)
            break
    print("Finished")
    print("\n----------------\n")

    print("\nBad Columns")
    for col,dct in hist.items():
    #    if dct['Bad'] > 0 and col.lower().find("date") == -1:
        if dct['Bad'] > 0:

            print(f"{col:30.30s}  {dct['Bad']:8d}")

    print("\n----------------------------\n")
    print("Date Specific Counts")

    print("                        Column  All Good  Date Good  No Good          Just Bad     Both Bad     ColOG Good   ColTG Good    Both B ad")
    for col,dct in dateHist.items():
        print(f'{col:30.30s}  {dct["All Good"]:8d}  {dct["Date Good"]:8d}  {dct["No Good"]:8d}  \
        {dct["Just Bad"]["count"]:8d}  {dct["Just Bad"]["both"]:8d}   {dct["Just Bad"]["colOG"]:8d}   \
        {dct["Just Bad"]["colTG"]:8d}  {dct["Just Bad"]["rohroh"]:8d} {dct["Just Bad"]["colOGR"]:8d}')

    print("\n----------------\n")
    print("\n-------------------------------")
    print("COLUMNS WITH YES/NO ANSWERS")
    print("COLUMNS WITH YES/NO ANSWERS")
    for col,cnt in yesno.items():
        print(col,cnt)
    if len(yesno) == 0:
        print("NO YES/NO Columns in Source Dataset")

    print("\n-------------------------------")
    if len(misses):
        print("SOURCE COLUMNS NOT FOUND IN OLD TRANSFORMED DATA")
        for col in misses:
            print(col)
        print("\n--------------------------------")

    return hist,dateHist,bads,badsT,total,columns,columnsT,yesno,allLinesO,allLinesT

########################################################################################




# What needs to be changed in <b>Run Analysis</b><br>
# 
# <ol>
#   <li> fileO  -> this is the new transformed file
#       <uL>
#           <li> OOpen (maybe need   "encoding=lating")
#           <li> ORdr  NEED "delimter='/t' and maybe  "quoting=3
#       </ul>
#   <li> fileT  ->  This is the OLD transformed file
#        <uL>
#           <li> TOpen (maybe need   "encoding=latin")
#           <li> TRdr  probably leave as ""
#       </ul>
#   <li> If need be, sort the 2 input files like this:<br>
#        cat  Charitable_Purpose_of_the_Charity_in_Colorado_20241010.csv | (sed -u 1q; sort ) > </li>
#   <li> link  ->  Change to datasets CIM link
#   <li> title ->  Change to CIM Title
#   <li> of  -> prepended to file name to make it uniqe for each dataset... can make it whatever ,as long as it is unique
#   <li> notes -> If we deleted columns from a dataset, list them here, otherwise, make it ""
#   <li> OUTPUT is written in directory html 
#   <li> Check output in VSC to be certain changed columns matches <a href="https://docs.google.com/spreadsheets/d/1RwrTNLihKfW0CQD5k98nzOYrUZaDhvvF7IVn1xpT56Y/edit?gid=0#gid=0">Summary Doc</a>
#       
# </ol>
#    

# ## Run Ananlysis

# In[12]:


##  This should be the NEW file which we have REMOVED the transform steps
#fileO = "/home/joe/bic_etl/cdos/business/business/data_transformed/trademarks.tsv"
#fileO = "/home/joe/bic_etl/cdos/business/business/data_transformed/tradenames.tsv"
#fileO = "/home/joe/bic_etl/cdos/business/business/data_transformed/business_entities.tsv"
#fileO = "/home/joe/bic_etl/cdos/business/business/data_transformed/corphist.tsv"
#fileO = "/home/joe/bic_etl/cdos/business/nonprofit/data_transformed/persons_sol_ntcs.tsv"
#fileO = "/home/joe/bic_etl/cdos/business/nonprofit/data_transformed/sol_ntcs.tsv"
#fileO="https://data.colorado.gov/resource/ew9y-6tv9.csv"
#fileO = "https://data.colorado.gov/resource/37wu-kn3g.csv"
#fileO = "/home/joe/bic_etl/cdos/business/nonprofit/data_transformed/reg_finan.tsv"
#fileO = "data/CIM/Registration_of_Charities__Paid_Solicitors__Professional_Fundraising_Consultants__and_for-profit_Public_Benefit_Corporations_in_Colorado_20240902.csv"
#fileO = "data/CIM/Paid_Solicitor_Solicitation_Notices_in_Colorado_20240911.csv"
#fileO = "data/CIM/Persons_Associated_with_Charitable_Organizations__Paid_Solicitors__and_Professional_Fundraising_Consultants_in_Colorado_20240925-sort.csv"
#fileO = "data/CIM/Charitable_Purpose_of_the_Charity_in_Colorado_20241010_sort.csv"
#fileO = "data/CIM/Other_State_Solicitation_of_Charities__Registrants_in_Colorado_20241011_sort.csv"
#fileO = "data/CIM/Charitable_Organizations__Offices_in_Colorado_20241014_sort.csv"
#fileO = "data/CIM/Campaign_Reports_for_Solicitation_Notices_to_Charities_in_Colorado_20241018_sort.csv"
#fileO = "data/CIM/Charitable_Solicitation_Call_Center_Locations_in_Colorado_20241021_sort.csv"
#fileO = "data/CIM/Charities_Solicitation_Type_by_Solicitation_in_Colorado_20241022_sort.csv"
#fileO = "data/CIM/Charity_Extension_Requests_20241024_sort.csv"
#fileO = "data/CIM/Communication_Methods_Used_in_Solicitation_Campaigns_in_Colorado_20241028_sort.csv"
#fileO = "data/CIM/Other_Names_a_Registered_Entity_Uses_to_Solicit_Contributions_in_Colorado_20241029_sort.csv"
#fileO = "data/CIM/Paid_Solicitors_Disclosed_on_Charity_Registration_Forms_in_Colorado_20241030_sort.csv"
#fileO = "data/CIM/Federal_Tax-Exempt_Subsection_Codes_in_Colorado_20241030_sort.csv"
#fileO = "/home/joe/bic_etl/cdos/business/business/data_transformed/masterlist.csv"
#fileO = "data/CIM/Business_Entity_Transaction_History_-_FOR_TESTING_ONLY_20251001_sort.csv"
fileO = "data/CIM/current_notaries_orig_sort_cleaned.csv"



## Directives for opening the file
OOpen= ""
#OOpen= "encoding='latin'"

##  Directives for use by the DictReader
ORdr = ""
#ORdr = "quoting=3,delimiter='\t'"

#ORdr = "delimiter='\t'"


## This should be the OLD file which we were Transforming
#fileT = "/home/joe/bic_etl/cdos/business/business/data_transformed/trademarks.csv"
#fileT = "/home/joe/bic_etl/cdos/business/business/data_transformed/tradenames.csv"
#fileT = "/home/joe/bic_etl/cdos/business/business/data_transformed/business_entities.csv"
#fileT = "/home/joe/bic_etl/cdos/business/business/data_transformed/corphist.csv"
#fileT = "https://data.colorado.gov/resource/hyr8-d3v9.csv?$limit=999999999"
#fileT = "data/CIM/Solicitation_Campaign_Supervisors_Listed_on_Solicitation_Notices_in_Colorado_20240813.csv"
#fileT = "data/CIM/Paid_Solicitor_Solicitation_Notices_in_Colorado_20240819.csv"
#fileT = "data/CIM/Registration_of_Charities__Paid_Solicitors__Professional_Fundraising_Consultants__and_for-profit_Public_Benefit_Corporations_in_Colorado_20240824.csv"
#fileT = "https://data.colorado.gov/resource/2nui-j9bu.csv"
#fileT = "https://data.colorado.gov/resource/37wu-kn3g.csv"
#fileT = "data/CIM/Registration_of_Charities__Paid_Solicitors__Professional_Fundraising_Consultants__and_for-profit_Public_Benefit_Corporations_in_Colorado_-_TESTING_ONLY_20240903.csv"
#fileT = "data/CIM/Registration_of_Charities__Paid_Solicitors__Professional_Fundraising_Consultants__and_for-profit_Public_Benefit_Corporations_in_Colorado_20240902.csv"
#fileT = "/home/joe/bic_etl/cdos/business/nonprofit/data_transformed/sol_notices.csv"
#TOpen= "encoding='latin'"
#fileT = "data/CIM/Charitable_Purpose_of_the_Charity_in_Colorado_-_FOR_TESTING_ONLY_20241010_sort.csv"
#fileT = "data/CIM/Other_State_Solicitation_of_Charities__Registrants_in_Colorado_-_FOR_TESTING_ONLY_20241011_sort.csv"
#fileT = "data/CIM/Charitable_Organizations__Offices_in_Colorado_-_FOR_TESTING_ONLY_20241014_sort.csv"
#fileT = "data/CIM/Charitable_Solicitation_Call_Center_Locations_in_Colorado-FOR_TESTING_ONLY_20241021_sort.csv"
#fileT = "data/CIM/Charities_Solicitation_Type_by_Solicitation_in_Colorado-FOR_TESTING_ONLY_20241022_sort.csv"
#fileT = "data/CIM/Charity_Extension_Requests-FOR_TESTING_ONLY_20241024_sort.csv"
#fileT = "data/CIM/Communication_Methods_Used_in_Solicitation_Campaigns_in_Colorado-FOR_TESTING_ONLY_20241028_sort.csv"
#fileT = "data/CIM/Other_Names_a_Registered_Entity_Uses_to_Solicit_Contributions_in_Colorado-FOR_TESTING_ONLY_20241029_sort.csv"
#fileT = "data/CIM/Paid_Solicitors_Disclosed_on_Charity_Registration_Forms_in_Colorado-FOR_TESTING_ONLY_20241030_sort.csv"
#fileT = "data/CIM/Federal_Tax-Exempt_Subsection_Codes_in_Colorado-FOR_TESTING_ONLY_20241030_sort.csv"
#fileT = "/home/joe/bic_etl/cdos/business/business/data_transformed/masterlist.tsv"
fileT = "data/CIM/Current_Notaries_in_Colorado_20251006_sort_cleaned.csv"

## Directives for opening the file
TOpen= ""

## Directives fro the DictReader
#TRdr = "delimiter='\t'"
TRdr = ""

## Can be used to xref old Transformed field names to CIM Field names
#  new:old
## sol_typ_sol_locs
# xrefCols = {
# "solicitationNoticeId":"sols_notice_id",
# "name":"ce_name",
# "solicitorName":"ps_name",
# "solicitationType":"sol_type_dscrp"
# }

# char_orgs_ext
# xrefCols = {
# "form990TCorporation":"filesForm990T",
# "dateCreated":"dateFiled",
# "irsRequires990":"IRSRequires990"
# }

xrefCols={}
dateCols=[]
xrefs2={}
#dateCols= [ 'solicitationApprovedDate', 'paymentProcessedDate','campaignCommencementDate','campaignConclusionDate', 'charitySignedDate',
#      'contractEffectiveDate','contractTerminationDate']

#hist,bads,total,linesO,linesT = createStats(fileO,fileT,OOpen,ORdr,TOpen,TRdr)
#hist,bads,total  = createStatsSerial(fileO,fileT,OOpen,ORdr,TOpen,TRdr)
#hist,bads,total,columns,yesno  = createStatsSerialNew(fileO,fileT,OOpen,ORdr,TOpen,TRdr,"W","L","","L")
#hist,dateHist,bads,badsT,total,columns,columnsT,yesno,linesO,linesT = createStatsMisMatch(fileO,fileT,OOpen,ORdr,TOpen,TRdr,dateCols,xrefs2,"L","L","","")
hist,dateHist,bads,badsT,total,columns,columnsT,yesno,linesO,linesT =  \
createStatsSequentialNew(xrefCols,fileO,fileT,OOpen,ORdr,TOpen,TRdr,dateCols,xrefs2,"L","L","L","L")
print("DH ",dateHist)

# CIM LINK TO DATASET
#link="https://data.colorado.gov/Business/Trade-Names-for-Businesses-in-Colorado/u7sb-g482/about_data"
#link="https://data.colorado.gov/Business/Trademarks-for-Businesses-in-Colorado/d3m2-b6we/about_data"
#link="https://data.colorado.gov/Business/Business-Entities-in-Colorado/4ykn-tg5h/about_data"
#link="https://data.colorado.gov/Business/Business-Entity-Transaction-History/casm-dbbj/about_data"
#link="https://data.colorado.gov/Business/Solicitation-Campaign-Supervisors-Listed-on-Solici/hyr8-d3v9/about_data"
#link="https://data.colorado.gov/Business/Registration-of-Charities-Paid-Solicitors-Professi/37wu-kn3g/about_data"
#link="https://data.colorado.gov/Business/Paid-Solicitor-Solicitation-Notices-in-Colorado/ew9y-6tv9/about_data"
#link="https://data.colorado.gov/Business/Persons-Associated-with-Charitable-Organizations-P/mr4v-jz8u/about_data"
#link="https://data.colorado.gov/Business/Charitable-Purpose-of-the-Charity-in-Colorado/7jm9-f28m/about_data"
#link="https://data.colorado.gov/Business/Other-State-Solicitation-of-Charities-Registrants-/5wyf-xqw7/about_data"
#link="https://data.colorado.gov/Business/Charitable-Organizations-Offices-in-Colorado/3qtu-edua/about_data"
#link="https://data.colorado.gov/Business/Campaign-Reports-for-Solicitation-Notices-to-Chari/fdcw-ei67/about_data"
#link="https://data.colorado.gov/Business/Charitable-Solicitation-Call-Center-Locations-in-C/wwhd-vg25/about_data"
#link="https://data.colorado.gov/Business/Charities-Solicitation-Type-by-Solicitation-in-Col/34aw-ny67/about_data"
#link="https://data.colorado.gov/Business/Charity-Extension-Requests/icqv-mi3c/about_data"
#link="https://data.colorado.gov/Business/Communication-Methods-Used-in-Solicitation-Campaig/w6kb-3vsj/about_data"
#link="https://data.colorado.gov/Business/Other-Names-a-Registered-Entity-Uses-to-Solicit-Co/q2av-rpr5/about_data"
#link="https://data.colorado.gov/Business/Paid-Solicitors-Disclosed-on-Charity-Registration-/wwbh-7bpa/about_data"
#link="https://data.colorado.gov/Business/Federal-Tax-Exempt-Subsection-Codes-in-Colorado/2z9k-uy4q/about_data"
#link="https://data.colorado.gov/Business/Master-List-in-Colorado/ej2c-jkvh/about_data"
#link="https://data.colorado.gov/Business/Business-Entity-Transaction-History/casm-dbbj/about_data"
link="https://data.colorado.gov/Government/Current-Notaries-in-Colorado/k4uv-yvnk/about_data"

# DATASET TITLE
#title="Trademarks for Businesses in Colorado"
#title="Trade Names for Businesses in Colorado"
#title="Business Entities in Colorado"
#title="Business Entity Transaction History"
#title="Solicitation Campaign Supervisors Listed on Solicitation Notices in Colorado"
#title="Registration of Charities, Paid Solicitors, Professional Fundraising Consultants, and for-profit Public Benefit Corporations in Colorado"
#title="Paid Solicitor Solicitation Notices in Colorado"
#title="Persons Associated with Charitable Organizations, Paid Solicitors, and Professional Fundraising Consultants in Colorado"
#title="Charitable Purpose of the Charity in Colorado"
#title="Other State Solicitation of Charities’ Registrants in Colorado"
#title="Charitable Organizations’ Offices in Colorado"
#title="Campaign Reports for Solicitation Notices to Charities in Colorado"
#title="Charitable Solicitation Call Center Locations in Colorado"
#title="Charities Solicitation Type by Solicitation in Colorado"
#title="Charity Extension Requests"
#title="Communication Methods Used in Solicitation Campaigns in Colorado"
#title="Other Names a Registered Entity Uses to Solicit Contributions in Colorado"
#title="Paid Solicitors Disclosed on Charity Registration Forms in Colorado"
#title="Master List in Colorado"
title="Current Notaries in Colorado"

#OUTPUT FILE NAME 
#of="tra-mrk"
#of="tra-nms"
#of="bus_ent"
#of="bus-trns"
#of="persons_sol_ntcs"
#of="reg_finan"
#of="sol_ntcs"
#of="persons_entity"
#of="purpose"
#of="state"
#of="offices"
#of="sn_cmpgn_rpts"
#of="sol_ntcs_locs"
#of="sol_typ_sol_ntcs"
#of="char_orgs_ext"
#of="sol_typ_entity"
#of="doing_bus_as"
#of="char_orgs_sol"
#of="tax_exempt_cds"
#of="masterlist"
of="nortaries"




# ADD EXTRA NOTES - This is used to indicate columns that were removed or added 
## tradename notes 
#notes = "Fields zipCode4 and mailingZipCode4 have been removed. These contained the 4-digit extension that some zip codes contain. Previously, these were extracted from the zip code and stored in its own field, however, now, this can be found as an extension on the zip code(s)."

## note for Solicitation Campaign Supervisors Listed on Solicitation Notices in Colorado
#notes="These fields have been removed as they are no longer available for this dataset: courtIssuingInjunction,courtWithJurisdiction,dateOfConviction,dateOfInjunction,dateOfViolatioin,dispostitionOfOffense,mailingAddress,mailingCity,mailingState,mailingZipCode and natureOfViolation"
## persons_entity
#notes="The column personType has been added.<br>These columns have been removed: mailingZipCode4, principalZipCode4"

## notes for reg_finan.txt
#notes="Fields principalZipcode4 and mailingZipcode4 have been removed"
## notes for offices.txt
#notes="Changed name to organizationName.<br>These columns have been removed: name,firstName,middleName,lastName,principalZipCode4,mailingZipCode4"
## notes for sn_cmpgn_rpts
#notes="The column snId has been added."
## notes for sol_ntcs_locs
#notes="The column snId and solicitationNoticeType has been added.<br>The column solicitationZipcode4 has been removed."
## sol_typ_sol_ntcs
#notes="The column snId has been added.<br>The column names have all been changed to Camel Case<br><p>No Significant Changes Were Made to Data Values</p>"
## char_orgs_ext
#notes = "The column reportNo has been added."
## char_orgs_sol
#notes="These columns were removed: registrantTypeAbbr, zipCode4, mailingZipCode4, performedZipCode4.<br>Changed column name nameofPS-PFC-CCV to orgName" 
#notes="The old transformation corrected some dates that are now being left as-is. This will cause some date mismatches.  Most of the appear to be bad years and affect about 50 records."
notes=""
print("Total Records Processed ",total)



string=createHTML(link,title,hist,dateHist,notes,xrefs2,100,bads)
print("Analysis Completed")

##  NOTE NOTE This does NOT write an output file.... THe next cell below does


# In[13]:

# ## Write Output

# In[ ]:


fout=open(f"html/{of}_cim.html","w")
fout.write(f"{string}\n")
fout.close()

