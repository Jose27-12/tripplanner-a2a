"""GET /trips/{id} — Obtiene un viaje por ID."""
import logging

from common.auth import get_user_id
from common.db import get_item, sk_trip
from common.response import ok, not_found, server_error

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        user_id = get_user_id(event)
        trip_id = event["pathParameters"]["id"]

        item = get_item(user_id, sk_trip(trip_id))
        if not item:
            return not_found("Viaje no encontrado")

        return ok(_clean(item))
    except Exception:
        logger.exception("Error en GetTrip")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}
