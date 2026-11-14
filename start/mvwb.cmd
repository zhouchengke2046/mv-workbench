@echo off
set DIR=%~dp0
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%DIR%..\scripts\mvwb.py" %*
) else (
  python "%DIR%..\scripts\mvwb.py" %*
)
