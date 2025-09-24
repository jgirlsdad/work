@echo off
setlocal

REM Get to BAT Directory
SET mypath=%~dp0
cd "%mypath%"

echo "This script will create a Windows Service to run in the background."
echo "Please give the service a unique name: e.g. SocrataIngressAgent.DEPARTMENT"
set /p service="Enter Service Name: "

REM 32 or 64 Bit Machine?
reg Query "HKLM\Hardware\Description\System\CentralProcessor\0" | find /i "x86" > NUL && set OS=32BIT || set OS=64BIT

REM SET LOGGING DIR
REM THIS WILL WORK EVEN IF THE PATH HAS SPACES
set PR_LOGPATH=%mypath%

if %OS%==64BIT goto 64B else goto 32B

REM Install the Service
:64B
echo Setting up for 64 bit machine...
"%mypath%/amd64/prunsrv.exe" "//IS//%service%" --DisplayName="%service%" ^
  --Description="The Socrata Ingress Agent" ^
  --Install="%mypath%/amd64/prunsrv.exe" ^
  --StartMode=jvm --StopMode=jvm ^
  --Classpath="%~dp0..\socrata-ingress-agent.jar" ^
  --ServiceUser=LocalSystem --ServicePassword="" ^
  --StartParams "--data-dir";"%LOCALAPPDATA%\socrata-ingress-agent" ^
  --StartClass=com.socrata.sia.launcher.Main ^
  --StopClass=com.socrata.sia.launcher.Main --StopParams stop ^
  --StdOutput=auto --StdError=auto
echo Service created.
goto check

:32B
echo Setting up for 32 bit machine
"%mypath%/prunsrv.exe" "//IS//%service%" --DisplayName="%service%" ^
  --Description="The Socrata Ingress Agent" ^
  --Install="%mypath%\prunsrv.exe" ^
  --StartMode=jvm --StopMode=jvm ^
  --Classpath="%~dp0..\socrata-ingress-agent.jar" ^
  --StartParams "--data-dir";"%LOCALAPPDATA%\socrata-ingress-agent" ^
  --StartClass=com.socrata.sia.launcher.Main ^
  --StopClass=com.socrata.sia.launcher.Main --StopParams stop ^
  --StdOutput=auto --StdError=auto
echo Service created.
goto check

:check
sc.exe config "%service%" start= auto
sc.exe failure "%service%" reset= 86400 actions= restart/1000/restart/1000
sc.exe start "%service%"

COPY "%mypath%\SocrataIngressAgent.exe" "%mypath%\%service%.exe"
echo "Process Complete."
PAUSE
