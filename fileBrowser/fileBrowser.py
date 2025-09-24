#!/usr/bin/env python
# coding: utf-8

# ## Imports

# In[4]:


import pandas as pd
import sys,os
from operator import itemgetter
sys.path.insert(0, '/mnt/c/users/cojoe/Python-Stuff')
import JCLib
import threading
import PySimpleGUI as sg
import pyglet,tkinter
from pyglet import font
# import OpenGL
# from OpenGL import GLU
font.add_file('/etc/fonts/fonts/CENTAUR.TTF')

##  Variables related to system info or imports
platform = sys.platform 


# ## GUI

# In[5]:


def setRowColors(lst,col1,col2,colsp,header):
    count=0
    colors = {}
    nrec = header.index("% miss")
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
                    stats[col]["% miss"] = df[col].isna().sum()/df.shape[0]*100 
                    stats[col]["% miss"] = float(f"{stats[col]['% miss']:4.1f}")

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
                    nstats[col]["% miss"] = df[col].isna().sum()/df.shape[0]*100 
                    nstats[col]["% miss"] = float(f"{nstats[col]['% miss']:4.1f}")
                    
                except Exception as errs:
                    print(f"{col} Number error {errs}")
                    windowP["-PINFO-"].update(f"{col} Number error {errs}\n",append=True)
                    
                    
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
                   [sg.Button('Close')],
                   [sg.Button('Show YrMoDy Inv')],
                   [sg.Table(values=valuesYrMo,
                       background_color='white',vertical_scroll_only=False,
                       auto_size_columns=False,enable_events=True,def_col_width=10,font="CENTAUR 10",
                       justification='center',alternating_row_color='tan',
                       key='-TABLEDATE-', headings = head_YrMo)]
            ]
    window2 = sg.Window(f"Inventory", layout2,finalize=True,resizable=True, grab_anywhere=False)
    table3n = window2['-TABLEDATE-']
    table3n.bind('<Button-1>', "Click")
#    window2['-TABLE2-'].expand(True, True)
    
    try:
        while True:
                event, vals = window2.read()
             #   print(event,vals)
            #    window, event, values = sg.read_all_windows()
                if event == sg.WIN_CLOSED or event == 'Close':
                    window2.close()
            #        sys.exit(1)
                    what = "QUIT"
                    break
                elif event == 'Show YrMoDy Inv':
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
                       [sg.Button('Close')],
                       
                       [sg.Table(values=valuesYrMoDy,
                           background_color='white',vertical_scroll_only=False,
                           auto_size_columns=False,enable_events=True,def_col_width=8,font="CENTAUR 8",
                           justification='center',alternating_row_color='tan',
                           key='-TABLEDATE-', headings = head_YrMoDy)]
                    ]
                    window3 = sg.Window(f"Year-Month-Day Inventory", layout3,finalize=True,resizable=True, grab_anywhere=False)

                    try:
                        while True:
                            event, vals = window3.read()
                           # print(event,vals)
                        #    window, event, values = sg.read_all_windows()
                            if event == sg.WIN_CLOSED or event == 'Close':
                                window3.close()
                                break
                    except Exception as e:
                        print(e)
                        print("Inventory YRMODY Table")
                    
                    
                    
    except Exception as e:
        print(e)
        print("inventory YrMo")







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
    
def showDFN(col,unq,windowParent):
   
 
    fname = col.replace(" ","")  #  output name used for file if output written
  
    valuesUNQ = list(zip(unq.index.tolist(),unq.tolist()))

    titleSort=1
    hUNQ = []
    hUNQ.append("Values")
    hUNQ.append("Count")

    
    sortState = []
    for val in hUNQ:
        sortState.append(1)
        
    layout2 = [    
                   [sg.Text(f"Unique Values for Column",text_color="black"),sg.Text(f" {col}",text_color="red")],
                   [sg.Button('Close')],
                   [sg.Button('Write Unique'),sg.Table(values=valuesUNQ,font="CENTAUR 15",
                       background_color='white',vertical_scroll_only=False,col_widths=[20,20],
                       auto_size_columns=False,enable_events=True,def_col_width=25,
                       justification='right',alternating_row_color='tan',
                       key='-TABLE3N-', headings = hUNQ)]
            ]
    window2 = sg.Window(f"DataFrame", layout2,finalize=True,resizable=True, grab_anywhere=False)
    table3n = window2['-TABLE3N-']
    table3n.bind('<Button-1>', "Click")
#    window2['-TABLE2-'].expand(True, True)
    
    try:
        while True:
                event, vals = window2.read()
             #   print(event,vals)
            #    window, event, values = sg.read_all_windows()
                if event == sg.WIN_CLOSED or event == 'Close':
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
                elif event == "-TABLE3N-Click":
                    e = table3n.user_bind_event
                    region = table3n.Widget.identify('region', e.x, e.y)
                    if region == 'heading':
                         column = int(table3n.Widget.identify_column(e.x)[1:])
                         
                         if column-1 < len(sortState):  # check to be certain column selected in range
                             sortState[column-1]*=-1
                             if sortState[column-1] == -1:
                                sortAsc=False
                             else:
                                sortAsc=True
                             valuesUNQ = sorted(valuesUNQ, key=lambda element: (element[column-1]),reverse=sortAsc)  
                             window2['-TABLE3N-'].update(values=valuesUNQ)
                    elif region == 'separator':
                        continue
                    else:
                        continue
    except Exception as e:
        print(e)
        print("Table 2")



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
                   [sg.Button('Close')],
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
                if event == sg.WIN_CLOSED or event == 'Close':
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





def analyzeDfGui(dfO,idcol,windowP,file):
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
    
    nrs,ncs = df.shape

    stats,nstats,ndates,colsNoDate = dfStringAnal(df,windowP)
    columnSortStateTable = {}
    columnSortStateTableN = {}
    header_list = ["Column","digits","non-digits","numeric","word","non-word","white-spc","  _  ","  -  ","  #  ","% miss","missing","string","integer","float","boolean"]
    for col in header_list:
         columnSortStateTable[col] = 1
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
    header_nlist = ["Column","Min","Max","Mean","Std","% miss","Missing"]
    for col in header_nlist:
        columnSortStateTableN[col] = 1
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
    
#     print(colorsTable)
#     colTab = []
    
    # for key,color in colorsTable.items():
    #     colTab.append(color)
    # rowNums = [num for num in range(0,len(colTab)+1)]
    # colText = ["black"]*len(colTab)
    # colrw = list(zip(rowNums,colTab))
   
    layout = [ 
             [sg.Text(f"File: {file}",font="CENTAUR 15")],
             [sg.Button('Quit')],
             [sg.Multiline(default_text="Summary\n",key="-PINFO-",size=[70,5],font="CENTAUR 10")],
             [sg.Text(f"Select Identifier Column",font="CENTAUR 15"),sg.Combo(values=columns,key="-IDENT-",enable_events=False,font="CENTAUR 10"),sg.Button("IdentB")],
             [sg.Text(f"Shape : {nrs} rows  by  {ncs} columns",font="CENTAUR 15")],
             [sg.Table(values=statsVals,text_color="black", auto_size_columns=False,enable_events=True,num_rows=20,col_widths=col_widths,font="CENTAUR 10",
                   justification='center',pad=(5,5),vertical_scroll_only=False,
                   key='-TABLE-',row_colors=colRowTable,headings = header_list)],
             [sg.Table(values=nstatsVals,text_color="black",
                   auto_size_columns=False,enable_events=True,num_rows=15,col_widths=col_widths,font="CENTAUR 10",justification='center',pad=(5,5),vertical_scroll_only=False,
                   key='-TABLEN-',row_colors=colRowTableN, headings = header_nlist)],
             [sg.Text("Convert Column to Date",font="CENTAUR 15"),sg.Combo(colsNoDate,s=[25,4],font="CENTAUR 15 bold",expand_y=True,key="-CONVDATE-",enable_events=True),sg.Text("Format: "),sg.Multiline("",s=(10,1),key="-DATEFORM-"),sg.Button("Convert to Date")],
             [sg.Table(values=ndateVals, 
                   background_color='#b3f0ff',text_color="black",
                   auto_size_columns=False,enable_events=True,num_rows=nlen+2,col_widths=[25,12,12,10],font="CENTAUR 10",justification='center',alternating_row_color='#33d6ff',pad=(5,5),vertical_scroll_only=False,
                   key='-TABLED-', headings = header_dlist)]
             ]
    # Create the Window
    sg.theme('Lightblue')
    window = sg.Window('Output', layout,finalize=True,resizable=True)
#    window.TKroot.focus_set()

    #window2.move(window.current_location()[0]+600, window.current_location()[1])
    table = window['-TABLE-']
    table.bind('<Button-1>', "Click")
    tablen = window['-TABLEN-']
    tablen.bind('<Button-1>', "Click")
    tabled = window['-TABLED-']
    tabled.bind('<Button-1>', "Click")

    while True:
        try:
            event, values = window.read()
            # print(event)
            # print("V ",values)
            # print("D ",values["-DATEFORM-"])
            
        #    window, event, values = sg.read_all_windows()
            if event == sg.WIN_CLOSED or event == 'Quit':
                window.close()
        #        sys.exit(1)
                what = "QUIT"
                break
            elif event == '-TABLE-':
                pass
            elif event == '-TABLE-Click':
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
                    statClicked = header_list[colClicked-1].strip()
                    columnClicked = statsVals[row-1][0]                 
                    tmp = dfStringShow(df,columnClicked,statClicked)             
                    un = df[columnClicked].value_counts()
                    showDF(tmp,columnClicked,statClicked,un,regex,idcol,window)
                else:
                    colClicked = int(table.Widget.identify_column(e.x)[1:])
                    statClicked = header_list[colClicked-1].strip()
                    columnSortStateTable[statClicked]*=-1
                    if columnSortStateTable[statClicked] == -1:
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
                         for k in header_list[1:]:
                            vals.append(statsS[col][k.strip()])
                         statsVals.append(vals)
                   # slen= len(statsVals)
                    colorsTable = setRowColors(statsVals,"#b3f0ff","#33d6ff","pink",header_list)
                
                    window['-TABLE-'].update(values=statsVals,row_colors=colorsTable)
            elif event == '-TABLEN-Click':
                e = tablen.user_bind_event
                region = tablen.Widget.identify('region', e.x, e.y)
                if region == 'heading':
                    row = 0
                elif region == 'cell':
                    row = int(tablen.Widget.identify_row(e.y))
                elif region == 'separator':
                    continue
                else:
                    continue
                if row > 0:
                    colClicked = nstatsVals[row-1][0]
                    un = df[colClicked].value_counts()
                    showDFN(colClicked,un,window)
                else:
                    colClicked = int(table.Widget.identify_column(e.x)[1:])
                    statClicked = header_nlist[colClicked-1].strip()
                    
                    columnSortStateTableN[statClicked]*=-1
                    if columnSortStateTableN[statClicked] == -1:
                        sortAsc=False
                    else:
                        sortAsc=True
                    if colClicked > 1:
                        nstatsS = dict(sorted(nstats.items(), key=lambda x: x[1][statClicked],reverse=sortAsc))
                    else:
                        nstatsS = dict(sorted(nstats.items(), key=lambda x: x[0],reverse=sortAsc))
                        
                    nstatsVals=[]
                    for col in nstatsS.keys():
                         vals=[]
                         vals.append(col)
                         for k in header_nlist[1:]:
                            vals.append(nstatsS[col][k])
                         nstatsVals.append(vals)
                    colRowTableN = setRowColors(nstatsVals,"#8AF5A1","#2DD150","pink",header_nlist)
                   
                    window['-TABLEN-'].update(values=nstatsVals,row_colors=colRowTableN)
                    
                
            elif event == '-TABLED-Click':
                e = tabled.user_bind_event
                region = tabled.Widget.identify('region', e.x, e.y)
                if region == 'heading':
                    pass
                elif region == 'cell':
                    row = int(tabled.Widget.identify_row(e.y))
                elif region == 'separator':
                    continue
                else:
                    continue
                colClicked = ndateVals[row-1][0]
                
                # tmp = dfStringShow(septicOrig,columnClicked,statClicked)
                showDates(df,colClicked,window)
            elif event == 'IdentB': 
                idcol = values["-IDENT-"]
                window.close()
                analyzeDfGui(df,idcol,windowP,file)
                
            elif event == 'Convert to Date':  
               
                dcol = values["-CONVDATE-"]
                dform = values["-DATEFORM-"]
                if len(dform) > 0:
                    form=dform.strip()
                else:
                    form= "%m/%d/%Y"
                df[dcol]=pd.to_datetime(df[dcol], format=form)
                ndates[dcol]={}
                ndates[dcol]["Start"] = df[dcol].min()
                ndates[dcol]["End"] = df[dcol].max()
                ndates[dcol]["# Unique Dates"] = df[dcol].nunique()
                ndateVals=[]
                for col in sorted(ndates.keys()):
                     vals=[]
                     vals.append(col)
                     for k in header_dlist[1:]:
                        vals.append(ndates[col][k])
                     ndateVals.append(vals)
                window['-TABLED-'].update(values=ndateVals)
        except Exception as err:
            print("Error :",err)
            print("bad bad ")


# ## File Browser

# In[18]:


def getPrevFiles(what,file=""):
##  what = 1 = read files; 2 = write files
    if platform == "linux":
        fdir = "/tmp/analyzeFile.txt"
    else:
        fdir = "c:\\tmp\\"
    if what == 1:
        with open(f"{fdir}","r") as filesIn:
            lines = filesIn.readlines()
            previousFiles = {}
            for line in lines:
                line = line.strip()
                if os.path.isfile(f"{line}"):
                    previousFiles[line]=1
            filesIn.close()
            
            return previousFiles
    elif what == 2: 
         with open(f"{fdir}","a+") as filesOut:
                if len(file) > 0: 
                    filesOut.write(f"{file}\n")
                    filesOut.close()
                else:
                    print(f"File Empty: tryin to write {file} to log")
                      
def fileBrowser():
    global df
    threads = []
    previousFiles = getPrevFiles(1)
    previousFiles = list(previousFiles.keys())
    print("Create Layout")
    layout = [
             [sg.FilesBrowse(button_text="Browse Files",initial_folder="/home/joe/bic_etl",font="CENTAUR 15",file_types=[("CSV Files","*.csv"),("TSV Files","*.tsv"),("Excel Files","*.xlsx")],enable_events=True,key='-FILES-')],
             [ sg.Text("Previous Files"),sg.Listbox(previousFiles,select_mode="LISTBOX_SELECT_MODE_SINGLE",enable_events=True,size=(100,5),key="-PREV-",font="CENTAUR 10"),sg.Button("Get")],
             [sg.Text("Web Address:",font="CENTAUR 15"),sg.Input(default_text="",font="CENTAUR 15",key="-WEB-"),sg.Button("Fetch")],
             [sg.Button('Quit')],
             [sg.Multiline(default_text="Summary\n",key="-PINFO-",font="CENTAUR 10",size=[70,5])],
            ]
    # Create the Window
    sg.theme('Lightblue')
    
    window = sg.Window('Files',layout,finalize=True,resizable=True)
    
    a = window.CurrentLocation()
    
    
    screen_width, screen_height = window.get_screen_dimensions()
    win_width, win_height = window.size
    x, y = (screen_width - win_width)//2, (screen_height - win_height)//2
 
    x=200
    y=200
    window.move(x, y)
    # a = window.CurrentLocation()
    # print("NEW LOCATION ",a)
    # window.TKroot.focus_set()
    # prevFil = window['-PREV-']
    # prevFil.bind('<Button-1>', "Click")
    #window2.move(window.current_location()[0]+600, window.current_location()[1])
          
    print("Starting Loop")
    while True:
        try:
           
            event, values = window.read(timeout=100000)
#             print(event)
#             print("V ",values)
           
            # window.move(x, y)
            # a = window.CurrentLocation()
            # print("NEW LOCATION ",a)
        #    window, event, values = sg.read_all_windows()
            if event == sg.WIN_CLOSED or event == 'Quit':
                window.close()
                break
            elif event == "-FILES-" or event == "Get":
                if event == "-FILES-":
                    file=values["-FILES-"]
                else:
                    file=values["-PREV-"][0]
                getPrevFiles(2,file)
                print(f"Processing File {file}") 
                string=f"Processed File: {file}"
                window["-PINFO-"].update(string,append=True)
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
    
               
                analyzeDfGui(df,"",window,file)
            elif event == "Fetch":
                print("Getting that web data")
                file=values["-WEB-"]
                getPrevFiles(2,file)
                
                window["-PINFO-"].update(f"START reading WEB File:{file}:")
                df=pd.read_csv(file)
                window["-PINFO-"].update(f"FINISHED reading WEB File:{file}:")
                analyzeDfGui(df,"",window,file)
                
    
        except Exception as e:
            print("ERROR ",e)
stats = {}        
nstats = {}
fileBrowser()


# In[ ]:


df


# In[ ]:


import datetime


# In[ ]:


from dateutil.parser import parse 


# In[ ]:


a = df["Issue Date"].values.tolist()


# In[9]:


import screeninfo

for m in screeninfo.get_monitors():
    print(m)


# In[ ]:


get_ipython().system('pipenv install  screeninfo')


# In[ ]:


b ='06 24 2023'
parse(b)


# In[ ]:


import re
for col in df.columns:
    if re.findall("date",col.lower()):
        typs = df[col].apply(type).value_counts().to_dict()
        print(typs)
        try:
            df[col] = pd.to_datetime(df[col])
            print(df[col].apply(type).value_counts().to_dict())
        except:
            print(f"Failed to COnvert {col} to a date")


# In[ ]:


pd.to_datetime(df["statusDate"])


# In[ ]:


for col in df.columns:
    if re.findall("date",col.lower()):
        typs = df[col].apply(type).value_counts().to_dict()
        print(typs)


# In[ ]:




