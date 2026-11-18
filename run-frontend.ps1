# Menjalankan frontend React (Vite) JudolGuard (http://localhost:5173)
# Pemakaian: .\run-frontend.ps1          (server pengembangan)
#            .\run-frontend.ps1 -Build   (build produksi ke frontend/dist)
param([switch]$Build)
$ErrorActionPreference = 'Stop'
Set-Location "$PSScriptRoot\frontend"

if (-not (Test-Path 'node_modules')) {
    Write-Host 'Menginstal dependensi npm ...' -ForegroundColor Cyan
    npm install
}
if ($Build) {
    npm run build
} else {
    npm run dev
}
