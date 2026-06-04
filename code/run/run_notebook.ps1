$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$notebookPath = Join-Path $projectRoot "notebook\vasstra_python.ipynb"
$preferredPython = "C:\ProgramData\anaconda3\python.exe"

Set-Location $projectRoot

if (Test-Path $preferredPython) {
    $python = $preferredPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = (Get-Command python).Source
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = (Get-Command py).Source
} else {
    throw "Python was not found on PATH. Install Python before launching the notebook."
}

if (-not (Test-Path $notebookPath)) {
    throw "Notebook not found at $notebookPath."
}

Write-Host "Ensuring JupyterLab is available..." -ForegroundColor Yellow
& $python -m pip install --quiet jupyterlab nbformat 2>&1 | Out-Null

Write-Host "Launching the Python VaSSTra notebook (Ctrl+C to stop)..." -ForegroundColor Green
& $python -m jupyter lab $notebookPath
