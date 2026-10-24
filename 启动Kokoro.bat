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
"C:\Users\nyats\.workbuddy-ai\binaries\python\envs\kokoro\Scripts\python.exe" kokoro_server.py
echo.
echo Server stopped. Press any key to close.
pause >nul
