# ============================================================
# sync_common.ps1 — Copia el paquete common/ dentro de cada Lambda
#
# El código fuente vive en backend/common/python/common/. Cada función
# lleva su propia copia en functions/<nombre>/common/ porque el Layer de
# SAM no se construye bien en arm64 desde Windows sin Docker.
#
# Ejecutar SIEMPRE antes de `sam build` si se editó algo en common/.
# Uso: .\sync_common.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $root "common\python\common"

Get-ChildItem (Join-Path $root "functions") -Directory | ForEach-Object {
    $dest = Join-Path $_.FullName "common"
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
    Copy-Item -Recurse -Force $source $dest
    Get-ChildItem $dest -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
    Write-Host "common/ sincronizado en $($_.Name)"
}
