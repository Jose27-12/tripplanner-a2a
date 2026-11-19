"""Respuestas HTTP estándar para todas las Lambdas."""
import json
import os
from decimal import Decimal

_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": _ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    "Content-Type": "application/json",
}


def _json_default(value):
    """DynamoDB devuelve los números como Decimal: se serializan como número JSON."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return str(value)


def _build(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": _CORS_HEADERS,
        "body": json.dumps(body, default=_json_default, ensure_ascii=False),
    }


def ok(body: dict) -> dict:
    return _build(200, body)


def created(body: dict) -> dict:
    return _build(201, body)


def bad_request(message: str) -> dict:
    return _build(400, {"error": message})


def forbidden(message: str = "Acceso denegado") -> dict:
    return _build(403, {"error": message})


def not_found(message: str = "Recurso no encontrado") -> dict:
    return _build(404, {"error": message})


def server_error() -> dict:
    # Nunca exponer detalles internos en producción
    return _build(500, {"error": "Error interno del servidor"})
