$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python -m pip install -r requirements.txt
Write-Host "Starte XRechnungsreader mit normalem Flet-Client ..." -ForegroundColor Cyan
flet run main.py
