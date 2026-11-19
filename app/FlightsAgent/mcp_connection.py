"""Conexión del agente especialista con su servidor MCP (AgentCore Runtime).

- En AWS el servidor MCP es otro runtime de AgentCore con autorización IAM:
  su URL se descubre por nombre (bedrock-agentcore-control:ListAgentRuntimes)
  y cada petición HTTP se firma con SigV4 usando el rol de este agente.
- En local se puede fijar la URL con la variable <PREFIJO>_MCP_URL
  (ej. FLIGHTS_MCP_URL=http://localhost:8000/mcp) y no se firma nada.
"""
import json
import logging
import os
import threading
import uuid
from urllib.parse import quote, urlparse

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

logger = logging.getLogger(__name__)

PROJECT_NAME = "TripPlannerA2A"
_SERVICE = "bedrock-agentcore"


class SigV4HttpxAuth(httpx.Auth):
    """Firma cada petición httpx con SigV4 (credenciales del rol en ejecución)."""

    requires_request_body = True

    def __init__(self, region: str):
        self._region = region
        self._session = boto3.Session()

    def auth_flow(self, request: httpx.Request):
        credentials = self._session.get_credentials().get_frozen_credentials()
        headers_to_sign = {
            k: v for k, v in request.headers.items()
            if k.lower() in ("host", "content-type") or k.lower().startswith("x-amz")
        }
        aws_request = AWSRequest(
            method=request.method, url=str(request.url), data=request.content, headers=headers_to_sign
        )
        SigV4Auth(credentials, _SERVICE, self._region).add_auth(aws_request)
        for name in ("Authorization", "X-Amz-Date", "X-Amz-Security-Token", "X-Amz-Content-SHA256"):
            if name in aws_request.headers:
                request.headers[name] = aws_request.headers[name]
        yield request


class McpRuntimeConnection:
    """Resuelve la URL del runtime MCP una vez y llama a sus tools."""

    def __init__(self, runtime_name: str, url_env_var: str):
        self._runtime_name = f"{PROJECT_NAME}_{runtime_name}"
        self._url_env_var = url_env_var
        self._region = os.environ.get("AWS_REGION", "us-east-1")
        self._url: str | None = None
        self._lock = threading.Lock()

    def _discover_url(self) -> str:
        override = os.environ.get(self._url_env_var)
        if override:
            return override
        control = boto3.client("bedrock-agentcore-control", region_name=self._region)
        token = None
        while True:
            kwargs = {"maxResults": 100, **({"nextToken": token} if token else {})}
            page = control.list_agent_runtimes(**kwargs)
            for runtime in page.get("agentRuntimes", []):
                if runtime.get("agentRuntimeName") == self._runtime_name:
                    arn = runtime["agentRuntimeArn"]
                    return (
                        f"https://bedrock-agentcore.{self._region}.amazonaws.com/runtimes/"
                        f"{quote(arn, safe='')}/invocations?qualifier=DEFAULT"
                    )
            token = page.get("nextToken")
            if not token:
                break
        raise RuntimeError(f"No se encontró el runtime MCP '{self._runtime_name}'")

    @property
    def url(self) -> str:
        if self._url is None:
            with self._lock:
                if self._url is None:
                    self._url = self._discover_url()
                    logger.info("Servidor MCP %s: %s", self._runtime_name, self._url)
        return self._url

    def _transport(self):
        url = self.url
        host = urlparse(url).hostname or ""
        auth = None if host in ("localhost", "127.0.0.1") else SigV4HttpxAuth(self._region)
        return streamablehttp_client(url, auth=auth, timeout=30)

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Llama a una tool del servidor MCP y devuelve su JSON ya parseado."""
        try:
            client = MCPClient(self._transport)
            with client:
                result = client.call_tool_sync(
                    tool_use_id=f"mcp-{uuid.uuid4()}", name=name, arguments=arguments
                )
        except Exception:
            logger.exception("No se pudo contactar el servidor MCP %s", self._runtime_name)
            return {"error": "El servicio no está disponible en este momento"}
        text = "".join(
            block.get("text", "") for block in result.get("content", []) if isinstance(block, dict)
        )
        if result.get("status") == "error":
            logger.error("La tool MCP %s falló: %s", name, text)
            return {"error": "El servicio no está disponible en este momento"}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": text or "Respuesta vacía del servidor MCP"}
