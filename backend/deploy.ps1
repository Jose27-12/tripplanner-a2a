# ============================================================
# deploy.ps1 — Construye y despliega el backend (SAM)
#
#   .\deploy.ps1                                   (CORS = dominio de CloudFront)
#   .\deploy.ps1 -FrontendOrigin "*"               (solo para pruebas)
#
# Requisitos: AWS CLI + SAM CLI, Python 3.13 en el PATH (runtime de las Lambdas).
# ============================================================
param(
    [string]$FrontendOrigin = "https://d36x9vpivgz7mo.cloudfront.net",
    [string]$Stage = "prod"
)

# Los CLI nativos escriben progreso en stderr: se valida con $LASTEXITCODE.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$env:PYTHONUTF8 = "1"            # rutas con tildes en Windows
$env:SAM_CLI_TELEMETRY = "0"

Write-Host "==> Sincronizando common/ en cada Lambda..." -ForegroundColor Cyan
.\sync_common.ps1 | Out-Null

Write-Host "==> sam build..." -ForegroundColor Cyan
sam build
if ($LASTEXITCODE -ne 0) { throw "Fallo sam build" }

Write-Host "==> sam deploy (Stage=$Stage, FrontendOrigin=$FrontendOrigin)..." -ForegroundColor Cyan
sam deploy --stack-name TripPlannerBackend --region us-east-1 `
    --parameter-overrides "Stage=$Stage FrontendOrigin=$FrontendOrigin" `
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --resolve-s3 `
    --no-confirm-changeset --no-fail-on-empty-changeset
if ($LASTEXITCODE -ne 0) { throw "Fallo sam deploy" }

# SAM no crea un nuevo deployment de API Gateway cuando solo cambia un
# parámetro (p. ej. FrontendOrigin en el CORS): se publica explícitamente.
Write-Host "==> Publicando el stage '$Stage' de API Gateway..." -ForegroundColor Cyan
$apiId = aws cloudformation describe-stack-resource --stack-name TripPlannerBackend --region us-east-1 `
    --logical-resource-id TripPlannerApi --query "StackResourceDetail.PhysicalResourceId" --output text
aws apigateway create-deployment --rest-api-id $apiId --stage-name $Stage --region us-east-1 `
    --description "deploy.ps1 $(Get-Date -Format s)" --query id --output text | Out-Null
Write-Host "Backend desplegado." -ForegroundColor Green
