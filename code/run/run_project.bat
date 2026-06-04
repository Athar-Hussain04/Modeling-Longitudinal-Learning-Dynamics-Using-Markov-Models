@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_project.ps1" %*
set "exit_code=%ERRORLEVEL%"
if not "%exit_code%"=="0" (
    echo.
    echo The launcher exited with code %exit_code%.
    pause
)
endlocal & exit /b %exit_code%