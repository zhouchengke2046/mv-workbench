@echo off
chcp 65001 >nul
cd /d "%~dp0.."

set "PY=python"
where py >nul 2>nul && set "PY=py -3"

echo MV 工作台 · Key 配置
echo 输入不回显；Key 只保存在本机 %%USERPROFILE%%\.config\mv-workbench\keys.json
echo.

%PY% scripts\mv_keys.py init
if errorlevel 1 goto fail
%PY% scripts\mv_keys.py set runninghub
if errorlevel 1 goto fail
%PY% scripts\mv_keys.py set router
if errorlevel 1 goto fail

echo.
echo 两个 Key 已保存。可以关闭这个窗口，回到 agent 继续。
pause
exit /b 0

:fail
echo.
echo 配置失败。请确认已安装 Python 3.9+，然后把上面的报错发给 agent。
pause
exit /b 1
