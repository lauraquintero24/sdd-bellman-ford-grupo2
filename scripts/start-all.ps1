# Lanzador para Windows 11 (PowerShell): Controller + un Router por nodo de la topología (C-32).
# Uso, desde la raíz del repositorio:
#   powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1 -Topology config\topology.json -ControllerPort 8000
# Requiere el entorno virtual .venv con requirements.txt instalado. Ctrl+C detiene todos los procesos.
param(
    [string]$Topology = "config/topology-demo.json",
    [string]$Routers = "config/routers.json",
    [int]$ControllerPort = 8000,
    [string]$SyncInterval = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "No se encontró $Python. Cree el entorno: python -m venv .venv; .venv\Scripts\python.exe -m pip install -r requirements.txt"
}

$Arguments = @((Join-Path $Root "scripts\start_all.py"), "--topology", $Topology, "--routers", $Routers,
               "--controller-port", $ControllerPort)
if ($SyncInterval -ne "") { $Arguments += @("--sync-interval", $SyncInterval) }

Push-Location $Root
try {
    & $Python @Arguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
