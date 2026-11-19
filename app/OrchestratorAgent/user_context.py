"""Identidad del usuario autenticado en la invocación actual.

INVARIANTE DE SEGURIDAD: el user_id NUNCA viene del LLM ni del payload que
envía el navegador. Se obtiene del claim `sub` del JWT de Cognito que llega
en la cabecera Authorization.

La firma, el emisor (issuer) y el client_id/audiencia del token ya los valida
el authorizer CUSTOM_JWT de AgentCore Runtime antes de que la petición llegue
al contenedor (ver authorizerConfiguration en agentcore/agentcore.json), por
eso aquí solo se decodifica el payload para leer `sub`.

El valor se guarda en un ContextVar: cada invocación tiene su propio contexto
(y las tools síncronas que Strands ejecuta en hilos heredan una copia), así que
dos peticiones concurrentes no pueden mezclar identidades.
"""
import base64
import json
import os
from contextvars import ContextVar, Token
from typing import Any, Mapping

_current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)

# Solo para `agentcore dev` en local (sin authorizer delante). Nunca se define
# en agentcore.json, así que en AWS no existe.
_LOCAL_DEV_USER_ENV = "LOCAL_DEV_USER_ID"


class UnauthenticatedError(Exception):
    """La invocación no trae un JWT válido con claim `sub`."""


def _sub_from_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token.count(".") != 2:
        return None
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
    except (ValueError, TypeError):
        return None
    sub = claims.get("sub") if isinstance(claims, dict) else None
    return sub if isinstance(sub, str) and sub else None


def resolve_user_id(context: Any) -> str:
    """Obtiene el user_id (Cognito sub) del contexto de la petición de AgentCore."""
    headers: Mapping[str, str] = getattr(context, "request_headers", None) or {}
    authorization = next(
        (v for k, v in headers.items() if k.lower() == "authorization"), None
    )
    sub = _sub_from_bearer(authorization)
    if sub:
        return sub

    dev_user = os.environ.get(_LOCAL_DEV_USER_ENV)
    if dev_user:
        return dev_user

    raise UnauthenticatedError("Se requiere un token de Cognito (Authorization: Bearer ...)")


def set_current_user_id(user_id: str) -> Token:
    return _current_user_id.set(user_id)


def reset_current_user_id(token: Token) -> None:
    _current_user_id.reset(token)


def current_user_id() -> str:
    """user_id de la invocación en curso. Falla si no hay usuario autenticado."""
    user_id = _current_user_id.get()
    if not user_id:
        raise UnauthenticatedError("No hay usuario autenticado en esta invocación")
    return user_id
