"""GET /trips/{id}/itinerary — Obtiene el itinerario de un viaje."""
import logging

from common.auth import get_user_id
from common.db import get_item, sk_itin
from common.response import ok, not_found, server_error

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        user_id = get_user_id(event)
        trip_id = event["pathParameters"]["id"]

        item = get_item(user_id, sk_itin(trip_id))
        if not item:
            return not_found("Itinerario no encontrado")

        return ok(_clean(item))
    except Exception:
        logger.exception("Error en GetItinerary")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}
