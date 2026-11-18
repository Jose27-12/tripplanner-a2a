"""GET /preferences — Obtiene las preferencias del usuario."""
import logging

from common.auth import get_user_id
from common.db import get_item, sk_prefs
from common.response import ok, server_error

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        user_id = get_user_id(event)
        item = get_item(user_id, sk_prefs())
        if not item:
            return ok({})   # Sin preferencias guardadas aún → objeto vacío
        return ok(_clean(item))
    except Exception:
        logger.exception("Error en GetPreferences")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}
