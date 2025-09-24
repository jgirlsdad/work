import re

fin = open("jss","r")

lines = fin.readlines()
targets = {}
for line in lines:
    nst = line.find("(")
    ned = line[nst:].find(")")
    if (nst > -1):
   #   print(line)
      target = line[nst+1:nst+ned]
      if target not in targets:
         targets[target]=0

      targets[target]+=1
    #   print(target)
    #   print("-------------------------------")
hit=0
miss=0
skipped = {}
fhit = open("libsToLoad","w")
fskp = open("libsToSkip","w")

for key,val in sorted(targets.items(), key=lambda x:x[1]):
    if key.find("/") == -1:
      fhit.write(f"{val:4d} - {key}\n")
      hit+=1
    else:
      miss+=1
      skipped[key] = val
      fskp.write(f"{val:4d} - {key}\n")



print(f"{hit}  Found,  skipped: {miss}")
   
