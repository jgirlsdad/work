def transformMasterList(row):
#  Additional Debtors
    addDebtors=""
    if len(row['Additional Debtors']) > -0: 
        
  #     print( row['Additional Debtors'])
        spl = row['Additional Debtors'].split(".")
        cntIds = row['Additional Debtors'].count("ID #")
        cntPds = row['Additional Debtors'].count("#")
        naddDebtors=0
        for val in spl:
            indx=val.find("ID #")
            if indx > -1:
               db=val[indx+5:].strip()
               addDebtors+=f"{db},"
               naddDebtors+=1
       
        if naddDebtors != cntIds or naddDebtors != cntPds:
            print("MISMATCH ",naddDebtors,cntIds,cntPds)
            print(row['Additional Debtors'])


#  Amendment ID
    addAmendId=""
    if len(row['Amendment ID #(s)']) > 0: 
        spl=row['Amendment ID #(s)'].split(";")
       
        for val in spl:
            spl2=val.split("-")
            aid=spl2[0].split("(")[0]
            aid=aid.replace("'","").strip()
            if len(aid) != 11:
                print(len(aid),aid,val)
            addAmendId+=f"{aid},"
        addAmendId=addAmendId.rstrip(",")


#  Record ID #
    countyId=""
    countyName=""
    recId=""
    recDate=""
    if len(row['Record Id #']) > 0:
        spl= row['Record Id #'].split("-")
        if len(spl) > 2:
            spl2 = spl[0].split("(")
            recId=spl2[0].strip()
            countyId = spl2[1].strip()
    
            countyName=spl[1].strip().strip(")")
            recDate = spl[2].strip()
        elif len(spl) == 2:
            recId=spl[0].strip()
            recDate=spl[1].strip()
            countyId=""
            countyName=""
    
    return addDebtors,addAmendId,recId,recDate,countyId,countyName