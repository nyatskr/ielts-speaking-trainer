@echo off
chcp 65001 >nul
title Kokoro TTS Server (port 8880)
cd /d "D:\LeStoreDownload\workbuddy\project\ielts-speaking-trainer\server"
set HTTPS_PROXY=http://127.0.0.1:10808
set HTTP_PROXY=http://127.0.0.1:10808
set HF_ENDPOINT=https://hf-mirror.com

REM --- preflight: refuse to start if port 8880 is already taken ---
REM Uses a raw socket so the HTTP_PROXY env var cannot interfere.
C:\Users\nyats\.workbuddy-ai\binaries\python\versions\3.13.12\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(1.0); r=s.connect_ex(('127.0.0.1',8880)); s.close(); sys.exit(0 if r==0 else 1)"
if errorlevel 1 goto :start_server

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

:start_server
echo ============================================
echo  Kokoro TTS server starting...
echo  http://localhost:8880
echo  Build: speed-parameter-enabled (v2)
echo  Close this window to stop the server.
echo ============================================
echo.

C:\Users\nyats\.workbuddy-ai\binaries\python\envs\kokoro\Scripts\python.exe kokoro_server.py
echo.
echo Server stopped. Press any key to close.
pause >nul
