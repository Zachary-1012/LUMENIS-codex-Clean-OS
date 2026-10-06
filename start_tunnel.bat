@echo off
setlocal
call "%~dp0deployment\start_remote.bat"
exit /b %ERRORLEVEL%
