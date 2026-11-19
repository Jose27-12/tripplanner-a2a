"""POST /trips — Crea un nuevo viaje."""
import logging
from datetime import datetime, timezone

from ulid import ULID

from common.auth import get_user_id
from common.validation import parse_json_body
from common.db import table, pk, sk_trip
from common.response import created, bad_request, server_error
from common.validation import validate_trip

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        user_id = get_user_id(event)
        body, err = parse_json_body(event)
        if err:
            return bad_request(err)

        err = validate_trip(body)
        if err:
            return bad_request(err)

        trip_id = str(ULID())
        now = datetime.now(timezone.utc).isoformat()

        item = {
            "PK": pk(user_id),
            "SK": sk_trip(trip_id),
            "tripId": trip_id,
            "origen": body["origen"],
            "destino": body["destino"],
            "fecha_inicio": body["fecha_inicio"],
            "fecha_fin": body["fecha_fin"],
            "viajeros": int(body["viajeros"]),
            "presupuesto": body.get("presupuesto"),
            "moneda": body.get("moneda", "COP"),
            "estado": "PLANIFICANDO",
            "createdAt": now,
            "updatedAt": now,
        }

        table.put_item(Item=item)
        return created(_clean(item))
    except Exception:
        logger.exception("Error en CreateTrip")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}
