# starts the backend (in a new window) and the web app (in this window).
# run from the Task3 folder:
#   powershell -ExecutionPolicy Bypass -File tools\dev.ps1

$ErrorActionPreference = "Stop"
$task3 = Split-Path -Parent $PSScriptRoot
$port = if ($env:MASAR_PORT) { $env:MASAR_PORT } else { "8001" }

foreach ($tool in "uv", "npm") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Host "$tool is not installed. See README.md, step 1." -ForegroundColor Red
        exit 1
    }
}

foreach ($p in $port, 5173) {
    $used = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($used) {
        Write-Host "Port $p is already in use. Close the program that uses it, or set another backend port with `$env:MASAR_PORT." -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path (Join-Path $task3 "web\node_modules"))) {
    Write-Host "The web packages are missing. Run: cd web; npm ci; cd .." -ForegroundColor Red
    exit 1
}

Write-Host "Starting the backend on http://127.0.0.1:$port in a new window..."
Start-Process powershell -WorkingDirectory $task3 -ArgumentList "-NoExit", "-Command",
    "`$env:MASAR_PORT = '$port'; uv run python -m api"

Write-Host "Starting the web app. Open http://127.0.0.1:5173 (stop with Ctrl+C)"
Set-Location (Join-Path $task3 "web")
$env:MASAR_PORT = $port
npm run dev
