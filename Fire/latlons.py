import grib2io

g = grib2io.open(f'Data/9035aad105e492216740525c32c4eeee.grib')
msgs = g.select(shortName="TMP",level="surface")
for msg in msgs:
    print(msg.shortName,msg.level,msg.valueOfForecastTime,msg.unitOfTimeRangeOfStatisticalProcess)

    lats = msg.lats
    lons = msg.lons
    print(lats,lons)
    break