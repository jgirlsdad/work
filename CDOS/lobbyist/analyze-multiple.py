import unicodedata
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
tdir="/home/joe/bic_etl/cdos/lobbyist/data_source/new_format/"
# file=input("Input File")
ffiles = open("files_in.txt","r")
files=ffiles.readlines()



for file in files:
    file=file.strip()
    #  spl = file.split("/")
    outf=file.replace(".txt","-summary.txt")
    errf=file.replace(".txt","-error.txt")

    print("Output",outf)
    fout=open(outf,"w")
    ferr=open(errf,"w")

    ff=file
    errrs={}
    fin = open(f"{tdir}{file}","rb")
    nlines=0
    histn={}
    histn_not={}
    string=""
    suml=0
    sumc=0
    crtnl=0
    nlcrt=0
    line0 = 0
    for line in fin.read():
        suml+=1
        try: 
        #  print(f"{suml}:{line}:{chr(line)}:{unicodedata.name(chr(line))}:{type(line)}")
            name=unicodedata.name(chr(line))
            if name not in histn:
                histn[name]=0
            histn[name]+=1
        except Exception as err:
    #       print(f"NO {suml}:{line}:{chr(line)}:{unicodedata.category(chr(line))}:{type(line)}")
            if line not in histn_not:
                histn_not[line]=0
            histn_not[line]+=1
            err=str(err)
           
            if err not in errrs:
                errrs[err]=0
            errrs[err]+=1

        line0=line
        # if suml > 100000:
        #     break
        # if suml > 100:
        #     break


    print(f"File: {file}")
    print(f"Number of Characters: {suml}\n")
 #   fout.write(f"File: {file}")
    tchars=0
    fout.write("File:Desc:Key:Count\n")

    #fout.write("\n\nHistogram of Letters\n")
    for key,val in sorted(histn.items()):
    #    print(f"{file}:Found:{key} : {val}")
        fout.write(f"{ff}:Found:{key} : {val}\n")
        tchars+=val


 #   print("--- not found in unicode ---")


    for key,val in sorted(histn_not.items()):
    #    print(f"{file}:Not Found:{key}:{val}")
        fout.write(f"{ff}:Not Found:{key}:{val}\n")
        tchars+=val

    fout.write(f"{ff}:Total Chars:{suml}:{tchars}")


    for key,val in errrs.items():
  #      print(f"{file}:error:{key}:{val}")
        ferr.write(f"{ff}:error:{key}:{val}\n")

    fout.close
    fin.close
    ferr.close()

    


# print("CRT Followed by NL:",crtnl)
# print("NL  Followed by CRT:",nlcrt)
# print("# New LInes ",histn[10])
# print("# Car Rets  ",histn[13])

