#!/home/joe/anaconda3/envs/bic/bin/python3
# coding: utf-8
import argparse
import sqlite3
import pandas as pd

parser = argparse.ArgumentParser(prog="geti",
                                description="Get info from the Dataset Tracker " ,
                                usage="%(geti)s [options]")
parser.add_argument("-s", "--socrata", help="input the datasets 4x4 to get the title,description")
parser.add_argument("-t", "--title", help="input the datasets title to get the 4x4 and description",type=str)

args, leftovers = parser.parse_known_args()
where=""
if args.socrata and len(args.socrata) > 0:
    where = f' where "4x4" = "{args.socrata}"'
elif args.title and  len(args.title) > 0:
    where = f' where "datasetTitle" = "{args.title}"'



conn = sqlite3.connect('/home/joe/DBs/datasetTracker.db')
string=f'select * from datasets {where}'

df = pd.read_sql(string,conn)

vals = df[["4x4","datasetTitle","shortDescription"]].values

for val in vals:
    print(f"   4x4: {val[0]}\n Title: {val[1]}\n Short: {val[2]}")
    if len(vals) > 1:
        print("----")

