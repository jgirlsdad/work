import pandas as pd
def transformBlsSmEmpData(transOpts,vars): 
    """
    Transforms the BLS employment data.
    
    Args:
        transOpts (dict): Transformation options.
        vars (list): List of variables to transform.
    
    Returns:
        None
    """
    pass
    def colsToDict(df,key,val,fmt={}):
        return df.set_index(key)[val].to_dict()
    def decodeBlsSeriesNoDt(srs):
            mt = srs[2:3]
            st = srs[3:5]
            ar = srs[5:10]
            ss = srs[10:12]
            ic = srs[12:18]
            fc = srs[10:18]
            return mt,st,ar,ss,ic,fc

    def getBlsDefs(dirTarget,defsDir):
            defSS = pd.read_csv(f"{dirTarget}/{defsDir}/sm.supersector",delimiter="\t")
            defSS = colsToDict(defSS,"supersector_code","supersector_name")

            defFS = pd.read_csv(f"{dirTarget}/{defsDir}/sm.industry",delimiter="\t",dtype={"industry_code":"str","industry_name":"str"})
            defFS = colsToDict(defFS,"industry_code","industry_name")

            defAR = pd.read_csv(f"{dirTarget}/{defsDir}/sm.area",delimiter="\t")
            defAR = colsToDict(defAR,"area_code","area_name")

            defDT = pd.read_csv(f"{dirTarget}/{defsDir}/sm.data_type",delimiter="\t")
            defDT = colsToDict(defDT,"data_type_code","data_type_text")

            return defSS,defFS,defAR,defDT

    stats=["U","S"]
    dirTarget=transOpts.dirTarget
    defsDir=transOpts.defsDir
    sourceFiles=transOpts.inFiles
    outputFile=transOpts.outFile
    delimiter=transOpts.delimiter
    w4x4=transOpts.w4x4

    logger2=transOpts.logger2
    logger2.info(f"Starting Transform for : {transOpts.title}",extra={"s4x4":transOpts.w4x4})
    

    defSS,defFS,defAR,defDT=getBlsDefs(dirTarget,defsDir)
    allRecs={}
    fin=open(f"/home/joe/bic_etl/bls/data_source/sm.data.6.Colorado.tsv","r")
    linesCol = fin.readlines()
    fin.close()
    hist={}
    for line in linesCol[1:]:
        vals = [val.strip() for val in line.split(delimiter)]
        var = vals[0][18:]
    
        year=int(vals[1])
        month=int(vals[2].lower().strip("m"))
        value=vals[3]
    #    print(f"year:{year} month:{month} value:{value}  vals:{vals}")
        footNote=vals[4].strip()
        srs=vals[0]
        srs=vals[0][0:2] + " " + vals[0][3:].rstrip()
        stat= vals[0][2:3]
        if stat in hist:
            hist[stat]+=1
        else:
            hist[stat]=1
        if month < 13 and footNote.upper() != "P":
            if int(var) == 1: 
                if year not in allRecs:
                    allRecs[year]={}
                if month not in allRecs[year]:
                    allRecs[year][month]={}
                if srs not in allRecs[year][month]:
                    allRecs[year][month][srs]={}
                
                allRecs[year][month][srs][stat]=float(value)

    for stat in stats:
        if stat not in hist or hist[stat] < 100:
            cnt=None
            if stat in hist:
                cnt=hist[stat]
           
            logger2.error(f"Stat {stat} not found in data or count is very low for {cnt}",extra={"s4x4":w4x4})
            return
    fout=open(f"{dirTarget}/{outputFile}","w")
    head= "year\tmonth\tarea\tsuperSector\tindustry\tseries\temployementUnchanged\temploymentSeasonalyAdjusted"
    
    fout.write(f"{head}\n")

    for year,dct in allRecs.items():
        for month,dct2 in dct.items():
            for srs,dct3 in dct2.items():
                mt,st,ar,ss,ic,fc = decodeBlsSeriesNoDt(srs)
            
                susc = defSS[int(ss)]
                inc = defFS[fc]
                area=defAR[int(ar)].rstrip(", CO")
                string=f"{year}\t{month}\t{area}\t{susc}\t{inc}\t{srs}\t"
                mm=0
            
                for nn,stat in enumerate(stats):
                    if stat in dct3:
                        val = dct3[stat] 
                    else:
                        val = ""             
                    
                    string+=f"{val}\t" 
                

                string= string.strip(" ")
                string= string[:-1]
                
                nlen=  len(string.split("\t"))
                # print(string.split("\t"))
                # print("  ")
                if nlen != 8:
                    print("Too  Many",nlen,string.split("\t"))
                    break
                #         logger2.error(f"Unexpected # of Columns Expected 8, but found:{nlen}:",extra={"s4x4":w4x4})
                fout.write(f"{string}\n")
    fout.close()