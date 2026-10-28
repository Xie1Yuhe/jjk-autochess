@echo off
chcp 65001 >nul
title 咒术自走棋 · 本地服务器
cd /d "%~dp0"
echo.
echo   正在启动本地服务器...
echo   地址： http://127.0.0.1:8848
echo   关闭本窗口即可停止。
echo.
start "" "http://127.0.0.1:8848/index.html"
python -m http.server 8848 2>nul || py -3 -m http.server 8848 2>nul || (
  echo   没有找到 Python。请直接双击 index.html 也可以运行。
  pause
)
