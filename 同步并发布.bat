@echo off
chcp 65001 >nul
title 同步并发布（GitHub API 模式）
cd /d "%~dp0"

echo ============================================
echo   咒术自走棋 - 一键同步并发布
echo ============================================
echo.
echo 本机 git push 不可用（github.com:443 被阻断），
echo 所以走 GitHub REST API 提交。
echo.

set /p MSG=提交说明（直接回车用默认）:
if "%MSG%"=="" set MSG=update

echo.
echo [1/3] 记录本地版本...
git add -A >nul 2>&1
git -c user.name="Xie1Yuhe" -c user.email="Xie1Yuhe@users.noreply.github.com" commit -q -m "%MSG%" >nul 2>&1

echo [2/3] 读取 GitHub 凭据...
set "TOKEN="
for /f "usebackq tokens=1,* delims==" %%A in (`powershell -NoProfile -Command "$env:GIT_TERMINAL_PROMPT=0; $o = \"protocol=https`nhost=github.com`n`n\" | git credential fill 2^>$null; ($o ^| Select-String '^password=') -replace '^password=',''"`) do set "TOKEN=%%B"
if "%TOKEN%"=="" (
  echo [!] 没读到凭据。请先在任意目录执行一次 git 凭证登录。
  pause
  exit /b 1
)

echo [3/3] 上传到 GitHub...
set "PY=C:\Users\谢宇赫\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" tools\push_github.py Xie1Yuhe jjk-autochess %TOKEN% "%MSG%"

echo.
echo ============================================
echo   线上地址：https://xie1yuhe.github.io/jjk-autochess/
echo   约 1 分钟后自动生效（Pages 需要重建）
echo ============================================
pause
