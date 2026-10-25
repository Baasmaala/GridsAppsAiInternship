# starts the backend (in a new window) and the web app (in this window).
# run from the Task3 folder:
#   powershell -ExecutionPolicy Bypass -File tools\dev.ps1
# -Open waits for the backend, then opens the browser (start.bat uses it)

param([switch]$Open)

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

Set-Location (Join-Path $task3 "web")
$env:MASAR_PORT = $port

if (-not $Open) {
    Write-Host "Starting the web app. Open http://127.0.0.1:5173 (stop with Ctrl+C)"
    npm run dev
    exit
}

# if the page opens before the backend is up, it shows "cannot reach the api"
Write-Host "Waiting for the backend..."
$up = $false
for ($i = 0; $i -lt 60 -and -not $up; $i++) {
    try {
        Invoke-WebRequest "http://127.0.0.1:$port/api" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $up = $true
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $up) { Write-Host "The backend is slow to start. Look at its window. The page may need a refresh." -ForegroundColor Yellow }

Write-Host "Starting the web app. The browser opens by itself (stop with Ctrl+C)"
npm run dev -- --open
