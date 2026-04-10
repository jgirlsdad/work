import cdsapi
import sys,datetime,os
#variables=["10m_u_component_of_wind","10m_v_component_of_wind","surface_pressure"]

def log(what,variable,time=None):
    global start,end
    fout = open("requests","a+")
    
    if what == "start":
        today=datetime.date.today()
        fout.write(f"{process_id}\t{variable}\tStart\t{today}\t\t{start}\t{end}\t{variables}\n")
        fout.close()
        return today
    elif what == "end":
        todayE=datetime.date.today()
        fout.write(f"{process_id}\n{variable}\tComplete\t{todayE}\t{todayE-time}\t{start}\t{end}\t{variables}\n")
        fout.close()
        return None
    elif what == "fail":
        todayE=datetime.date.today()
        fout.write(f"{process_id}\t{variable}\tFAIL\t{todayE}\t\t{start}\t{end}\t{variables}\n")
        fout.close()
        return None


process_id = os.getpid()

#variables=["2m_temperature","2m_dewpoint_temperature"]
#variables=["2m_temperature"]
#variables=["2m_dewpoint_temperature"]
##variables=["total_precipitation"]
#variables=["10m_u_component_of_wind"]

variables=["10m_v_component_of_wind"]
#ariables=["2m_temperature","2m_dewpoint_temperature","total_precipitation","10m_u_component_of_wind","10m_v_component_of_wind"]

# #variables=["total_precipitation"]



# global start,end
# start=1986
# end=1989
# timeStart=log("start",variables)
# # years=[str(year) for year in range(start,end)]
# print(f"Vars: {variables}")
# print(f"Years: {[str(year) for year in range(start,end+1)]}")

# dataset = "reanalysis-era5-land"
# for nvar in variables: 
#     variable= nvar
#     timeV=log("start",variable,timeStart)
    
#     try:
#         for starts in range(start,end,4):
#     #        end=start+3
#             ofile=f"{variable}_{start}_{end}"
#             years=[str(year) for year in range(start,end+1)]
#             print(ofile,years)
#             request = {
#                 "variable": [
#                      f"{variable}"
#                 ],
#                 "year": years,
#                 "month": [
#                     "01" , "02", "03",
#                     "04", "05", "06",
#                     "07", "08", "09",
#                     "10", "11", "12"
#                    ],
#                 "day": [
#                     "01", "02", "03",
#                     "04", "05", "06",
#                     "07", "08", "09",
#                     "10", "11", "12",
#                     "13", "14", "15",
#                     "16", "17", "18",
#                     "19", "20", "21",
#                     "22", "23", "24",
#                     "25", "26", "27",
#                     "28", "29", "30",
#                     "31"
#                 ],
#                 "time": [
#                     "00:00", "03:00", "06:00",
#                     "09:00", "12:00", "15:00",
#                     "18:00", "21:00"
#                 ],
#                 "data_format": "grib",
#                 "download_format": "unarchived",
#                 "target":ofile,
#                 "area": [41.1, -109, 37, -102]
#             }
            
#             client = cdsapi.Client()
#             client.retrieve(dataset, request).download()
#             print(f"File {ofile} Downloaded")
#             log("end",variable,timeV)          
#     except:
#         log("fail",variable)
#         print(f"Failed for {variable}")
#         sys.exit(1)
            

# log("end",variables,timeStart)




dataset = "reanalysis-era5-land"
request = {
    "variable": variables,
    "year": ["2026"],
    "month":  ["01" , "02", "03",
                     "04", "05", "06",
                     "07", "08", "09",
                     "10", "11", "12"],
    "day": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12",
        "13", "14", "15",
        "16", "17", "18",
        "19", "20", "21",
        "22", "23", "24",
        "25", "26", "27",
        "28", "29", "30",
        "31"
    ],
    "time": [
        "00:00", "03:00", "06:00",
        "09:00", "12:00", "15:00",
        "18:00", "21:00"
    ],
    "data_format": "grib",
    "download_format": "unarchived",
    "area": [41.1, -109, 37, -102]
}

client = cdsapi.Client()
client.retrieve(dataset, request).download()