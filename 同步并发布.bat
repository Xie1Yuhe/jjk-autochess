@echo off
chcp 65001 >nul
title 同步并发布
cd /d "%~dp0"

echo ============================================
echo   咒术自走棋 - 一键同步
echo ============================================
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [!] 当前目录还不是 git 仓库
  echo     先执行：git init  ^&^&  git remote add origin 你的仓库地址
  pause
  exit /b 1
)

echo [1/3] 暂存全部修改...
git add -A

echo.
echo [2/3] 提交...
set /p MSG=提交说明（直接回车用默认）:
if "%MSG%"=="" set MSG=update
git commit -m "%MSG%"
if errorlevel 1 (
  echo     没有新的修改需要提交
)

echo.
echo [3/3] 推送到远程...
git push

echo.
echo ============================================
echo   完成。若已配置 Pages / Cloudflare，
echo   约 1 分钟后线上自动更新。
echo ============================================
pause
