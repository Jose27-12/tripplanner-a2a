"""Validaciones de negocio compartidas."""
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

TRIP_ESTADOS = {"PLANIFICANDO", "CONFIRMADO", "CANCELADO"}
RES_TIPOS = {"VUELO", "HOTEL", "ACTIVIDAD"}
RES_ESTADOS = {"SIMULADA", "PENDIENTE", "CONFIRMADA"}
PPTO_TIPOS = {"ECONOMICO", "MODERADO", "PREMIUM"}
MONEDAS = {"COP", "USD"}

# Rangos permitidos
MAX_VIAJEROS = 50
MAX_PRESUPUESTO = Decimal("1000000000000")   # 1 billón (cubre COP)
MAX_TEXTO = 120
MAX_DIAS_ITINERARIO = 60
MAX_ACTIVIDADES_DIA = 30

# Campos de pago prohibidos en cualquier payload (comparados ya normalizados:
# minúsculas y sin '_', '-' ni espacios, para cubrir cardNumber, card-number, etc.)
_PAYMENT_FIELDS = {
    "tarjeta", "card", "creditcard", "debitcard", "cvv", "cvc", "cvv2", "pin",
    "numerotarjeta", "cardnumber", "expiry", "expiracion", "fechaexpiracion",
    "expirationdate", "iban", "cuentabancaria", "accountnumber",
}
# Fragmentos que delatan un campo de pago aunque el nombre tenga prefijos/sufijos
_PAYMENT_FRAGMENTS = ("tarjeta", "cardnumber", "creditcard", "cvv", "cvc")

# Secuencia de 13–19 dígitos (con espacios o guiones opcionales): posible tarjeta
_CARD_LIKE = re.compile(r"(?:\d[ -]?){12,18}\d")


# ── Parsing del body ──────────────────────────────────────────────────────────

def parse_json_body(event: dict) -> tuple[dict, str | None]:
    """Parsea el body JSON del evento.

    Los números decimales se leen como Decimal porque DynamoDB no acepta float.
    Retorna (body, None) si es válido o ({}, mensaje_de_error) si no lo es.
    """
    raw = event.get("body") or "{}"
    try:
        body = json.loads(raw, parse_float=Decimal)
    except (ValueError, TypeError):
        return {}, "El body debe ser JSON válido"
    if not isinstance(body, dict):
        return {}, "El body debe ser un objeto JSON"
    return body, None


# ── Helpers de tipo ───────────────────────────────────────────────────────────

def _is_int(value) -> bool:
    """True para enteros (incluye Decimal entero que devuelve DynamoDB), nunca bool."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, Decimal):
        try:
            return value == value.to_integral_value()
        except InvalidOperation:
            return False
    return False


def _is_number(value) -> bool:
    """True para int, float o Decimal finitos, nunca bool."""
    if isinstance(value, bool):
        return False
    if isinstance(value, Decimal):
        return value.is_finite()
    return isinstance(value, (int, float))


def _is_text(value, max_len: int = MAX_TEXTO) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= max_len


# ── Anti-datos de pago ────────────────────────────────────────────────────────

def _normalize_key(key: str) -> str:
    return re.sub(r"[\s_\-]", "", str(key)).lower()


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _looks_like_card_number(value: str) -> bool:
    for match in _CARD_LIKE.finditer(value):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return True
    return False


def find_payment_data(obj, _path: str = "detalle") -> str | None:
    """Busca recursivamente campos o valores de pago. Retorna la ruta o None."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            norm = _normalize_key(key)
            path = f"{_path}.{key}"
            if norm in _PAYMENT_FIELDS or any(f in norm for f in _PAYMENT_FRAGMENTS):
                return path
            found = find_payment_data(value, path)
            if found:
                return found
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found = find_payment_data(item, f"{_path}[{i}]")
            if found:
                return found
    elif isinstance(obj, str) and _looks_like_card_number(obj):
        return _path
    return None


# ── Validaciones de entidades ────────────────────────────────────────────────

def validate_dates(fecha_inicio, fecha_fin) -> str | None:
    """Valida que las fechas sean ISO 8601 y que fin >= inicio.
    Retorna un mensaje de error o None si es válido.
    """
    if not isinstance(fecha_inicio, str) or not isinstance(fecha_fin, str):
        return "Las fechas deben estar en formato YYYY-MM-DD"
    try:
        ini = date.fromisoformat(fecha_inicio)
        fin = date.fromisoformat(fecha_fin)
    except ValueError:
        return "Las fechas deben estar en formato YYYY-MM-DD"
    if fin < ini:
        return "fecha_fin debe ser mayor o igual a fecha_inicio"
    return None


def validate_trip(body: dict) -> str | None:
    """Valida los campos de un viaje. Retorna mensaje de error o None."""
    required = ["origen", "destino", "fecha_inicio", "fecha_fin", "viajeros"]
    for field in required:
        if field not in body:
            return f"Campo requerido: {field}"

    for field in ("origen", "destino"):
        if not _is_text(body[field]):
            return f"{field} debe ser un texto de 1 a {MAX_TEXTO} caracteres"

    err = validate_dates(body["fecha_inicio"], body["fecha_fin"])
    if err:
        return err

    viajeros = body.get("viajeros")
    if not _is_int(viajeros) or not 1 <= viajeros <= MAX_VIAJEROS:
        return f"viajeros debe ser un entero entre 1 y {MAX_VIAJEROS}"

    presupuesto = body.get("presupuesto")
    if presupuesto is not None and (
        not _is_number(presupuesto) or not 0 < presupuesto <= MAX_PRESUPUESTO
    ):
        return "presupuesto debe ser un número positivo"

    moneda = body.get("moneda", "COP")
    if moneda not in MONEDAS:
        return f"moneda debe ser uno de: {', '.join(sorted(MONEDAS))}"

    estado = body.get("estado")
    if estado is not None and estado not in TRIP_ESTADOS:
        return f"estado debe ser uno de: {', '.join(sorted(TRIP_ESTADOS))}"

    return None


def validate_reservation(body: dict) -> str | None:
    """Valida los campos de una reserva. Retorna mensaje de error o None."""
    if "tripId" not in body:
        return "Campo requerido: tripId"
    if not _is_text(body["tripId"], 64):
        return "tripId inválido"
    if "tipo" not in body:
        return "Campo requerido: tipo"

    if body["tipo"] not in RES_TIPOS:
        return f"tipo debe ser uno de: {', '.join(sorted(RES_TIPOS))}"

    detalle = body.get("detalle", {})
    if not isinstance(detalle, dict):
        return "detalle debe ser un objeto"

    # Rechazar cualquier dato de pago, también en objetos anidados
    found = find_payment_data(detalle)
    if found:
        return f"No se permiten datos de pago en la reserva ({found})"

    return None


def validate_reservation_update(body: dict) -> str | None:
    """Valida la actualización de una reserva."""
    estado = body.get("estado")
    if estado is not None and estado not in RES_ESTADOS:
        return f"estado debe ser uno de: {', '.join(sorted(RES_ESTADOS))}"

    detalle = body.get("detalle", {})
    if not isinstance(detalle, dict):
        return "detalle debe ser un objeto"

    found = find_payment_data(detalle)
    if found:
        return f"No se permiten datos de pago en la reserva ({found})"

    return None


def validate_itinerary(body: dict) -> str | None:
    """Valida los campos de un itinerario."""
    dias = body.get("dias")
    if dias is None:
        return "Campo requerido: dias"
    if not isinstance(dias, list):
        return "dias debe ser una lista"
    if len(dias) > MAX_DIAS_ITINERARIO:
        return f"El itinerario admite como máximo {MAX_DIAS_ITINERARIO} días"
    for i, dia in enumerate(dias):
        if not isinstance(dia, dict):
            return f"dias[{i}] debe ser un objeto"
        if "dia" not in dia:
            return f"dias[{i}] falta campo: dia"
        if not _is_int(dia["dia"]) or dia["dia"] < 1:
            return f"dias[{i}].dia debe ser un entero >= 1"
        if "fecha" in dia:
            try:
                date.fromisoformat(dia["fecha"])
            except (TypeError, ValueError):
                return f"dias[{i}].fecha debe tener formato YYYY-MM-DD"
        if "actividades" not in dia:
            return f"dias[{i}] falta campo: actividades"
        if not isinstance(dia["actividades"], list):
            return f"dias[{i}].actividades debe ser una lista"
        if len(dia["actividades"]) > MAX_ACTIVIDADES_DIA:
            return f"dias[{i}] admite como máximo {MAX_ACTIVIDADES_DIA} actividades"
    if find_payment_data(dias, "dias"):
        return "No se permiten datos de pago en el itinerario"
    return None
