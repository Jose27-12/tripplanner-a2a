"""GET /reservations — Lista reservas del usuario. Acepta ?tripId= para filtrar."""
import logging

from common.auth import get_user_id
from common.db import query_by_prefix, query_gsi1
from common.response import ok, server_error

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        user_id = get_user_id(event)
        params = event.get("queryStringParameters") or {}
        trip_id = params.get("tripId")

        if trip_id:
            # Filtrar por viaje usando GSI1 — solo devuelve reservas de ese viaje
            items = query_gsi1(trip_id)
            # Filtro adicional: verificar que el PK coincide con el usuario
            # (evita que un usuario vea reservas de otro si adivinara un tripId)
            items = [i for i in items if i.get("PK") == f"USER#{user_id}"]
        else:
            items = query_by_prefix(user_id, "RES#")

        return ok({"reservations": [_clean(i) for i in items]})
    except Exception:
        logger.exception("Error en GetReservations")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK")}
