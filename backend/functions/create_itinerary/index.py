"""POST /trips/{id}/itinerary — Crea o reemplaza el itinerario de un viaje."""
import logging
from datetime import datetime, timezone

from common.auth import get_user_id
from common.validation import parse_json_body
from common.db import table, get_item, pk, sk_trip, sk_itin
from common.response import created, bad_request, not_found, server_error
from common.validation import validate_itinerary

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        user_id = get_user_id(event)
        trip_id = event["pathParameters"]["id"]
        body, err = parse_json_body(event)
        if err:
            return bad_request(err)

        # El viaje debe existir y pertenecer al usuario
        trip = get_item(user_id, sk_trip(trip_id))
        if not trip:
            return not_found("Viaje no encontrado")

        err = validate_itinerary(body)
        if err:
            return bad_request(err)

        now = datetime.now(timezone.utc).isoformat()
        item = {
            "PK": pk(user_id),
            "SK": sk_itin(trip_id),
            "tripId": trip_id,
            "dias": body["dias"],
            "updatedAt": now,
        }

        table.put_item(Item=item)
        return created(_clean(item))
    except Exception:
        logger.exception("Error en CreateItinerary")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}
