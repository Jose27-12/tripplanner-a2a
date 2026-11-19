# ============================================================
# test_backend.ps1 — Pruebas del backend TripPlanner
# Sesión 4: flujo completo + pruebas negativas
# Uso: .\test_backend.ps1
# ============================================================

$ErrorActionPreference = "Continue"

# ── Configuración ────────────────────────────────────────────
$API       = "https://h4s4e8hqlg.execute-api.us-east-1.amazonaws.com/prod"
$POOL_ID   = "us-east-1_7ICuf3puR"
$CLIENT_ID = "752fpcc8a5ea2c09adrlq5iobt"
$REGION    = "us-east-1"

# Usuario de prueba — cámbialo si quieres
$TEST_EMAIL = "test-$(Get-Random)@tripplanner.dev"
$TEST_PASS  = "Test1234!"   # cumple: 8 chars, upper, lower, número

# ── Helpers ──────────────────────────────────────────────────
function OK   { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
$script:FAILS = 0
function FAIL { param($msg) $script:FAILS++; Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function INFO { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function SHOW { param($label,$val) Write-Host "      $label`: $val" -ForegroundColor Gray }

function Invoke-Api {
    param($Method, $Path, $Token = $null, $Body = $null)
    $headers = @{ "Content-Type" = "application/json" }
    if ($Token) { $headers["Authorization"] = "Bearer $Token" }
    $uri = "$API$Path"
    try {
        if ($Body) {
            $resp = Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers `
                -Body ($Body | ConvertTo-Json -Depth 10) -ErrorAction Stop
        } else {
            $resp = Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -ErrorAction Stop
        }
        return @{ ok = $true; data = $resp }
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $errBody = $reader.ReadToEnd() | ConvertFrom-Json
        } catch { $errBody = @{error = $_.Exception.Message} }
        return @{ ok = $false; status = $status; data = $errBody }
    }
}

function Invoke-Raw {
    param($Method, $Path, $Token = $null, $RawBody = $null, $ExtraHeaders = @{})
    $headers = @{} + $ExtraHeaders
    if ($Token) { $headers["Authorization"] = "Bearer $Token" }
    try {
        $p = @{ Method = $Method; Uri = "$API$Path"; Headers = $headers; UseBasicParsing = $true; ErrorAction = "Stop" }
        if ($RawBody) { $p["Body"] = $RawBody; $p["ContentType"] = "application/json" }
        $resp = Invoke-WebRequest @p
        return @{ status = [int]$resp.StatusCode; headers = $resp.Headers }
    } catch {
        $r = $_.Exception.Response
        return @{ status = [int]$r.StatusCode; headers = $r.Headers }
    }
}

function New-TestUser {
    param($Email)
    $su = aws cognito-idp sign-up --client-id $CLIENT_ID --username $Email --password $TEST_PASS --region $REGION 2>$null | ConvertFrom-Json
    aws cognito-idp admin-confirm-sign-up --user-pool-id $POOL_ID --username $Email --region $REGION 2>$null | Out-Null
    $a = aws cognito-idp admin-initiate-auth --user-pool-id $POOL_ID --client-id $CLIENT_ID `
        --auth-flow ADMIN_USER_PASSWORD_AUTH --auth-parameters "USERNAME=$Email,PASSWORD=$TEST_PASS" `
        --region $REGION 2>$null | ConvertFrom-Json
    return @{ sub = $su.UserSub; token = $a.AuthenticationResult.IdToken }
}

# ════════════════════════════════════════════════════════════
# PASO 1 — Registrar usuario en Cognito
# ════════════════════════════════════════════════════════════
INFO "PASO 1: Registrar usuario de prueba"
SHOW "Email" $TEST_EMAIL

$signUp = aws cognito-idp sign-up `
    --client-id $CLIENT_ID `
    --username $TEST_EMAIL `
    --password $TEST_PASS `
    --region $REGION 2>&1 | ConvertFrom-Json

if ($signUp.UserSub) {
    OK "Usuario registrado (sub: $($signUp.UserSub))"
} else {
    FAIL "Error al registrar: $signUp"
    exit 1
}

# ── Confirmar el usuario (auto-confirm para pruebas) ─────────
$confirm = aws cognito-idp admin-confirm-sign-up `
    --user-pool-id $POOL_ID `
    --username $TEST_EMAIL `
    --region $REGION 2>&1

OK "Usuario confirmado"

# ════════════════════════════════════════════════════════════
# PASO 2 — Autenticar y obtener token
# ════════════════════════════════════════════════════════════
INFO "PASO 2: Autenticar y obtener ID Token"

$authResult = aws cognito-idp admin-initiate-auth `
    --user-pool-id $POOL_ID `
    --client-id $CLIENT_ID `
    --auth-flow ADMIN_USER_PASSWORD_AUTH `
    --auth-parameters "USERNAME=$TEST_EMAIL,PASSWORD=$TEST_PASS" `
    --region $REGION 2>&1

$auth = $authResult | ConvertFrom-Json

$TOKEN = $auth.AuthenticationResult.IdToken
if ($TOKEN) {
    OK "Token obtenido (primeros 30 chars: $($TOKEN.Substring(0,30))...)"
} else {
    FAIL "No se pudo obtener token: $auth"
    exit 1
}

# ════════════════════════════════════════════════════════════
# PASO 3 — Pruebas negativas (sin token → 401)
# ════════════════════════════════════════════════════════════
INFO "PASO 3: Pruebas negativas"

$r = Invoke-Api -Method GET -Path "/trips"
if ($r.status -eq 401) { OK "GET /trips sin token → 401" }
else { FAIL "Se esperaba 401, llegó $($r.status)" }

# CORS: el preflight OPTIONS no lleva token y debe responder 2xx con cabeceras CORS
$r = Invoke-Raw -Method OPTIONS -Path "/trips" -ExtraHeaders @{ "Origin" = "https://example.com"; "Access-Control-Request-Method" = "GET"; "Access-Control-Request-Headers" = "authorization,content-type" }
if ($r.status -ge 200 -and $r.status -lt 300 -and $r.headers["Access-Control-Allow-Origin"]) { OK "Preflight OPTIONS sin token -> $($r.status) con CORS" }
else { FAIL "Preflight OPTIONS -> $($r.status) (CORS: $($r.headers['Access-Control-Allow-Origin']))" }

# CORS: el 401 que genera API Gateway debe traer Access-Control-Allow-Origin
$r = Invoke-Raw -Method GET -Path "/trips"
if ($r.status -eq 401 -and $r.headers["Access-Control-Allow-Origin"]) { OK "401 incluye cabecera CORS" }
else { FAIL "401 sin cabecera CORS (status $($r.status))" }

# ════════════════════════════════════════════════════════════
# PASO 4 — Crear viaje
# ════════════════════════════════════════════════════════════
INFO "PASO 4: Crear viaje"

$r = Invoke-Api -Method POST -Path "/trips" -Token $TOKEN -Body @{
    origen       = "Bogotá"
    destino      = "Cartagena"
    fecha_inicio = "2026-12-10"
    fecha_fin    = "2026-12-14"
    viajeros     = 3
    presupuesto  = 5000000
    moneda       = "COP"
}
if ($r.ok) {
    $TRIP_ID = $r.data.tripId
    OK "Viaje creado: tripId=$TRIP_ID"
    SHOW "Estado" $r.data.estado
} else {
    FAIL "Error al crear viaje: $($r.data.error)"
    exit 1
}

# ── Validación negativa: fecha_fin < fecha_inicio ────────────
$r = Invoke-Api -Method POST -Path "/trips" -Token $TOKEN -Body @{
    origen       = "Bogotá"
    destino      = "Medellín"
    fecha_inicio = "2026-12-14"
    fecha_fin    = "2026-12-10"
    viajeros     = 2
}
if ($r.status -eq 400) { OK "Fecha inválida → 400" }
else { FAIL "Se esperaba 400, llegó $($r.status)" }

# ── Validación negativa: viajeros = 0 ───────────────────────
$r = Invoke-Api -Method POST -Path "/trips" -Token $TOKEN -Body @{
    origen       = "Bogotá"
    destino      = "Medellín"
    fecha_inicio = "2026-12-10"
    fecha_fin    = "2026-12-14"
    viajeros     = 0
}
if ($r.status -eq 400) { OK "Viajeros=0 → 400" }
else { FAIL "Se esperaba 400, llegó $($r.status)" }

# ── Presupuesto con decimales (antes provocaba 500 en DynamoDB) ──
$r = Invoke-Api -Method POST -Path "/trips" -Token $TOKEN -Body @{
    origen       = "Bogota"
    destino      = "Santa Marta"
    fecha_inicio = "2027-01-10"
    fecha_fin    = "2027-01-12"
    viajeros     = 2
    presupuesto  = 1500000.50
}
if ($r.ok -and $r.data.presupuesto -eq 1500000.5) { OK "Presupuesto decimal -> 201 (presupuesto=$($r.data.presupuesto))" }
else { FAIL "Presupuesto decimal: status $($r.status) $($r.data.error)" }

# ── JSON inválido → 400 (antes 500) ──
$r = Invoke-Raw -Method POST -Path "/trips" -Token $TOKEN -RawBody "{esto no es json"
if ($r.status -eq 400) { OK "JSON invalido -> 400" }
else { FAIL "JSON invalido: se esperaba 400, llego $($r.status)" }

# ════════════════════════════════════════════════════════════
# PASO 5 — Listar viajes
# ════════════════════════════════════════════════════════════
INFO "PASO 5: Listar viajes"

$r = Invoke-Api -Method GET -Path "/trips" -Token $TOKEN
if ($r.ok -and $r.data.trips.Count -ge 1) {
    OK "GET /trips → $($r.data.trips.Count) viaje(s)"
} else {
    FAIL "Error al listar viajes: $($r.data)"
}

# ── Actualizar viaje (antes fallaba: DynamoDB devuelve viajeros como Decimal) ──
$r = Invoke-Api -Method PUT -Path "/trips/$TRIP_ID" -Token $TOKEN -Body @{ presupuesto = 5200000 }
if ($r.ok -and $r.data.presupuesto -eq 5200000 -and $r.data.viajeros -eq 3) { OK "PUT /trips/{id} -> presupuesto actualizado, viajeros sigue en 3" }
else { FAIL "PUT /trips/{id}: status $($r.status) $($r.data.error)" }

# ════════════════════════════════════════════════════════════
# PASO 6 — Crear itinerario
# ════════════════════════════════════════════════════════════
INFO "PASO 6: Crear itinerario"

$r = Invoke-Api -Method POST -Path "/trips/$TRIP_ID/itinerary" -Token $TOKEN -Body @{
    dias = @(
        @{ dia = 1; fecha = "2026-12-10"; actividades = @("Llegada", "Check-in", "Centro histórico") }
        @{ dia = 2; fecha = "2026-12-11"; actividades = @("Islas del Rosario", "Playa") }
        @{ dia = 3; fecha = "2026-12-12"; actividades = @("Castillo San Felipe", "Gastronomía") }
        @{ dia = 4; fecha = "2026-12-13"; actividades = @("Compras artesanías", "Vuelta a Bogotá") }
    )
}
if ($r.ok) { OK "Itinerario creado con $($r.data.dias.Count) días" }
else { FAIL "Error al crear itinerario: $($r.data.error)" }

# ════════════════════════════════════════════════════════════
# PASO 7 — Crear reserva (debe quedar SIMULADA)
# ════════════════════════════════════════════════════════════
INFO "PASO 7: Crear reserva"

$r = Invoke-Api -Method POST -Path "/reservations" -Token $TOKEN -Body @{
    tripId = $TRIP_ID
    tipo   = "VUELO"
    detalle = @{
        aerolinea  = "LATAM"
        vuelo      = "LA4410"
        salida     = "12:40"
        llegada    = "13:55"
        precio_usd = 76
    }
}
if ($r.ok) {
    $RES_ID = $r.data.resId
    OK "Reserva creada: resId=$RES_ID"
    if ($r.data.estado -eq "SIMULADA") { OK "Estado = SIMULADA OK" }
    else { FAIL "Estado deberia ser SIMULADA, es $($r.data.estado)" }
} else {
    FAIL "Error al crear reserva: $($r.data.error)"
}

# ── Validación negativa: campo de pago ───────────────────────
$r = Invoke-Api -Method POST -Path "/reservations" -Token $TOKEN -Body @{
    tripId = $TRIP_ID
    tipo   = "VUELO"
    detalle = @{ tarjeta = "4111111111111111"; cvv = "123" }
}
if ($r.status -eq 400) { OK "Campo de pago en detalle → 400" }
else { FAIL "Se esperaba 400 por campo de pago, llegó $($r.status)" }

# ── Dato de pago anidado o como valor → 400 ──
$r = Invoke-Api -Method POST -Path "/reservations" -Token $TOKEN -Body @{
    tripId = $TRIP_ID; tipo = "HOTEL"; detalle = @{ hotel = "Casa Pestagua"; pago = @{ cardNumber = "x" } }
}
if ($r.status -eq 400) { OK "Campo de pago anidado -> 400" }
else { FAIL "Campo de pago anidado: se esperaba 400, llego $($r.status)" }

$r = Invoke-Api -Method POST -Path "/reservations" -Token $TOKEN -Body @{
    tripId = $TRIP_ID; tipo = "ACTIVIDAD"; detalle = @{ nota = "pagar con 4111 1111 1111 1111" }
}
if ($r.status -eq 400) { OK "Numero de tarjeta en un valor -> 400" }
else { FAIL "Numero de tarjeta en valor: se esperaba 400, llego $($r.status)" }

# ── Validación negativa: tipo inválido ───────────────────────
$r = Invoke-Api -Method POST -Path "/reservations" -Token $TOKEN -Body @{
    tripId = $TRIP_ID
    tipo   = "TAXI"
    detalle = @{}
}
if ($r.status -eq 400) { OK "Tipo inválido TAXI → 400" }
else { FAIL "Se esperaba 400, llegó $($r.status)" }

# ════════════════════════════════════════════════════════════
# PASO 8 — Listar reservas
# ════════════════════════════════════════════════════════════
INFO "PASO 8: Listar reservas"

$r = Invoke-Api -Method GET -Path "/reservations" -Token $TOKEN
if ($r.ok) {
    OK "GET /reservations → $($r.data.reservations.Count) reserva(s)"
} else {
    FAIL "Error: $($r.data)"
}

# ── Filtrar por tripId ───────────────────────────────────────
$r = Invoke-Api -Method GET -Path "/reservations?tripId=$TRIP_ID" -Token $TOKEN
if ($r.ok) { OK "GET /reservations?tripId → $($r.data.reservations.Count) reserva(s)" }
else { FAIL "Error: $($r.data)" }

# ════════════════════════════════════════════════════════════
# PASO 9 — Avanzar estado de reserva
# ════════════════════════════════════════════════════════════
INFO "PASO 9: Avanzar estado reserva SIMULADA → PENDIENTE"

$r = Invoke-Api -Method PUT -Path "/reservations/$RES_ID" -Token $TOKEN -Body @{
    estado = "PENDIENTE"
}
if ($r.ok -and $r.data.estado -eq "PENDIENTE") { OK "Estado PENDIENTE OK" }
else { FAIL "Error: $($r.data)" }

# ── Validación negativa: salto de estado inválido ────────────
$r = Invoke-Api -Method PUT -Path "/reservations/$RES_ID" -Token $TOKEN -Body @{
    estado = "SIMULADA"
}
if ($r.status -eq 400) { OK "Retroceso de estado PENDIENTE→SIMULADA → 400" }
else { FAIL "Se esperaba 400, llegó $($r.status): $($r.data.error)" }

# ════════════════════════════════════════════════════════════
# PASO 10 — Preferencias
# ════════════════════════════════════════════════════════════
INFO "PASO 10: Preferencias"

$r = Invoke-Api -Method PUT -Path "/preferences" -Token $TOKEN -Body @{
    actividades           = @("playa", "gastronomia")
    presupuesto_tipo      = "MODERADO"
    aerolineas_preferidas = @("Avianca")
    asiento_preferido     = "ventana"
}
if ($r.ok) { OK "Preferencias guardadas" }
else { FAIL "Error: $($r.data.error)" }

$r = Invoke-Api -Method GET -Path "/preferences" -Token $TOKEN
if ($r.ok -and $r.data.aerolineas_preferidas) {
    OK "GET /preferences → aerolinea preferida: $($r.data.aerolineas_preferidas[0])"
} else {
    FAIL "Error al leer preferencias: $($r.data)"
}

# ════════════════════════════════════════════════════════════
# PASO 11 — Verificar aislamiento (viaje de otro usuario)
# ════════════════════════════════════════════════════════════
INFO "PASO 11: Aislamiento de datos entre usuarios"

# Intentar acceder a un tripId inventado
$r = Invoke-Api -Method GET -Path "/trips/FAKEID999" -Token $TOKEN
if ($r.status -eq 404) { OK "Viaje inexistente → 404 (no expone datos de otros usuarios)" }
else { FAIL "Se esperaba 404, llegó $($r.status)" }

# Usuario B intenta leer y modificar los datos del usuario A
$userB = New-TestUser -Email "test-b-$(Get-Random)@tripplanner.dev"
if (-not $userB.token) { FAIL "No se pudo crear el usuario B" }
else {
    $r = Invoke-Api -Method GET -Path "/trips/$TRIP_ID" -Token $userB.token
    if ($r.status -eq 404) { OK "Usuario B no ve el viaje de A -> 404" } else { FAIL "Usuario B GET viaje de A -> $($r.status)" }

    $r = Invoke-Api -Method PUT -Path "/trips/$TRIP_ID" -Token $userB.token -Body @{ viajeros = 9 }
    if ($r.status -eq 404) { OK "Usuario B no modifica el viaje de A -> 404" } else { FAIL "Usuario B PUT viaje de A -> $($r.status)" }

    $r = Invoke-Api -Method GET -Path "/reservations?tripId=$TRIP_ID" -Token $userB.token
    if ($r.ok -and $r.data.reservations.Count -eq 0) { OK "Usuario B no ve reservas de A" } else { FAIL "Usuario B ve reservas de A" }

    $r = Invoke-Api -Method PUT -Path "/reservations/$RES_ID" -Token $userB.token -Body @{ estado = "CONFIRMADA" }
    if ($r.status -eq 404) { OK "Usuario B no modifica la reserva de A -> 404" } else { FAIL "Usuario B PUT reserva de A -> $($r.status)" }
}

# ════════════════════════════════════════════════════════════
# RESUMEN
# ════════════════════════════════════════════════════════════
Write-Host "`n══════════════════════════════════════════" -ForegroundColor Yellow
if ($script:FAILS -eq 0) { Write-Host "  PRUEBAS COMPLETADAS: 0 fallos" -ForegroundColor Green }
else { Write-Host "  PRUEBAS COMPLETADAS: $($script:FAILS) fallo(s)" -ForegroundColor Red }
Write-Host "  Usuario de prueba: $TEST_EMAIL" -ForegroundColor Yellow
Write-Host "  tripId: $TRIP_ID" -ForegroundColor Yellow
Write-Host "  resId:  $RES_ID" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Verifica en DynamoDB:" -ForegroundColor White
Write-Host "  aws dynamodb scan --table-name TripPlannerTable-prod --region us-east-1 --output json | ConvertFrom-Json | Select -Expand Items" -ForegroundColor Gray

exit $script:FAILS
