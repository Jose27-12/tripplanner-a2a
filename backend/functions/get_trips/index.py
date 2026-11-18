"""GET /trips — Lista todos los viajes del usuario autenticado."""
import logging
from common.auth import get_user_id
from common.db import query_by_prefix
from common.response import ok, server_error

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        user_id = get_user_id(event)
        items = query_by_prefix(user_id, "TRIP#")
        # Quitar las claves internas de DynamoDB antes de devolver
        trips = [_clean(item) for item in items]
        return ok({"trips": trips})
    except Exception:
        logger.exception("Error en GetTrips")
        return server_error()


def _clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}
