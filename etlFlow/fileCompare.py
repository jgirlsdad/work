#!/usr/bin/env python
# coding: utf-8

# ## Imports

# In[2]:


import pandas as pd
import sys,os,inspect
from operator import itemgetter
sys.path.insert(0, '/mnt/c/users/cojoe/Python-Stuff')
#import JCLib
import threading
import PySimpleGUI as sg
import pyglet,tkinter
from pyglet import font
# import OpenGL
# from OpenGL import GLU
font.add_file('/etc/fonts/fonts/CENTAUR.TTF')
#D7BDE2 
##  Variables related to system info or imports
platform = sys.platform 
import time

colorPairs = [["#C39BD3","#D7BDE2"],["#D6EAF8","#85C1E9"],["#b3f0ff","#33d6ff"],["#D5F5E3","#A3E4D7"],["#FCF3CF","#F7DC6F"]]


# ## Functions

# In[3]:


def exceptionLog(exception,funCall):
  exception_message = str(exception)
  exception_type, exception_object, exception_traceback = sys.exc_info()
  filename = os.path.split(exception_traceback.tb_frame.f_code.co_filename)[1]
  print(f"{exception_message} {exception_type} {funCall}, Line {exception_traceback.tb_lineno}")
    
#####################################################################################

def find_delimiter(filename):
    sniffer = csv.Sniffer()
    with open(filename) as fp:
        delimiter = sniffer.sniff(fp.read(5000)).delimiter
    return delimiter

#####################################################

def fileAnalysis(file):
    delim = find_delimiter(file)    
    columns = {}
    fin = open(file,"r",encoding="latin")    
    lines = fin.readlines()
    for line in lines:
        spl = line.split(delim)
        nc = len(spl)
        if nc in columns:
            columns[nc]+=1
        else:
            columns[nc]=1
            
    return len(lines),delim,columns

########################################################################################

def getFile(how,file,WindowP,header=0):
    if how == "Local":
        if file[-3:].lower() == "tsv":
            delim = "\t"
            df=pd.read_csv(file,encoding="latin",delimiter=delim,header=header)
        elif file[-4:].lower() == "xlsx":
            df=pd.read_excel(file,engine="openpyxl",header=header)
        else:
            try:
                df=pd.read_csv(file)
            except Exception as err:
                print("Error, trying with encoding=latin")
                df=pd.read_csv(file,encoding="latin")
    elif how == "Fetch":
      
        file=values["-WEB-"]
        getPrevFiles(2,file)

        windowP["-PINFO-"].update(f"START reading WEB File:{file}:")
        df=pd.read_csv(file)
        windowP["-PINFO-"].update(f"FINISHED reading WEB File:{file}:")
        
    return df

##############################################################

def setRowColors(lst,col1,col2,colsp,header):
    count=0
    colors = {}
    print("COLORS ",col2,col2)
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

###########################################################

def sortTable(row,stats,colSortState,table,event,header):
    
        e = table.user_bind_event 
        region = table.Widget.identify('region', e.x, e.y)
        if region == 'heading':
            row = 0
        elif region == 'cell':
            row = int(table.Widget.identify_row(e.y))
   
        if row == 0:
            colClicked = int(table.Widget.identify_column(e.x)[1:])
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


#             window['-TABLE-'].update(values=statsVals,row_colors=colorsTable)
        return statsVals,colSortState

#######################################################################

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

def getValues(stats,header):

    statsVals=[]
    for col in sorted(stats.keys()):
         vals=[]
         vals.append(col)
         for k in header[1:]:
            vals.append(stats[col][k.strip()])
         statsVals.append(vals)
    return statsVals   

############################################################

def getFilesClicked(values,window):
        if len(values["-FILE1-"]) > 0:
            file = values["-FILE1-"]
        elif len(values["-WEB1-"]) > 0:
            file = values["-WEB1-"]
        
        df = getFile("Local",file,window)
        stats = dfAnalyze(df)

        return df,stats,file

############################################################

def getRowClicked(table,columns):
    col=""
    e = table.user_bind_event 
    region = table.Widget.identify('region', e.x, e.y)
    if region == 'heading':
        row = 0
    elif region == 'cell':
        row = int(table.Widget.identify_row(e.y))  
        col = columns[row-1][0]
    return row,col    

#####################################################################

def showDFUN(col,unq,windowParent,colr1,colr2):
  
    valuesUNQ = list(zip(unq.index.tolist(),unq.tolist()))
    hUNQ = []
    hUNQ.append("Values")
    hUNQ.append("Count")

    
    sortState = {}
    for val in hUNQ:
        sortState[val]=-1
    layout2 = [    
                   [sg.Text(f"Showing unique Values for Column"),sg.Text(f" {col}",text_color="red"),sg.Text(f" and Reg Ex",text_color="black")],
                
                   [sg.Button('Quit')],
            
                   [sg.Button('Write Unique'),
                    sg.Table(values=valuesUNQ,
                       background_color=colr1,vertical_scroll_only=False,col_widths=60,font='Courier 10 bold ' ,
                       auto_size_columns=True,enable_events=True,def_col_width=25,text_color="black",
                       justification='right',alternating_row_color=colr2,
                       key='-TABLE-', headings = hUNQ,metadata=sortState)]
            ]
    window2 = sg.Window(f"Unique", layout2,finalize=True,debugger_enabled=True,resizable=True)
    
    table = window2['-TABLE-']
    table.bind('<Button-1>', "Click")
    
    return window2,table,valuesUNQ,hUNQ


###########################################################

def sortUniqe(table,window,dataStore,headerStore):
    try:
        e = table.user_bind_event
        region = table.Widget.identify('region', e.x, e.y)
        sortAsc = {}
        sortAsc[1] =False
        sortAsc[-1]=True
      
        if region == 'heading':
            values = dataStore[table]
           
            header = headerStore[table]
           
            column = int(table.Widget.identify_column(e.x)[1:])
            col=header[column-1]
          
            sortState = table.metadata
            sortState[col]*=-1
            table.metadata = sortState
          
            values = sorted(values, key=lambda element: (element[column-1]),reverse=sortAsc[sortState[col]]) 
          
            window["-TABLE-"].update(values=values)
            dataStore[table] = values
    except Exception as err:
        exceptionLog(err,inspect.currentframe().f_code.co_name)
                    
 #######################################################################################       
        
def dfStringAnal(df,windowP):
    stats = {}
    nstats = {}
    ndates={}
    nums = ["int64","float64"]
    columnsNoDate=[]
    try: 
        for col in df: 
            if df[col].dtypes == "object":
                try : 
                    stats[col] = {}
                    
                    stats[col]["digits"] = -1
                    stats[col]["non-digits"] = -1
                    stats[col]["numeric"] = -1
                    stats[col]["word"] = -1
        #            stats[col]["non-word"] = df["B1_PER_ID1"].str.contains("\S").sum()
                    stats[col]["non-word"] = -1
                    stats[col]["white-spc"] = -1
                    stats[col]["_"] = -1                     
                    stats[col]["-"] = -1
                    stats[col]["#"] = -1
                    stats[col]["missing"] = -1

                    columnsNoDate.append(col)
                    typs = df[col].apply(type).value_counts().to_dict()
                    
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
                    
                    stats[col]["missing"] = df[col].isna().sum() 
                    stats[col]["% Missing"] = df[col].isna().sum()/df.shape[0]*100 
                    stats[col]["% Missing"] = float(f"{stats[col]['% Missing']:4.1f}")

                    stats[col]["digits"] = df[col].str.contains("\d").sum()
                    stats[col]["non-digits"] = df[col].str.contains("\D").sum()
                    stats[col]["numeric"] = df[col].str.replace(".","",1).str.isdecimal().sum()


                    stats[col]["word"] = df[col].str.contains("\w").sum()
        #            stats[col]["non-word"] = df["B1_PER_ID1"].str.contains("\S").sum()
                    stats[col]["non-word"] = df[col].str.contains("[^a-zA-Z0-9_ \-]").sum() 
                    stats[col]["white-spc"] = df[col].str.contains("\s").sum()   

                    stats[col]["_"] = df[col].str.contains("_").sum()                        
                    stats[col]["-"] = df[col].str.contains("-").sum()   
                    stats[col]["#"] = df[col].str.contains("#").sum() 
                except Exception as errs:
                    print(f"{col} Object error {errs}")
                    windowP["-PINFO-"].update(f"{col} Object error {errs}\n",append=True)
                    
            elif df[col].dtypes in nums:
                try: 
                    columnsNoDate.append(col)            
                    amin,amax,amen,astd = df[col].agg(["min","max","mean","std"])
                    nstats[col]={}
                    nstats[col]["Min"] = amin
                    nstats[col]["Max"] = amax
                    nstats[col]["Mean"] = amen
                    nstats[col]["Std"] = astd
                    nstats[col]["Missing"] =df[col].isna().sum()
                    nstats[col]["% Missing"] = df[col].isna().sum()/df.shape[0]*100 
                    nstats[col]["% Missing"] = float(f"{nstats[col]['% Missing']:4.1f}")
                    
                except Exception as errs:
                    print(f"{col} Number error {errs}")
   #                 windowP["-PINFO-"].update(f"{col} Number error {errs}\n",append=True)
                    
                    
            else:
                ndates[col]={}
                ndates[col]["Start"] = df[col].min()
                ndates[col]["End"] = df[col].max()
                ndates[col]["# Unique Dates"] = df[col].nunique()
    except Exception as err:
        print("dfStringAnal Error")
        print(err)

            
    
            
    nrecs=0
    return stats,nstats,ndates,columnsNoDate




def showDetailedAnalysis(dfO,windowP,file,idcol=""):
    
    global stats,nstats,statsVals,header_list
    df = dfO.copy()
    regex = {}
    regex["digits"] = "\d"
    regex["non-digits"] = "\D"
    regex["numeric"] = "isdecimal()"
    
    regex["word"] = "\w"
    regex["non-word"] = "[^a-zA-Z0-9_ \-]"
    regex["white-spc"] = "\s"  
    regex["_"] = "_"                        
    regex["-"] = "-"
    regex["#"] = "#" 
    regex["missing"] = "isna()" 
    regex["integer"] = "isinstance(x,int)" 
    
    dateFormats = ["%m/%d/%Y","%Y-%m-%d","%Y%m%d"]
    
    nrs,ncs = df.shape

    stats,nstats,ndates,colsNoDate = dfStringAnal(df,windowP)
    
    columnSortStateTable = {}
    columnSortStateTableN = {}
    header_list = ["Column","digits","non-digits","numeric","word","non-word","white-spc","  _  ","  -  ","  #  ","% Missing","missing","string","integer","float","boolean"]
    for col in range(len(header_list)):
         columnSortStateTable[col] = True
    col_widths = [8]*len(header_list)
    col_widths[0] = 25
 
    statsVals=[]
    for col in sorted(stats.keys()):
         vals=[]
        
         vals.append(col)
         for k in header_list[1:]:
            vals.append(stats[col][k.strip()])
         statsVals.append(vals)
    slen= len(statsVals)
   
## Number Stats for Tables
    header_nlist = ["Column","Min","Max","Mean","Std","% Missing","Missing"]
    for col in range(len(header_nlist)):
        columnSortStateTableN[col] = True
        
    nstatsVals=[]
    for col in sorted(nstats.keys()):
         vals=[]
        
         vals.append(col)
         for k in header_nlist[1:]:
            vals.append(nstats[col][k])
         nstatsVals.append(vals)
    nlen=len(nstatsVals)
   
## Date Stats for Tables   
    header_dlist = ["Column","Start","End","# Unique Dates"]
    ndateVals=[]
    for col in sorted(ndates.keys()):
         vals=[]
         vals.append(col)
         for k in header_dlist[1:]:
            vals.append(ndates[col][k])
         ndateVals.append(vals)
    
   
    columns = df.columns

    colRowTable = setRowColors(statsVals,"#b3f0ff","#33d6ff","pink",header_list)
    colRowTableN = setRowColors(nstatsVals,"#8AF5A1","#2DD150","pink",header_nlist)
    
   
    layout = [ 
             [sg.Text(f"File: {file}",font="CENTAUR 15")],
             [sg.Button('Quit')],
             [sg.Multiline(default_text="Summary\n",key="-PINFO-",size=[70,5],font="CENTAUR 10")],
             [sg.Text(f"Select Identifier Column",font="CENTAUR 15"),sg.Combo(values=columns,key="-IDENT-",enable_events=False,font="CENTAUR 10"),sg.Button("IdentB")],
             [sg.Text(f"Shape : {nrs} rows  by  {ncs} columns",font="CENTAUR 15")],
             [sg.Table(values=statsVals,text_color="black", auto_size_columns=False,enable_events=True,num_rows=20,col_widths=col_widths,font="CENTAUR 10",
                   justification='center',pad=(5,5),vertical_scroll_only=False,
                   key='-TABLES-',row_colors=colRowTable,headings = header_list,metadata=[header_list,statsVals,columnSortStateTable])],
             [sg.Table(values=nstatsVals,text_color="black",
                   auto_size_columns=False,enable_events=True,num_rows=15,col_widths=col_widths,font="CENTAUR 10",justification='center',pad=(5,5),vertical_scroll_only=False,
                   key='-TABLEN-',row_colors=colRowTableN, headings = header_nlist,metadata=[header_nlist,nstatsVals,columnSortStateTableN])],
             [sg.Text("Convert Column to Date",font="CENTAUR 15"),
              sg.Combo(colsNoDate,s=(25,4),font="CENTAUR 15 bold",expand_y=True,key="-CONVDATE-",enable_events=True),
              sg.Text("Format: "),sg.Combo(dateFormats,font="CENTAUR 15 bold",key="-DATEFS-"),sg.Multiline("",s=(10,1),key="-DATEFORM-"),sg.Button("Convert to Date")],
             [sg.Table(values=ndateVals, 
                   background_color='#b3f0ff',text_color="black",
                   auto_size_columns=False,enable_events=True,num_rows=nlen+2,col_widths=[25,12,12,10],font="CENTAUR 10",justification='center',alternating_row_color='#33d6ff',pad=(5,5),vertical_scroll_only=False,
                   key='-TABLED-', headings = header_dlist,metadata=[header_dlist,ndateVals,ndates])]
             ]
    # Create the Window
 
    sg.theme('Lightblue')
    window = sg.Window('Output', layout,finalize=True,resizable=True,metadata=[df])
#    window.TKroot.focus_set()

    #window2.move(window.current_location()[0]+600, window.current_location()[1])
    table = window['-TABLES-']
    table.bind('<Button-1>', "Click")
    tablen = window['-TABLEN-']
    tablen.bind('<Button-1>', "Click")
    tabled = window['-TABLED-']
    tabled.bind('<Button-1>', "Click")

##################################################################################    
    
def dfStringShow(df,col,statType):
    if df[col].dtypes == "object":
        if statType == "digits":
          tmp = df.loc[df[col].notna() & df[col].str.contains("\d")]
        elif statType == "non-digits":
          tmp = df.loc[df[col].notna() & df[col].str.contains("\D")]
        elif statType == "numeric":
          tmp = df.loc[df[col].notna() & df[col].str.replace(".","",1).str.isdecimal()]
        elif statType == "word":
          tmp = df.loc[df[col].notna() & df[col].str.contains("\w")]
        elif statType == "non-word":
          tmp = df.loc[df[col].notna() & df[col].str.contains("[^a-zA-Z0-9_ \-]")]
        elif statType == "white-spc":
          tmp = df.loc[df[col].notna() & df[col].str.contains("\s")]
        elif statType == "_":
          tmp = df.loc[df[col].notna() & df[col].str.contains("_")]
        elif statType == "-":
          tmp = df.loc[df[col].notna() & df[col].str.contains("-")]
        elif statType == "#":
          tmp = df.loc[df[col].notna() & df[col].str.contains("#")]
        elif statType == "missing" or statType == "% miss":
          tmp = df.loc[df[col].isna()]
        elif statType == "string":
          tmp = df.loc[df[col].apply(lambda x: isinstance(x,str))]
        elif statType == "integer":
          tmp = df.loc[df[col].apply(lambda x: isinstance(x,int))]
        elif statType == "float":
          tmp = df.loc[df[col].apply(lambda x: isinstance(x,float))]
        elif statType == "boolean":
          tmp = df.loc[df[col].apply(lambda x: isinstance(x,bool))]
        
        return tmp   

#################################################################################    
    
def showDF(df,col,st,unq,regex,idcol,windowParent):
  
    h = []
    cols=[]
    fname = col.replace(" ","")  #  output name used for file if output written
    h.append("Index")
    if len(idcol) > 0:
        h.append(idcol)
        cols.append(idcol)
    h.append(col)
    cols.append(col)
   
    if len(idcol) > 0:
      tmp = df.loc[:,cols]
      values = list(zip(tmp.index.tolist(),tmp.loc[:,idcol].tolist(),tmp.loc[:,col].tolist()))
    else:
      tmp = df.loc[:,col]
      values = list(zip(tmp.index.tolist(),tmp.tolist()))
    header= h
    valuesUNQ = list(zip(unq.index.tolist(),unq.tolist()))
#    print([f"{line}\n" for line in valuesUNQ])

    titleSort=1
    hUNQ = []
    hUNQ.append("Values")
    hUNQ.append("Count")

    
    sortState = []
    for val in hUNQ:
        sortState.append(1)
    layout2 = [    
                   [sg.Text(f"Showing Rows for Column"),sg.Text(f" {col}",text_color="red"),sg.Text(f" and Reg Ex",text_color="black"),sg.Text(f"{st} : {regex[st]}",text_color="red")],
                   [sg.Text(f"Total Rows with "),sg.Text(f" {regex[st]}",text_color="red"),sg.Text(f": {tmp.shape[0]} ")],
                   [sg.Button('Quit')],
                   [sg.Button('Write Bad'),sg.Table(values=values,
                       background_color='green',vertical_scroll_only=False,font="CENTAUR 15",
                       auto_size_columns=True,enable_events=False,def_col_width=30,
                       justification='right',alternating_row_color='brown',
                       key='-TABLE2-', headings = header)],
                   [sg.Button('Write Unique'),sg.Table(values=valuesUNQ,
                       background_color='white',vertical_scroll_only=False,col_widths=60,font='Courier 10 bold ' ,
                       auto_size_columns=True,enable_events=True,def_col_width=25,
                       justification='right',alternating_row_color='tan',
                       key='-TABLE3-', headings = hUNQ)]
            ]
    window2 = sg.Window(f"DataFrame", layout2,finalize=True,resizable=True, grab_anywhere=False)
    table2 = window2['-TABLE2-']
    table3 = window2['-TABLE3-']
    table3.bind('<Button-1>', "Click")
#    window2['-TABLE2-'].expand(True, True)
    
    try:
        while True:
                event, vals = window2.read()
            #    print(event,vals)
            #    window, event, values = sg.read_all_windows()
                if event == sg.WIN_CLOSED or event == 'Quit':
                    window2.close()
            #        sys.exit(1)
                    what = "QUIT"
                    break
                elif event == "Write Unique":
                    fout = open(f"{fname}.unq.txt","a+")
                    fout.write(f"\nColumn:Type:({col},Count)\n")
                    fout.writelines([f"{col}:UNIQUE:{line}\n" for line in valuesUNQ])
                    fout.close()
                    text = f"{col} Wrote Unique Records to file {fname}.unq.txt\n"
                    windowParent["-PINFO-"].update(text,append="True")
                elif event == "Write Bad":
                    fout = open(f"{fname}.bad.txt","a+")
                    fout.write(f"Column:Type:Desc:Reg Ex:(Index,{idcol},{col})\n")
                    fout.writelines([f"{col}:BAD:{st}:{regex[st]}:{line}\n" for line in values])
                    fout.close()
                    text = f"{col} Wrote Bad Records to file {fname}.bad.txt\n"
                    windowParent["-PINFO-"].update(text,append="True")
                elif event == "-TABLE3-Click":
                    e = table3.user_bind_event
                    region = table3.Widget.identify('region', e.x, e.y)
                    if region == 'heading':
                         column = int(table3.Widget.identify_column(e.x)[1:])
                         
                         if column-1 < len(sortState):  # check to be certain column selected in range
                             sortState[column-1]*=-1
                             if sortState[column-1] == -1:
                                sortAsc=False
                             else:
                                sortAsc=True
                             valuesUNQ = sorted(valuesUNQ, key=lambda element: (element[column-1]),reverse=sortAsc)  
                             window2['-TABLE3-'].update(values=valuesUNQ)
                    elif region == 'separator':
                        continue
                    else:
                        continue
    except Exception as err:
        print(err)
        print("Table 2")

###############################################################################

def inventoryYrMoDy(df,column):
    ''' invYrMo,invYrMoDy = inventoryYrMoDy(df,"Date Column")
    Compute Year-Month and Year-Month-Day inventory counts
    for a date column in the dataframe.  It is expected the 
    column is already a PANDAS date-time object'''
    amax=df[column].max()
    amin=df[column].min()
    invYrMo = {}
    invYrMoDy = {}

    for yr in range(amin.year,amax.year+1):
        invYrMo[yr]={}
        invYrMoDy[yr]={}
        for mo in range(1,13):
            invYrMo[yr][mo]=0
            invYrMoDy[yr][mo]={}      
            for dy in range(1,32):
                invYrMoDy[yr][mo][dy]=0

    x = df[column].value_counts()
    for xx in sorted(x.index):
        d=xx
        invYrMo[d.year][d.month]+= x[xx]
        invYrMoDy[d.year][d.month][d.day]+= x[xx]   
        
    return invYrMo,invYrMoDy

###############################################################################

def showDates(df,col,windowParent):
   
    head_YrMo = ["Year","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Dec"]
    fname = col.replace(" ","")  #  output name used for file if output written
  
    iYrMo,iYrMoDy=inventoryYrMoDy(df,col)
    
    valuesYrMo=[]
    for yr in sorted(iYrMo.keys()):
        tmp = [yr]
        for mo in range(1,13):
            tmp.append(iYrMo[yr][mo])       
        valuesYrMo.append(tmp)


    
    layout2 = [    
                   [sg.Text(f"Year-Month Inventory",text_color="black"),sg.Text(f" {col}",text_color="red")],
                   [sg.Button('Quit')],
                   [sg.Button('Show YrMoDy Inv')],
                   [sg.Table(values=valuesYrMo,
                       background_color='white',vertical_scroll_only=False,
                       auto_size_columns=False,enable_events=True,def_col_width=10,font="CENTAUR 10",
                       justification='center',alternating_row_color='tan',
                       key='-TABLEDATE-', headings = head_YrMo)]
            ]
    window2 = sg.Window(f"Inventory", layout2,finalize=True,resizable=True, grab_anywhere=False,metadata=[iYrMoDy,col])
    table3n = window2['-TABLEDATE-']
    table3n.bind('<Button-1>', "Click")
#    window2['-TABLE2-'].expand(True, True)
    
############################################################################

def showYrMoDyInv(iYrMoDy,col):
    head_YrMoDy = ["Year","Month"] + [f"Day {nn}" for nn in range(1,32)]
    valuesYrMoDy=[]                             
    for yr in sorted(iYrMoDy.keys()):
        for mo in range(1,13):
            tmp = [yr,mo]
            for dy in range(1,32):
                tmp.append(iYrMoDy[yr][mo][dy])         
            valuesYrMoDy.append(tmp)
    layout3 = [    
       [sg.Text(f"Year-Month Inventory",text_color="black"),sg.Text(f" {col}",text_color="red")],
       [sg.Button('Quit')],

       [sg.Table(values=valuesYrMoDy,
           background_color='white',vertical_scroll_only=False,
           auto_size_columns=False,enable_events=True,def_col_width=8,font="CENTAUR 8",
           justification='center',alternating_row_color='tan',
           key='-TABLEDATE-', headings = head_YrMoDy)]
    ]
    window3 = sg.Window(f"Year-Month-Day Inventory", layout3,finalize=True,resizable=True, grab_anywhere=False)

    
    


# ## GUI

# In[4]:



#############################################
def compareWindow(stats1,df1,file1):
    global color1,color2
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
               [sg.Button("Detailed Analysis",font="CENTAUR 15")],
               [sg.Table(values=valsFile1,text_color="black", auto_size_columns=False,enable_events=True,num_rows=20,col_widths=col_widths,font="CENTAUR 10",
                   justification='center',pad=(5,5),vertical_scroll_only=False,
                   key='-TABLEFILE-',row_colors=rowFile1Colors,headings = header_list,metadata=columnSortStateTable1)]
               ]
    
    

    layout = [[sg.Button("Quit")],
              
              [sg.Text("Change Header Row",font="CENTAUR 10"),
              sg.Combo([1,2,3,4,5,6,7,8,9,10],font="CENTAUR 10",enable_events=True,key="-HEADERCOMBO-"),
              sg.Button("Change Header")],
              [layCol1]  
             ]
    
   
    
                  
              
    window2 = sg.Window('Compare',layout,finalize=True,resizable=True,metadata=[df1,stats1,file1])
    a = window2.CurrentLocation()
    screen_width, screen_height = window2.get_screen_dimensions()
    win_width, win_height = window2.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
    x=200
    y=200
    window2.move(x, y)
    tableFile1 = window2['-TABLEFILE-']
    tableFile1.bind('<Button-1>', "Click")
   
    return window2,tableFile1,valsFile1,rowFile1Colors

##############################################   

def fileBrowser():
    global df1,df2,numWindows,color1,color2
    global stats1,stats2,window,statsVals
    dataStore = {}
    headerStore = {}
    header_list = ["Column","% Missing","Missing","string","integer","float","boolean"]
    
    regex = {}
    regex["digits"] = "\d"
    regex["non-digits"] = "\D"
    regex["numeric"] = "isdecimal()"
    
    regex["word"] = "\w"
    regex["non-word"] = "[^a-zA-Z0-9_ \-]"
    regex["white-spc"] = "\s"  
    regex["_"] = "_"                        
    regex["-"] = "-"
    regex["#"] = "#" 
    regex["missing"] = "isna()" 
    regex["integer"] = "isinstance(x,int)" 
    
    
    
    
    col_widths = [8]*len(header_list)
    col_widths[0] = 25
    columnSortStateTable1 = {}
    columnSortStateTable2 = {}

    ## set up sort state for the column in both tables
    for col in header_list:
         columnSortStateTable1[col] = -1
         columnSortStateTable2[col] = -1    
    
    # previousFiles = getPrevFiles(1)
    # previousFiles = list(previousFiles.keys())
    # print("Create Layout")
    layout = [[sg.Button("Close")],
             [sg.Button("Compare")],
             [sg.FilesBrowse(button_text="File # 1",initial_folder="/home/joe/bic_etl",font="CENTAUR 15",file_types=[("CSV Files","*.csv"),("TSV Files","*.tsv"),("Excel Files","*.xlsx")],enable_events=True,key='-FILE1-')],
             [sg.Text("Web Address:",font="CENTAUR 15"),sg.Input(default_text="",font="CENTAUR 15",key="-WEB1-"),sg.Button("Fetch")], 
             [sg.Checkbox("Error Analysis",font="CENTAUR 15",key="-ERRORANAL-")],
             [sg.Multiline(default_text="Summary\n",key="-PINFO-",font="CENTAUR 15",size=[70,5])],
             [sg.Output(size=(40,10),font="CENTAUR 15")],
             ]
              
              
    window = sg.Window('Files',layout,finalize=True,resizable=True)
    
    a = window.CurrentLocation()
    
    
    screen_width, screen_height = window.get_screen_dimensions()
    win_width, win_height = window.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
 
    x=200
    y=200
    window.move(x, y)
    windowsOpen = {}
    windowsOpen["main"] = []
    windowsOpen["unique"] = []
    numWindows=0
    
    while True:
        try:
            wid, event, values = sg.read_all_windows()
            
            print(wid)
            print(event)
            print(values)
            if event == sg.WIN_CLOSED or event == 'Close':
            
                break
            elif event == event == 'Quit':
                wid.close()
                
              #  break
            elif event == "-FILE1-" or event == "Compare" or event == "Fetch":
     #           files=[]
                if event == "Compare":
#                    values["-FILE1-"] = "/home/joe/bic_etl/cdos/business/nonprofit/data_transformed/sol_typ_entity.csv"
                    values["-FILE1-"] = "/home/joe/bic_etl/cdor/regulations_liquor/data_transformed/liquorLicenses.csv"
                if values["-ERRORANAL-"]:
                    file=values["-FILE1-"]
                    nlines,delim,columns = fileAnalysis(file)
                   
                    string = f"file: {file}\n# of lines: {nlines}\nDelimiter: {delim}\n"
                    for k,v in columns.items():
                        string+= f" {k} # Columns, # of lines {v}\n"
                    string+= "\n-----------------------------------------------\n"
                    window["-PINFO-"].update(string)
                else:
                    df1,stats1,file1 = getFilesClicked(values,window)
                    color1 = colorPairs[numWindows][0]
                    color2 = colorPairs[numWindows][1]

                    numWindows+=1
                    if numWindows > len(colorPairs):
                        numWindows=0

                    WindowC,tabl1,valsFile1,rowFile1Colors = compareWindow(stats1,df1,file1)
                    dataStore[tabl1]=valsFile1
                    windowsOpen["main"].append(WindowC)
            elif event == "-TABLEFILE-Click":
               
                row,col=getRowClicked(tabl1,valsFile1)
                stats1=wid.metadata[1]
                if row == 0:
                   valsFile1,columnSortStateTable1 = sortTable(row,stats1,columnSortStateTable1,tabl1,event,header_list)          
                   rowFile1Colors= setRowColors(valsFile1,color1,color2,"pink",header_list)
                  
                   wid["-TABLEFILE-"].update(values=valsFile1,row_colors=rowFile1Colors)
                else:
                   
                    unq = df1[col].value_counts()
                    w,t,values,uHead = showDFUN(col,unq,wid,"#b3f0ff","#33d6ff")
                    dataStore[t] = values
                    headerStore[t] = uHead
                    windowsOpen["unique"].append(w)
                   
            elif event == "-TABLE-Click":
                table = wid['-TABLE-']
                
                sortUniqe(table,wid,dataStore,headerStore)

### Change HEADER   
            elif event == "Change Header":
                headerRow = int(values["-HEADERCOMBO-"])
                file1 = wid.metadata[2]
                df1 = getFile("Local",file1,window,headerRow)
                stats1 = dfAnalyze(df1)
                wid.close()
                WindowC,tabl1,valsFile1,rowFile1Colors = compareWindow(stats1,df1,file1)
                dataStore[tabl1]=valsFile1
                windowsOpen["main"].append(WindowC)
                                
### Detailed Analysis
            elif event == "Detailed Analysis":    
                dfO = wid.metadata[0]
                file = wid.metadata[2]
                
                
                showDetailedAnalysis(dfO,window,file,idcol="")

### Detailed Clicked            
            elif event in ['-TABLES-Click','-TABLEN-Click']:
                ts = event.replace("Click","")
                
                table = wid[ts]
                header = table.metadata[0]
                statsVals = table.metadata[1]
                df = wid.metadata[0]
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
                    
                if row > 0:
                    colClicked = int(table.Widget.identify_column(e.x)[1:])
                    statClicked = header[colClicked-1].strip()
                    columnClicked = statsVals[row-1][0] 
                   
                    tmp = dfStringShow(df,columnClicked,statClicked)             
                    un = df[columnClicked].value_counts()
                    idcol=""
                    showDF(tmp,columnClicked,statClicked,un,regex,idcol,window)
                else:
                    colClicked = int(table.Widget.identify_column(e.x)[1:])-1
                   
                    statClicked = header[colClicked].strip()
                   
                    columnSortState = table.metadata[2]
                    columnSortState[colClicked]= not columnSortState[colClicked]
                    statsS =     sorted(statsVals, key=lambda x: x[colClicked],reverse=columnSortState[colClicked])
                    colorsTable = setRowColors(statsS,"#b3f0ff","#33d6ff","pink",header)
                    table.metadata = [header,statsS,columnSortState]
                    wid[ts].update(values=statsS,row_colors=colorsTable)     
                
### Convert Date
            elif event == 'Convert to Date':                 
                dcol = values["-CONVDATE-"]
                dform = values["-DATEFORM-"]
                if len(dform) > 0:
                    form=dform.strip()
                else:
                    form= values["-DATEFS-"]
                    
                df = wid.metadata[0]
                df[dcol]=pd.to_datetime(df[dcol], format=form)
                ndates = wid["-TABLED-"].metadata[2]
                header = wid["-TABLED-"].metadata[0]
                
                ndates[dcol]={}
                ndates[dcol]["Start"] = df[dcol].min()
                ndates[dcol]["End"] = df[dcol].max()
                ndates[dcol]["# Unique Dates"] = df[dcol].nunique()
                ndateVals=[]
                for col in sorted(ndates.keys()):
                     vals=[]
                     vals.append(col)
                     for k in header[1:]:
                        vals.append(ndates[col][k])
                     ndateVals.append(vals)
                wid['-TABLED-'].update(values=ndateVals)
                wid['-TABLED-'].metadata = [header,ndateVals,ndates]
                
### TableD Clicked
            elif event == '-TABLED-Click':
                table = wid["-TABLED-"]
                e = table.user_bind_event
                region = table.Widget.identify('region', e.x, e.y)
                if region == 'heading':
                    pass
                elif region == 'cell':
                    row = int(table.Widget.identify_row(e.y))
                elif region == 'separator':
                    continue
                else:
                    continue
                ndateVals = wid["-TABLED-"].metadata[1]
                colClicked = ndateVals[row-1][0]
                df=wid.metadata[0]
                
                # tmp = dfStringShow(septicOrig,columnClicked,statClicked)
                showDates(df,colClicked,window)

### Show YrMoDy Inventory
            elif event == 'Show YrMoDy Inv':
                iYrMoDy = wid.metadata[0]
                col = wid.metadata[1]
                showYrMoDyInv(iYrMoDy,col)
            
        
        except Exception as err:
             exceptionLog(err,inspect.currentframe().f_code.co_name)
    for wid in windowsOpen["unique"]:
        
        if wid:
            print("cosing ",wid)
            print(wid.close())
            wid = None
            

    for wid in windowsOpen["main"]:
       
        if wid:
            print("cosing ",wid)
            wid.close()
            wid = None
          
    window.close()
                    
fileBrowser()


# ## EnD
