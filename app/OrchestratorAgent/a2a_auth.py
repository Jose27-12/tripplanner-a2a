"""Clientes A2A autenticados hacia FlightsAgent y WeatherAgent.

En AWS los especialistas son runtimes de AgentCore con autorización IAM, así
que cada petición HTTP del Orchestrator se firma con SigV4 usando el rol de
ejecución del Orchestrator (permiso bedrock-agentcore:InvokeAgentRuntime).

Además se envía la cabecera X-Amzn-Bedrock-AgentCore-Runtime-User-Id con el
usuario actual: con ella AgentCore emite el Workload Access Token del
especialista, que este necesita para leer su credencial de Gemini desde
AgentCore Identity (requiere bedrock-agentcore:InvokeAgentRuntimeForUser).

En local (endpoints http://localhost) no se firma nada.
"""
import os
from urllib.parse import urlparse

import boto3
import httpx
from a2a.client import ClientConfig
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

USER_ID_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-User-Id"
_SERVICE = "bedrock-agentcore"
_TIMEOUT = httpx.Timeout(300.0, connect=10.0)


class SigV4HttpxAuth(httpx.Auth):
    """Firma cada petición httpx con SigV4 (credenciales del rol en ejecución)."""

    requires_request_body = True

    def __init__(self, region: str):
        self._region = region
        self._session = boto3.Session()

    def auth_flow(self, request: httpx.Request):
        credentials = self._session.get_credentials().get_frozen_credentials()
        # Solo se firman host, content-type y las cabeceras x-amz*: el resto de
        # cabeceras que añada httpx no forman parte de la firma.
        headers_to_sign = {
            k: v for k, v in request.headers.items()
            if k.lower() in ("host", "content-type") or k.lower().startswith("x-amz")
        }
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=headers_to_sign,
        )
        SigV4Auth(credentials, _SERVICE, self._region).add_auth(aws_request)
        for name in ("Authorization", "X-Amz-Date", "X-Amz-Security-Token", "X-Amz-Content-SHA256"):
            if name in aws_request.headers:
                request.headers[name] = aws_request.headers[name]
        yield request


def _is_local(endpoint: str) -> bool:
    host = urlparse(endpoint).hostname or ""
    return host in ("localhost", "127.0.0.1")


def build_client_config(endpoint: str, user_id: str) -> ClientConfig | None:
    """ClientConfig de A2A con httpx firmado para el endpoint dado."""
    if _is_local(endpoint):
        return None
    region = os.environ.get("AWS_REGION", "us-east-1")
    http_client = httpx.AsyncClient(
        auth=SigV4HttpxAuth(region),
        headers={USER_ID_HEADER: user_id},
        timeout=_TIMEOUT,
    )
    return ClientConfig(httpx_client=http_client)


def build_agent_card(endpoint: str, name: str = "agent") -> AgentCard:
    """AgentCard sin red para especialistas en AgentCore.

    AgentCore solo expone una ruta por runtime (POST .../invocations, firmada
    con SigV4 y autorizada vía bedrock-agentcore:InvokeAgentRuntime); no existe
    el endpoint bien-conocido .well-known/agent-card.json que el resolver por
    defecto de a2a-sdk intenta pedir con GET — esa ruta no es una acción IAM
    válida y responde 403. bedrock_agentcore.runtime.a2a._build_agent_card ya
    fija esta misma forma de card en el lado del especialista (card.url =
    la propia URL de invocación), así que la reconstruimos aquí y se la
    inyectamos al cliente para saltar el descubrimiento por HTTP.
    """
    return AgentCard(
        name=name,
        description="",
        url=endpoint,
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        skills=[AgentSkill(id="main", name=name, description="", tags=["main"])],
        default_input_modes=["text"],
        default_output_modes=["text"],
    )
