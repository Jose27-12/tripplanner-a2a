"""PUT /trips/{id}/itinerary — Actualiza el itinerario de un viaje."""
import logging
from datetime import datetime, timezone

from common.auth import get_user_id
from common.validation import parse_json_body
from common.db import table, get_item, pk, sk_itin
from common.response import ok, bad_request, not_found, server_error
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

        existing = get_item(user_id, sk_itin(trip_id))
        if not existing:
            return not_found("Itinerario no encontrado")

        err = validate_itinerary(body)
        if err:
            return bad_request(err)

        now = datetime.now(timezone.utc).isoformat()
        table.update_item(
            Key={"PK": pk(user_id), "SK": sk_itin(trip_id)},
            UpdateExpression="SET #dias = :dias, updatedAt = :ts",
            ExpressionAttributeNames={"#dias": "dias"},
            ExpressionAttributeValues={":dias": body["dias"], ":ts": now},
        )

        updated = get_item(user_id, sk_itin(trip_id))
        return ok(_clean(updated))
    except Exception:
        logger.exception("Error en UpdateItinerary")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}
