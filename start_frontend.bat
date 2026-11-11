@echo off
setlocal
pushd "%~dp0" || exit /b 1
"backend\.venv\Scripts\python.exe" -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
set "exitCode=%errorlevel%"
popd
exit /b %exitCode%
