file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/state_lobbyist_bills.txt"
# file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/"
# file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/"
# file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/"
# file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/"
#file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/prof_disclosure_report_summary.txt"
#file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/state_lobbyist_officials.txt"
#file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/state_lobbyist_directory.txt"


#file="test.csv"
#file="test.tsv"
#fout= open("test.tsv","w")
#file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/state_lobbyist_officials.txt"
fin = open(file,"r")
nlines=0
histn={}
string=""
suml=0
sumc=0
crtnl=0
nlcrt=0
line0 = 0
for line in fin:
    nchrs=0
    for c in line:
        print(f"{nchrs}:{c}:{ord(c)}:{type(c)}")
        nchrs+=1


#if suml > 1:
#         if line == 13 and line0 == 10:
#             nlcrt+=1
#             print("hit nl",line,line0)
#         if line == 10 and line0 == 13:
#             crtnl+=1
#             print("hit  crt",line,line0)
# #    print(f"{suml}:{line}:{chr(line)}:{type(line)}")

    if line not in histn:
        histn[line]=0
    histn[line]+=1
 #   line0=line
    # if suml > 100:
    #     break
    
print(suml)
print("CRT Followed by NL:",crtnl)
print("NL  Followed by CRT:",nlcrt)
print("# New LInes ",histn[10])
print("# Car Rets  ",histn[13])

