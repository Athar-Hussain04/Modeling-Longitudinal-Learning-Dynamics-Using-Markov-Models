$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendScript = Join-Path $projectRoot "backend\run_vasstra_pipeline.py"
$preferredPython = "C:\ProgramData\anaconda3\python.exe"

Set-Location $projectRoot
if (Test-Path $preferredPython) {
    & $preferredPython $backendScript
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python $backendScript
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py $backendScript
} else {
    throw "Python was not found on PATH. Install Python before running the pipeline."
}
