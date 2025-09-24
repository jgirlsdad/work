import unicodedata
file="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/tate_lobbyist_bills.tsv"
file="test-crtnl.tsv"
file="test-nl.tsv"

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
tdir="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/"
#tdir="./"

# file=input("Input File")
# ffiles = open("files_in.txt","r")
# files=ffiles.readlines()

#files = ['test.tsv']
files = [file]

for file in files:
    file=file.strip()
    print(file)
    #  spl = file.split("/")
    fin = open(f"{file}","rb")
    nlines=0
    hist={}

    suml=0
    sumc=0
    chars=[]
    for line in fin.read():
        suml+=1
        chars.append(line)
 


nlines=1
for nn,char in enumerate(chars[1:-1]):
    if chars[nn] == 10:
        nlines+=1
    if chars[nn] == 127:
        ch=chars[nn]
        ch0=chars[nn-1]
        ch1=chars[nn+1]
        print(nlines,nn,chars[nn-1],chars[nn],chars[nn+1])

    if char not in hist:
        hist[char]=0
    hist[char]+=1


for char,count in sorted(hist.items()):
        print(char,count)

        # name=unicodedata.name(chr(ch))
        # name0=unicodedata.name(chr(ch0))
        # name1=unicodedata.name(chr(ch1))

       
        # print(name0,name,name1)
        # print()