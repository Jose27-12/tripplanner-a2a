"""Validaciones de negocio compartidas."""
from datetime import date

TRIP_ESTADOS = {"PLANIFICANDO", "CONFIRMADO", "CANCELADO"}
RES_TIPOS = {"VUELO", "HOTEL", "ACTIVIDAD"}
RES_ESTADOS = {"SIMULADA", "PENDIENTE", "CONFIRMADA"}
PPTO_TIPOS = {"ECONOMICO", "MODERADO", "PREMIUM"}
MONEDAS = {"COP", "USD"}

# Campos de pago prohibidos en cualquier payload
_PAYMENT_FIELDS = {
    "tarjeta", "card", "credit_card", "cvv", "cvc", "pin",
    "numero_tarjeta", "card_number", "expiry", "expiracion",
}


def validate_dates(fecha_inicio: str, fecha_fin: str) -> str | None:
    """Valida que las fechas sean ISO 8601 y que fin >= inicio.
    Retorna un mensaje de error o None si es válido.
    """
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

    err = validate_dates(body["fecha_inicio"], body["fecha_fin"])
    if err:
        return err

    viajeros = body.get("viajeros")
    if not isinstance(viajeros, int) or viajeros < 1:
        return "viajeros debe ser un entero >= 1"

    presupuesto = body.get("presupuesto")
    if presupuesto is not None and (not isinstance(presupuesto, (int, float)) or presupuesto <= 0):
        return "presupuesto debe ser un número positivo"

    moneda = body.get("moneda", "COP")
    if moneda not in MONEDAS:
        return f"moneda debe ser uno de: {', '.join(MONEDAS)}"

    estado = body.get("estado")
    if estado is not None and estado not in TRIP_ESTADOS:
        return f"estado debe ser uno de: {', '.join(TRIP_ESTADOS)}"

    return None


def validate_reservation(body: dict) -> str | None:
    """Valida los campos de una reserva. Retorna mensaje de error o None."""
    if "tripId" not in body:
        return "Campo requerido: tripId"
    if "tipo" not in body:
        return "Campo requerido: tipo"

    if body["tipo"] not in RES_TIPOS:
        return f"tipo debe ser uno de: {', '.join(RES_TIPOS)}"

    detalle = body.get("detalle", {})
    if not isinstance(detalle, dict):
        return "detalle debe ser un objeto"

    # Rechazar cualquier campo de pago
    forbidden = _PAYMENT_FIELDS & {k.lower() for k in detalle}
    if forbidden:
        return f"Campos no permitidos en detalle: {', '.join(forbidden)}"

    return None


def validate_reservation_update(body: dict) -> str | None:
    """Valida la actualización de una reserva."""
    estado = body.get("estado")
    if estado is not None and estado not in RES_ESTADOS:
        return f"estado debe ser uno de: {', '.join(RES_ESTADOS)}"

    detalle = body.get("detalle", {})
    if not isinstance(detalle, dict):
        return "detalle debe ser un objeto"

    forbidden = _PAYMENT_FIELDS & {k.lower() for k in detalle}
    if forbidden:
        return f"Campos no permitidos en detalle: {', '.join(forbidden)}"

    return None


def validate_itinerary(body: dict) -> str | None:
    """Valida los campos de un itinerario."""
    dias = body.get("dias")
    if dias is None:
        return "Campo requerido: dias"
    if not isinstance(dias, list):
        return "dias debe ser una lista"
    for i, dia in enumerate(dias):
        if not isinstance(dia, dict):
            return f"dias[{i}] debe ser un objeto"
        if "dia" not in dia:
            return f"dias[{i}] falta campo: dia"
        if "actividades" not in dia:
            return f"dias[{i}] falta campo: actividades"
        if not isinstance(dia["actividades"], list):
            return f"dias[{i}].actividades debe ser una lista"
    return None
