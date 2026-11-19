"""Carga del modelo Gemini.

La API key de Gemini NUNCA va en texto plano en agentcore.json:

- En AWS se guarda en AgentCore Identity como ApiKeyCredentialProvider
  ("GeminiApiKey", declarado en agentcore/agentcore.json -> credentials) y se
  obtiene en tiempo de petición con el Workload Access Token que AgentCore
  inyecta en cada invocación.
- En desarrollo local (`agentcore dev` / `uv run main.py`) basta con
  GEMINI_API_KEY en el entorno (.env.local).

Como el token solo existe durante una invocación, la clave se resuelve de
forma perezosa justo antes de crear el cliente de Gemini (Strands crea un
cliente nuevo en cada llamada al modelo) y se cachea en el proceso.
"""
import logging
import os
import threading

from strands.models.gemini import GeminiModel

logger = logging.getLogger(__name__)

# Modelo configurable por variable de entorno.
DEFAULT_GEMINI_MODEL = "gemini-3.7-flash"
# El CDK de AgentCore expone el nombre del proveedor como CREDENTIAL_<NOMBRE>_NAME.
GEMINI_CREDENTIAL_PROVIDER = os.environ.get("CREDENTIAL_GEMINIAPIKEY_NAME", "GeminiApiKey")

_cached_key: str | None = None
_lock = threading.Lock()


def get_gemini_api_key() -> str:
    """Devuelve la API key de Gemini (entorno local o AgentCore Identity)."""
    global _cached_key

    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key
    if _cached_key:
        return _cached_key

    with _lock:
        if _cached_key:
            return _cached_key

        from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
        from bedrock_agentcore.services.identity import IdentityClient

        token = BedrockAgentCoreContext.get_workload_access_token()
        if not token:
            raise RuntimeError(
                "No hay GEMINI_API_KEY en el entorno ni Workload Access Token de "
                "AgentCore para leer la credencial "
                f"'{GEMINI_CREDENTIAL_PROVIDER}' desde AgentCore Identity."
            )

        region = os.environ.get("AWS_REGION", "us-east-1")
        client = IdentityClient(region)
        response = client.dp_client.get_resource_api_key(
            resourceCredentialProviderName=GEMINI_CREDENTIAL_PROVIDER,
            workloadIdentityToken=token,
        )
        _cached_key = response["apiKey"]
        logger.info("API key de Gemini obtenida desde AgentCore Identity")
        return _cached_key


class _GeminiModelWithIdentityKey(GeminiModel):
    """GeminiModel que resuelve la API key justo antes de crear el cliente."""

    def _get_client(self):
        self.client_args["api_key"] = get_gemini_api_key()
        return super()._get_client()


def load_model() -> GeminiModel:
    """Cliente de Gemini; la API key se resuelve en la primera llamada al modelo."""
    return _GeminiModelWithIdentityKey(
        client_args={},
        model_id=os.environ.get("GEMINI_MODEL_ID", DEFAULT_GEMINI_MODEL),
    )
