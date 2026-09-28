# Build backend Python -> backend-dist\server.exe (PyInstaller onedir)
# Chạy từ thư mục repo root: powershell -File desktop\build-backend.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

pyinstaller --onedir --name server `
  --distpath backend-dist `
  --workpath build\pyinstaller `
  --specpath build `
  --collect-all playwright `
  --hidden-import aiohttp `
  --hidden-import winocr `
  backend\server.py

Write-Host "Built: $root\backend-dist\server\server.exe"
