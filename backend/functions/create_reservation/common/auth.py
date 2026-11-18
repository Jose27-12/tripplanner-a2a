"""Extracción del user_id desde el contexto JWT de API Gateway.

El user_id NUNCA se acepta como parámetro del cliente —
siempre se extrae del token validado por el Cognito Authorizer.
"""


def get_user_id(event: dict) -> str:
    """Extrae el Cognito sub del JWT validado por API Gateway.

    Lanza KeyError si el contexto no contiene el claim — lo que indica
    que la Lambda fue invocada sin pasar por el Authorizer, lo cual
    no debería ocurrir en producción.
    """
    return event["requestContext"]["authorizer"]["claims"]["sub"]


def get_user_id_from_payload(payload: dict) -> str:
    """Extrae el user_id de un payload de invocación directa (desde los agentes).

    Los agentes inyectan el user_id después de validarlo con AgentCore;
    nunca lo reciben como parámetro libre del LLM.
    """
    user_id = payload.get("user_id")
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id ausente o inválido en el payload")
    return user_id
