@echo off
setlocal
rem LEGACY compatibility wrapper. Keep this path for external Task Scheduler and shortcut callers.
chcp 65001 >nul
call "%~dp0start-lumenis-autostart.cmd"
set "exitCode=%ERRORLEVEL%"
endlocal & exit /b %exitCode%
