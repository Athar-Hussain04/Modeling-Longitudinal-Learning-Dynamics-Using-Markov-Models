$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$apiPort = 9511
$preferredPython = "C:\ProgramData\anaconda3\python.exe"

Set-Location $projectRoot

if (Test-Path $preferredPython) {
    $python = $preferredPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = (Get-Command python).Source
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = (Get-Command py).Source
} else {
    throw "Python was not found on PATH. Install Python before starting the API."
}

& $python -m pip install --quiet fastapi "uvicorn[standard]" pydantic joblib scikit-learn pandas numpy openpyxl 2>&1 | Out-Null

$dashboard = Join-Path $projectRoot "outputs\backend\dashboard.json"
if (-not (Test-Path $dashboard)) {
    Write-Host "dashboard.json not found, running pipeline first..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "run_pipeline.ps1")
}

Write-Host "Starting FastAPI on http://127.0.0.1:$apiPort (Ctrl+C to stop)" -ForegroundColor Green
& $python -m uvicorn backend.api:app --host 127.0.0.1 --port $apiPort
