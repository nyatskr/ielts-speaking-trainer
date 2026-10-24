@echo off
chcp 65001 >nul
title Stopping Kokoro TTS Server
echo ============================================
echo  Stopping all Kokoro TTS processes...
echo ============================================
echo.

REM --- Step 1: Kill kokoro_server.py processes ---
echo [1/3] Searching for kokoro_server.py processes...
powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*kokoro_server.py*' }; if ($procs) { foreach ($p in $procs) { Write-Host ('  Killing PID ' + $p.ProcessId); Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host '  Done.' } else { Write-Host '  No kokoro_server.py processes found.' }"
echo.

REM --- Step 2: Kill leftover venv launcher processes ---
echo [2/3] Checking for leftover venv launcher processes...
powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*kokoro*' -and $_.CommandLine -notlike '*kokoro_server.py*' }; if ($procs) { foreach ($p in $procs) { Write-Host ('  Killing leftover PID ' + $p.ProcessId); Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host '  Done.' } else { Write-Host '  No leftover processes found.' }"
echo.

REM --- Step 3: Verify port 8880 is free ---
echo [3/3] Verifying port 8880 is free...
C:\Users\nyats\.workbuddy-ai\binaries\python\versions\3.13.12\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(1.0); r=s.connect_ex(('127.0.0.1',8880)); s.close(); sys.exit(0 if r==0 else 1)"
if errorlevel 1 (
  echo.
  echo  ============================================
  echo   Port 8880 is now FREE.
  echo   All Kokoro processes stopped.
  echo  ============================================
) else (
  echo.
  echo  ############################################
  echo  #  WARNING: Port 8880 is STILL in use!
  echo  ############################################
)

echo.
echo Done. Press any key to close.
pause >nul
