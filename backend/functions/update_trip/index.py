"""PUT /trips/{id} — Actualiza un viaje existente."""
import logging
from datetime import datetime, timezone

from common.auth import get_user_id
from common.validation import parse_json_body
from common.db import table, get_item, pk, sk_trip
from common.response import ok, bad_request, not_found, server_error
from common.validation import validate_trip, TRIP_ESTADOS

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Campos que el cliente puede actualizar
_ALLOWED = {
    "origen", "destino", "fecha_inicio", "fecha_fin",
    "viajeros", "presupuesto", "moneda", "estado",
}


def handler(event, context):
    try:
        user_id = get_user_id(event)
        trip_id = event["pathParameters"]["id"]
        body, err = parse_json_body(event)
        if err:
            return bad_request(err)

        # Verificar que el viaje existe y pertenece al usuario
        existing = get_item(user_id, sk_trip(trip_id))
        if not existing:
            return not_found("Viaje no encontrado")

        # Mezclar con los valores actuales para validar el objeto completo
        merged = {**_clean(existing), **{k: v for k, v in body.items() if k in _ALLOWED}}
        err = validate_trip(merged)
        if err:
            return bad_request(err)

        # Construir expresión de actualización dinámica
        now = datetime.now(timezone.utc).isoformat()
        updates = {k: v for k, v in body.items() if k in _ALLOWED}
        updates["updatedAt"] = now

        expr_parts = []
        expr_values = {}
        expr_names = {}
        for i, (k, v) in enumerate(updates.items()):
            placeholder = f":v{i}"
            name_placeholder = f"#n{i}"
            expr_parts.append(f"{name_placeholder} = {placeholder}")
            expr_values[placeholder] = v
            expr_names[name_placeholder] = k

        table.update_item(
            Key={"PK": pk(user_id), "SK": sk_trip(trip_id)},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names,
        )

        # Leer el item actualizado para devolverlo
        updated = get_item(user_id, sk_trip(trip_id))
        return ok(_clean(updated))
    except Exception:
        logger.exception("Error en UpdateTrip")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}
