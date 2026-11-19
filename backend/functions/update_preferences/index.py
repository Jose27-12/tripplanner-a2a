"""PUT /preferences — Crea o reemplaza las preferencias del usuario."""
import logging
from datetime import datetime, timezone

from common.auth import get_user_id
from common.validation import parse_json_body, find_payment_data
from common.db import table, pk, sk_prefs
from common.response import ok, bad_request, server_error
from common.validation import PPTO_TIPOS

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_ALLOWED_KEYS = {
    "actividades", "presupuesto_tipo", "restricciones",
    "aerolineas_preferidas", "asiento_preferido",
}


def handler(event, context):
    try:
        user_id = get_user_id(event)
        body, err = parse_json_body(event)
        if err:
            return bad_request(err)

        if find_payment_data(body, "preferencias"):
            return bad_request("No se permiten datos de pago en las preferencias")

        ppto = body.get("presupuesto_tipo")
        if ppto and ppto not in PPTO_TIPOS:
            return bad_request(f"presupuesto_tipo debe ser uno de: {', '.join(PPTO_TIPOS)}")

        now = datetime.now(timezone.utc).isoformat()
        item = {
            "PK": pk(user_id),
            "SK": sk_prefs(),
            "updatedAt": now,
        }
        # Solo guardar los campos permitidos
        for k in _ALLOWED_KEYS:
            if k in body:
                item[k] = body[k]

        table.put_item(Item=item)
        return ok(_clean(item))
    except Exception:
        logger.exception("Error en UpdatePreferences")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}
