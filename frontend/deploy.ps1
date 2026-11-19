# ============================================================
# deploy.ps1 — Publica el frontend en S3 + CloudFront
#
#   1. Crea/actualiza el stack TripPlannerFrontend (infra/template.yaml)
#   2. npm run build (usa .env.production)
#   3. Sube dist/ al bucket privado (assets con caché larga, index.html sin caché)
#   4. Invalida la caché de CloudFront
#
# Uso: .\deploy.ps1            (desde frontend/)
#      .\deploy.ps1 -SkipInfra (solo build + subida)
# ============================================================
param([switch]$SkipInfra)

# Los CLI nativos escriben progreso en stderr: se valida con $LASTEXITCODE.
$ErrorActionPreference = "Continue"
$Region = "us-east-1"
$Stack = "TripPlannerFrontend"
Set-Location $PSScriptRoot

if (-not $SkipInfra) {
    Write-Host "==> Desplegando infraestructura ($Stack)..." -ForegroundColor Cyan
    aws cloudformation deploy --stack-name $Stack --template-file infra/template.yaml `
        --region $Region --no-fail-on-empty-changeset
    if ($LASTEXITCODE -ne 0) { throw "Fallo el despliegue de la infraestructura" }
}

$outputs = aws cloudformation describe-stacks --stack-name $Stack --region $Region `
    --query "Stacks[0].Outputs" --output json | ConvertFrom-Json
$bucket = ($outputs | Where-Object OutputKey -eq "BucketName").OutputValue
$distId = ($outputs | Where-Object OutputKey -eq "DistributionId").OutputValue
$url    = ($outputs | Where-Object OutputKey -eq "SiteUrl").OutputValue

Write-Host "==> Compilando..." -ForegroundColor Cyan
npm run build
if ($LASTEXITCODE -ne 0) { throw "Fallo el build" }

Write-Host "==> Subiendo a s3://$bucket ..." -ForegroundColor Cyan
# Archivos con hash en el nombre: caché de 1 año
aws s3 sync dist/assets "s3://$bucket/assets" --region $Region --delete `
    --cache-control "public,max-age=31536000,immutable"
# Resto (index.html, favicon): siempre revalidar
aws s3 sync dist "s3://$bucket" --region $Region --delete --exclude "assets/*" `
    --cache-control "no-cache"

Write-Host "==> Invalidando CloudFront ($distId)..." -ForegroundColor Cyan
aws cloudfront create-invalidation --distribution-id $distId --paths "/*" --query "Invalidation.Id" --output text | Out-Null

Write-Host "`nListo: $url" -ForegroundColor Green
