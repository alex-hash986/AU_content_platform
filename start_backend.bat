@echo off
setlocal
pushd "%~dp0backend" || exit /b 1
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
set "exitCode=%errorlevel%"
popd
exit /b %exitCode%
