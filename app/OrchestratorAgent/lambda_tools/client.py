"""Cliente Lambda compartido para las tools del Orchestrator.

El user_id NUNCA viene del LLM — se inyecta aquí desde el contexto
de sesión de AgentCore (actor_id validado por JWT).
"""
import json
import logging
import os
import boto3

logger = logging.getLogger(__name__)

_lambda = boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "us-east-1"))

# Prefijo de las Lambdas desplegadas (coincide con el template SAM)
_STAGE = os.environ.get("BACKEND_STAGE", "prod")
_PREFIX = f"TripPlanner-{{name}}-{_STAGE}"


def invoke_lambda(name: str, payload: dict) -> dict:
    """Invoca una Lambda del backend y devuelve el body parseado.

    name: nombre corto, ej. 'CreateTrip'
    payload: dict que se serializa como body + user_id inyectado
    """
    fn_name = _PREFIX.format(name=name)
    logger.info("Invocando Lambda %s", fn_name)

    response = _lambda.invoke(
        FunctionName=fn_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode(),
    )

    raw = response["Payload"].read()
    result = json.loads(raw)

    # Las Lambdas devuelven {statusCode, body}
    status = result.get("statusCode", 500)
    body_raw = result.get("body", "{}")
    body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw

    if status >= 400:
        error_msg = body.get("error", f"Error {status} en {name}")
        logger.warning("Lambda %s devolvio %d: %s", fn_name, status, error_msg)
        return {"error": error_msg, "statusCode": status}

    return body
