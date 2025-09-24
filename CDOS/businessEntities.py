import sys
import os.path
bic_etl_home = os.getenv('bic_etl_home')
## Add the bic_etl/general/script directory to path 
sys.path.insert(0, os.path.join(bic_etl_home, 'general', 'scripts'))
import custom_log
w4x4="4ykn-tg5h"
logger2 = custom_log.setupNew("Business Entities in Colorado")
logger2.info("Starting: CDOS Business Entities in Colorado",extra={"s4x4":w4x4})

fin = open(f"{bic_etl_home}/cdos/business/business/data_source/business_entities.tsv",encoding="latin")

fout = open(f"{bic_etl_home}/cdos/business/business/data_transformed/business_entities-new.csv","w")
nlines=0
nfixed=0
status=-1
headerc=[
    "entityId",
    "entityName",
    "principalAddress1",
    "principalAddress2",
    "principalCity",
    "principalState",
    "principalZipCode",
    "principalCountry",
    "mailingAddress1",
    "mailingAddress2",
    "mailingCity",
    "mailingState",
    "mailingZipCode",
    "mailingCountry",
    "entityStatus",
    "jurisdictonOfFormation",
    "entityType",
    "agentFirstName",
    "agentMiddleName",
    "agentLastName",
    "agentSuffix",
    "agentOrganizationName",
    "agentPrincipalAddress1",
    "agentPrincipalAddress2",
    "agentPrincipalCity",
    "agentPrincipalState",
    "agentPrincipalZipCode",
    "agentPrincipalCountry",
    "agentMailingAddress1",
    "agentMailingAddress2",
    "agentMailingCity",
    "agentMailingState",
    "agentMailingZipCode",
    "agentMailingCountry",
    "entityFormDate"]
header='\t'.join(headerc)
fout.write(header+"\n")
for line in fin:
    spl=line.split("\t")
    nlines+=1
    if nlines > 1:
        if len(spl) > 35:
            for nn,c in enumerate(line):
                if ord(c) == 34:
                    status*=-1
      #          print(ord(c),c,status)
                if  ord(c) == 9 and status==1:
                   tmp=list(line)
                   tmp[nn]=""
                   line=''.join(tmp)
                   nfixed+=1

#        line=line.replace("\t",",")
        fout.write(line)
        
fout.close()
print(f"Total lines output: {nlines}") 
print(f"Total lines FIXED: {nfixed}")


# fin = open(f"{bic_etl_home}/cdos/business/business/data_transformed/business_entities-new.csv")
# #fin = open("/home/joe/bic_etl/cdos/business/business/data_source/business_entities-new.tsv",encoding="latin")
# nlines=0
# ndouble=0
# hist={}
# for line in fin:
#     nlines+=1
#     spl=line.split("\t")
#     for val in spl:
#         if val.count('"') != 2 and val.count('"') != 0:
#             ndouble+=1
#     nn=len(spl)
#     if nn not in hist:
#         hist[nn]=0
#     hist[nn]+=1
#     if len(spl) != 35:
#        logger2.warn(f"Bad Number of Fields in Line #{nlines}   # of fields {len(spl)}")
# print("Total Lines Checked",nlines)
# print(f"Histogram of the # of fields found  {hist}")
# print(f"# of multple double-quotes in fields: {ndouble}")

