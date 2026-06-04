$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$preferredPython = "C:\ProgramData\anaconda3\python.exe"
Set-Location $projectRoot

if (Test-Path $preferredPython) {
    & $preferredPython -m http.server 8511
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m http.server 8511
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py -m http.server 8511
} else {
    throw "Python was not found on PATH. Install Python before serving the frontend."
}