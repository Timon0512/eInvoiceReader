$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python -m pip install -r requirements.txt
Write-Host "Erzeuge den Windows-Release-Build ..." -ForegroundColor Cyan
flet build windows . --clear-cache --product "XRechnungsreader" --artifact "XRechnungsreader" -v
Write-Host "Build abgeschlossen: build\windows\XRechnungsreader.exe" -ForegroundColor Green
