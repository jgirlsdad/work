USE GoCode_0719;
SET NOCOUNT ON;
SELECT 
'"' + REPLACE(statelst.stateabbrv, '"', '""') + '"' AS stateabbrv,
'"' + REPLACE(statelst.statename, '"', '""') + '"' AS statename, 
'"' + REPLACE(statelst.stfips, '"', '""') + '"' AS stfips, 
'"' + REPLACE(areatype.areatyname, '"', '""') + '"' AS areatyname, 
'"' + REPLACE(RTRIM(geog.areaname), '"', '""') + '"' AS areaname, 
'"' + REPLACE(ces.area, '"', '""') + '"' AS area, 
'"' + REPLACE(ces.periodyear, '"', '""') + '"' AS periodyear, 
'"' + REPLACE(ces.periodtype, '"', '""') + '"' AS periodtype, 
'"' + REPLACE(periodty.pertypdesc, '"', '""') + '"' AS pertypdesc, 
'"' + REPLACE(ces.period, '"', '""') + '"' AS period, 
'"' + REPLACE(ces.seriescode, '"', '""') + '"' AS seriescode, 
'"' + REPLACE(RTRIM(cescode.seriesttls), '"', '""') + '"' AS seriesttls, 
'"' + REPLACE(RTRIM(cescode.seriesdesc), '"', '""') + '"' AS seriesdesc, 
'"' + REPLACE(ces.adjusted, '"', '""') + '"' AS adjusted, 
'"' + REPLACE(ces.benchmark, '"', '""') + '"' AS benchmark, 
'"' + REPLACE(ces.prelim, '"', '""') + '"' AS prelim, 
'"' + REPLACE(ces.empces, '"', '""') + '"' AS empces, 
COALESCE(NULLIF(cast(ces.empprodwrk as varchar(20)),''), '') AS empprodwrk, 
COALESCE(NULLIF(cast(ces.empfemale as varchar(20)),''), '') AS empfemale, 
COALESCE(NULLIF(cast(ces.hours as varchar(20)),''), '') AS hours, 
COALESCE(NULLIF(cast(ces.earnings as varchar(20)),''), '') AS earnings, 
COALESCE(NULLIF(cast(ces.hourearn as varchar(20)),''), '') AS hourearn, 
'"' + REPLACE(ces.supprecord, '"', '""') + '"' AS supprecord, 
'"' + REPLACE(ces.supphe, '"', '""') + '"' AS supphe, 
'"' + REPLACE(ces.supppw, '"', '""') + '"' AS supppw, 
'"' + REPLACE(ces.suppfem, '"', '""') + '"' AS suppfem, 
COALESCE(NULLIF(cast(ces.hoursallwrkr as varchar(20)),''), '') AS hoursallwrkr, 
COALESCE(NULLIF(cast(ces.earningsallwrkr as varchar(20)),''), '') AS earningsallwrkr, 
COALESCE(NULLIF(cast(ces.hourearnallwrkr as varchar(20)),''), '') AS hourearnallwrkr, 
'"' + REPLACE(ces.suppheallwrkr, '"', '""') + '"' AS suppheallwrkr 
FROM dbo.ces 
JOIN dbo.statelst	ON ces.stfips = statelst.stfips 
JOIN dbo.areatype	ON ces.areatype = areatype.areatype AND ces.stfips = areatype.stfips 
JOIN dbo.cescode	ON ces.seriescode = cescode.seriescode AND ces.stfips = cescode.stfips 
JOIN dbo.periodty	ON ces.periodtype = periodty.periodtype 
JOIN dbo.geog		ON ces.areatype = geog.areatype	AND ces.stfips = geog.stfips AND ces.area = geog.area
