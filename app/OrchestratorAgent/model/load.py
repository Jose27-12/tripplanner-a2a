"""Carga del modelo de lenguaje (Claude por la API de Anthropic, o Gemini).

Proveedor configurable con MODEL_PROVIDER:
  - "anthropic": Claude Sonnet 5.5 vía API de Anthropic (ANTHROPIC_MODEL_ID).
  - "gemini":    Gemini vía Google AI (GEMINI_MODEL_ID).

Las API keys NUNCA van en texto plano en agentcore.json:
- En AWS se guardan en AgentCore Identity como ApiKeyCredentialProvider
  ("AnthropicApiKey" / "GeminiApiKey", sección credentials de
  agentcore/agentcore.json) y se leen en tiempo de petición con el Workload
  Access Token que AgentCore inyecta en cada invocación.
- En desarrollo local basta con ANTHROPIC_API_KEY / GEMINI_API_KEY en el entorno.

Como el token solo existe durante una invocación, la clave se resuelve de
forma perezosa justo antes de la primera llamada al modelo y se cachea.
"""
import logging
import os
import threading

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = "gemini"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5-5"
DEFAULT_GEMINI_MODEL = "gemini-3.7-flash"

# proveedor -> (variable local, nombre del credential provider en AgentCore Identity)
# El CDK de AgentCore expone el nombre como CREDENTIAL_<NOMBRE>_NAME.
_KEYS = {
    "anthropic": ("ANTHROPIC_API_KEY", os.environ.get("CREDENTIAL_ANTHROPICAPIKEY_NAME", "AnthropicApiKey")),
    "gemini": ("GEMINI_API_KEY", os.environ.get("CREDENTIAL_GEMINIAPIKEY_NAME", "GeminiApiKey")),
}

_cache: dict[str, str] = {}
_lock = threading.Lock()


def get_api_key(provider: str) -> str:
    """API key del proveedor: entorno local o AgentCore Identity."""
    env_var, credential_name = _KEYS[provider]
    env_key = os.environ.get(env_var)
    if env_key:
        return env_key
    if provider in _cache:
        return _cache[provider]

    with _lock:
        if provider in _cache:
            return _cache[provider]

        from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
        from bedrock_agentcore.services.identity import IdentityClient

        token = BedrockAgentCoreContext.get_workload_access_token()
        if not token:
            raise RuntimeError(
                f"No hay {env_var} en el entorno ni Workload Access Token de AgentCore "
                f"para leer la credencial '{credential_name}' desde AgentCore Identity."
            )
        client = IdentityClient(os.environ.get("AWS_REGION", "us-east-1"))
        response = client.dp_client.get_resource_api_key(
            resourceCredentialProviderName=credential_name,
            workloadIdentityToken=token,
        )
        _cache[provider] = response["apiKey"]
        logger.info("API key de %s obtenida desde AgentCore Identity", provider)
        return _cache[provider]


def _anthropic_model():
    import anthropic
    from strands.models.anthropic import AnthropicModel

    class _AnthropicModelWithIdentityKey(AnthropicModel):
        """AnthropicModel que crea su cliente con la key en la primera llamada."""

        _ready = False

        def _ensure_client(self):
            if not self._ready:
                self.client = anthropic.AsyncAnthropic(api_key=get_api_key("anthropic"))
                self._ready = True

        async def stream(self, *args, **kwargs):
            self._ensure_client()
            async for event in super().stream(*args, **kwargs):
                yield event

        async def structured_output(self, *args, **kwargs):
            self._ensure_client()
            async for event in super().structured_output(*args, **kwargs):
                yield event

    return _AnthropicModelWithIdentityKey(
        # Clave provisional: el cliente real se crea en la primera llamada.
        client_args={"api_key": "pendiente"},
        model_id=os.environ.get("ANTHROPIC_MODEL_ID", DEFAULT_ANTHROPIC_MODEL),
        max_tokens=16000,
    )


def _gemini_model():
    from strands.models.gemini import GeminiModel

    class _GeminiModelWithIdentityKey(GeminiModel):
        """GeminiModel que resuelve la API key justo antes de crear el cliente."""

        def _get_client(self):
            self.client_args["api_key"] = get_api_key("gemini")
            return super()._get_client()

    return _GeminiModelWithIdentityKey(
        client_args={},
        model_id=os.environ.get("GEMINI_MODEL_ID", DEFAULT_GEMINI_MODEL),
    )


def load_model():
    provider = os.environ.get("MODEL_PROVIDER", DEFAULT_PROVIDER).lower()
    if provider == "anthropic":
        return _anthropic_model()
    if provider == "gemini":
        return _gemini_model()
    raise ValueError(f"MODEL_PROVIDER no soportado: {provider}")
