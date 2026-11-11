Push-Location -LiteralPath $PSScriptRoot
try {
    .\backend\.venv\Scripts\python.exe -m streamlit run frontend/app.py
    $streamlitExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $streamlitExitCode
