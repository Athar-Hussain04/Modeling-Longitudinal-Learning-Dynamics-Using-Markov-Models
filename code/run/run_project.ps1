param(
    [switch]$SkipPipeline,
    [switch]$NoBrowser
)

$runDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $runDir "..")
$pipelineRunner = Join-Path $runDir "run_pipeline.ps1"
$backendRunner = Join-Path $runDir "run_backend.ps1"
$frontendRunner = Join-Path $runDir "run_frontend.ps1"

$frontendScript = Get-Content $frontendRunner -Raw
$portMatch = [regex]::Match($frontendScript, "http\.server\s+(\d+)")
if (-not $portMatch.Success) {
    throw "Could not detect the frontend port from run_frontend.ps1."
}
$frontendPort = [int]$portMatch.Groups[1].Value
$frontendUrl = "http://127.0.0.1:$frontendPort/frontend/index.html"

Set-Location $projectRoot

$dashboard = Join-Path $projectRoot "outputs\backend\dashboard.json"
if (-not $SkipPipeline -and -not (Test-Path $dashboard)) {
    Write-Host "Running offline pipeline to generate dashboard.json..." -ForegroundColor Yellow
    & $pipelineRunner
}

Write-Host "Starting backend API in a new window..." -ForegroundColor Green
Start-Process powershell -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $backendRunner)

if (-not $NoBrowser) {
    Start-Sleep -Seconds 2
    Start-Process $frontendUrl
}

& $frontendRunner
