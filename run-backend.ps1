# Menjalankan backend Flask JudolGuard (http://127.0.0.1:5000)
# Pemakaian: .\run-backend.ps1            (jalankan server)
#            .\run-backend.ps1 -Install   (paksa install ulang dependensi)
#            .\run-backend.ps1 -Test      (jalankan pytest)
param([switch]$Install, [switch]$Test)
$ErrorActionPreference = 'Stop'
Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'Membuat virtualenv Python 3.12 ...' -ForegroundColor Cyan
    python -m venv .venv
    $Install = $true
}
if ($Install) {
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
}
if ($Test) {
    .\.venv\Scripts\python.exe -m pytest -v
    exit $LASTEXITCODE
}
.\.venv\Scripts\python.exe wsgi.py
