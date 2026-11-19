"""POST /reservations — Crea una reserva (estado inicial: SIMULADA)."""
import logging
from datetime import datetime, timezone

from ulid import ULID

from common.auth import get_user_id
from common.validation import parse_json_body
from common.db import table, get_item, pk, sk_trip, sk_res
from common.response import created, bad_request, not_found, server_error
from common.validation import validate_reservation

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        user_id = get_user_id(event)
        body, err = parse_json_body(event)
        if err:
            return bad_request(err)

        err = validate_reservation(body)
        if err:
            return bad_request(err)

        trip_id = body["tripId"]
        # El viaje debe existir y pertenecer al usuario
        trip = get_item(user_id, sk_trip(trip_id))
        if not trip:
            return not_found("Viaje no encontrado")

        res_id = str(ULID())
        now = datetime.now(timezone.utc).isoformat()

        item = {
            "PK": pk(user_id),
            "SK": sk_res(res_id),
            "GSI1PK": f"TRIP#{trip_id}",
            "GSI1SK": f"RES#{res_id}",
            "resId": res_id,
            "tripId": trip_id,
            "tipo": body["tipo"],
            "estado": "SIMULADA",          # siempre SIMULADA al crear
            "detalle": body.get("detalle", {}),
            "createdAt": now,
            "updatedAt": now,
        }

        table.put_item(Item=item)
        return created(_clean(item))
    except Exception:
        logger.exception("Error en CreateReservation")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK")}
