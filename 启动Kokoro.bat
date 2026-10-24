@echo off
chcp 65001 >nul
title Kokoro TTS Server (port 8880)
cd /d "D:\LeStoreDownload\workbuddy\project\ielts-speaking-trainer\server"
set HTTPS_PROXY=http://127.0.0.1:10808
set HTTP_PROXY=http://127.0.0.1:10808
set HF_ENDPOINT=https://hf-mirror.com

REM --- preflight: check if port 8880 is free (raw socket, not affected by proxy) ---
C:\Users\nyats\.workbuddy-ai\binaries\python\versions\3.13.12\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(1.0); r=s.connect_ex(('127.0.0.1',8880)); s.close(); sys.exit(0 if r==0 else 1)"
if errorlevel 1 goto :start_server

echo.
echo  ############################################################
echo  #  Port 8880 is in use by an old server process.
echo  #  Auto-cleaning old processes now...
echo  ############################################################
echo.

REM --- Auto-kill old kokoro processes ---
powershell -NoProfile -Command ^
  "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*kokoro*' }; ^
   if ($procs) { ^
     foreach ($p in $procs) { ^
       Write-Host ('  Killing PID ' + $p.ProcessId); ^
       Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue ^
     } ^
   }"

REM --- Wait a moment for processes to fully exit ---
timeout /t 2 /nobreak >nul

REM --- Re-check port ---
C:\Users\nyats\.workbuddy-ai\binaries\python\versions\3.13.12\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(1.0); r=s.connect_ex(('127.0.0.1',8880)); s.close(); sys.exit(0 if r==0 else 1)"
if errorlevel 1 goto :start_server

echo.
echo  ############################################################
echo  #  Port 8880 is STILL in use after auto-cleanup.
echo  #  Something else is holding the port.
echo  #  Run 停止Kokoro.bat, then try again.
echo  ############################################################
echo.
pause >nul
exit /b 1

:start_server
echo ============================================
echo  Kokoro TTS server starting...
echo  http://localhost:8880
echo  Build: speed-parameter-enabled (v2)
echo  Close this window to stop the server.
echo  Or run 停止Kokoro.bat to force-kill.
echo ============================================
echo.

C:\Users\nyats\.workbuddy-ai\binaries\python\envs\kokoro\Scripts\python.exe kokoro_server.py
echo.
echo Server stopped. Press any key to close.
pause >nul
