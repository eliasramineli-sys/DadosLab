$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check-Native { if ($LASTEXITCODE -ne 0) { throw "Comando falhou com código $LASTEXITCODE. Leia o erro acima." } }
if (-not (Test-Path ".venv/Scripts/python.exe")) {
    py -3.12 -m venv .venv
    Check-Native
}
$Python = Join-Path $PWD ".venv/Scripts/python.exe"
& $Python -m pip install -r requirements-dev.txt
Check-Native
& $Python scripts/build.py
Check-Native
& $Python -m pytest -q
Check-Native
& $Python scripts/package_windows.py
Check-Native
Write-Host "Pronto: abra dist/DadosLab/DadosLab.exe. Mantenha toda a pasta junta." -ForegroundColor Green
