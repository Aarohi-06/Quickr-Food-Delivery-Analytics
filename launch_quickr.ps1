# Run from PowerShell: .\launch_quickr.ps1
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectDirectory
$appPython = Join-Path $projectDirectory '.venv-ml\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $appPython)) {
    throw 'Missing .venv-ml. Follow README.md Spark ML installation instructions.'
}
& $appPython -m streamlit run app/app.py --server.address 127.0.0.1
