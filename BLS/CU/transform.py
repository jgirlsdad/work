import pandas as pd
import csv
import numpy as np

def transformBlsCU(): 
    def colsToDict(df,key,val,fmt={}):
        return df.set_index(key)[val].to_dict()

#  Get the definitions for the series, item, and area codes
    defItem = pd.read_csv("cu.item",delimiter="\t")
    defItem = colsToDict(defItem,"item_code","item_name")
    defAre = pd.read_csv("cu.area",delimiter="\t")
    defAre = colsToDict(defAre,"area_code","area_name")
    print("ITEMS ",defItem)

    df=pd.read_csv("cu.data.0.Current",delimiter="\t")
    df.columns = df.columns.str.strip()
    df['area'] = df["series_id"].str[4:8]
    df['periodicity'] = df["series_id"].str[3:4]
    df['item'] = df["series_id"].str[8:16].str.strip()


#  Get Colorado subset of the data
    dfC = df.loc[df["area"]=="S48B"]
    dfC["itemName"] = dfC["item"].map(defItem)

    #dfCSemiA=dfC.loc[dfC["periodicity"] == "S"]
    dfCMnly=dfC.loc[dfC["periodicity"] == "R"]
    #print(dfCSemiA.shape)
    print(dfCMnly.shape)


    data={}
    dfCMnly.sort_values(by=["year","period"],inplace=True)
    items=list(dfCMnly["itemName"].value_counts().to_dict().keys())
    items.sort()
    years=sorted(dfCMnly["year"].value_counts().to_dict().keys())
    heads=["series","year","month"]
    for h in heads:
        data[h]=[]
    for item in items:
        data[item]=[]

    for year in years:    
        if year > 2000: 
            tmp=dfCMnly.loc[dfCMnly["year"]== year]
            for pp in sorted(tmp["period"].value_counts().to_dict().keys()):
                if pp.upper() != "M13":
                    hld=tmp.loc[tmp["period"] == pp]
            
                    dct=hld.set_index("itemName")["value"].to_dict()
                    srs=hld["series_id"].values[0]
                    srs=srs[:8]
                    data["series"].append(srs)
                    data["year"].append(year)
                    period=pp.upper().strip("M")
                    data["month"].append(period)
                    
                    for item in items:
                        if item in dct:
                            val=dct[item]
                        else:
                            val=""
                        data[item].append(val)


    cuOutput=pd.DataFrame(data)
    cuOutput.to_csv("cu.mnthly.tsv",sep="\t",index=False)

transformBlsCU()

#decodeBlsData(dirTarget=dirTarget,sourceFiles=inFiles,outputFile=outFile,defsDir=defsDir,w4x4=w4x4,logger2=logger2,vars=vars,delimiter=delimiter)