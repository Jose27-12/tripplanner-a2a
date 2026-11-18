"""PUT /reservations/{id} — Actualiza una reserva (estado, detalle)."""
import json
import logging
from datetime import datetime, timezone

from common.auth import get_user_id
from common.db import table, get_item, pk, sk_res
from common.response import ok, bad_request, not_found, server_error
from common.validation import validate_reservation_update, RES_ESTADOS

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Secuencia de avance de estado permitida
_NEXT_ESTADO = {
    "SIMULADA": {"SIMULADA", "PENDIENTE"},
    "PENDIENTE": {"PENDIENTE", "CONFIRMADA"},
    "CONFIRMADA": {"CONFIRMADA"},
}


def handler(event, context):
    try:
        user_id = get_user_id(event)
        res_id = event["pathParameters"]["id"]
        body = json.loads(event.get("body") or "{}")

        existing = get_item(user_id, sk_res(res_id))
        if not existing:
            return not_found("Reserva no encontrada")

        err = validate_reservation_update(body)
        if err:
            return bad_request(err)

        # Validar secuencia de estado
        new_estado = body.get("estado")
        if new_estado:
            current = existing.get("estado", "SIMULADA")
            if new_estado not in _NEXT_ESTADO.get(current, set()):
                return bad_request(
                    f"No se puede cambiar estado de {current} a {new_estado}. "
                    f"Secuencia válida: SIMULADA → PENDIENTE → CONFIRMADA"
                )

        now = datetime.now(timezone.utc).isoformat()
        updates = {}
        if new_estado:
            updates["estado"] = new_estado
        if "detalle" in body:
            updates["detalle"] = body["detalle"]
        updates["updatedAt"] = now

        expr_parts = []
        expr_values = {}
        expr_names = {}
        for i, (k, v) in enumerate(updates.items()):
            ph = f":v{i}"
            nm = f"#n{i}"
            expr_parts.append(f"{nm} = {ph}")
            expr_values[ph] = v
            expr_names[nm] = k

        table.update_item(
            Key={"PK": pk(user_id), "SK": sk_res(res_id)},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names,
        )

        updated = get_item(user_id, sk_res(res_id))
        return ok(_clean(updated))
    except Exception:
        logger.exception("Error en UpdateReservation")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK")}
