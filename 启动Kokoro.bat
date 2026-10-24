@echo off
chcp 65001 >nul
title Kokoro TTS Server (port 8880)
cd /d "D:\LeStoreDownload\workbuddy\project\ielts-speaking-trainer\server"
set HTTPS_PROXY=http://127.0.0.1:10808
set HTTP_PROXY=http://127.0.0.1:10808
set HF_ENDPOINT=https://hf-mirror.com
echo ============================================
echo  Kokoro TTS server starting...
echo  http://localhost:8880
echo  Build: speed-parameter-enabled (v2)
echo  Close this window to stop the server.
echo ============================================
echo.

REM --- preflight: refuse to start if port 8880 is already taken ---
powershell -NoProfile -Command "if (Test-NetConnection -ComputerName 127.0.0.1 -Port 8880 -InformationLevel Quiet -WarningAction SilentlyContinue) { exit 1 } else { exit 0 }" 2>nul
if errorlevel 1 (
  echo.
  echo  ############################################################
  echo  #  ERROR: port 8880 is already in use.
  echo  #
  echo  #  An older Kokoro server is still running and is serving
  echo  #  requests. The new one would silently lose every request,
  echo  #  which is why speed control appeared to do nothing.
  echo  #
  echo  #  Close EVERY Kokoro server window (task manager: python.exe)
  echo  #  then run this launcher again.
  echo  ############################################################
  echo.
  pause >nul
  exit /b 1
)

"C:\Users\nyats\.workbuddy-ai\binaries\python\envs\kokoro\Scripts\python.exe" kokoro_server.py
echo.
echo Server stopped. Press any key to close.
pause >nul
