import os
from typing import Any
from collections import OrderedDict
from strands import Agent, tool
from strands.agent.a2a_agent import A2AAgent
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config  import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

app = BedrockAgentCoreApp()
log = app.logger

# Define a Streamable HTTP MCP Client
mcp_clients = [get_streamable_http_mcp_client()]

DEFAULT_SYSTEM_PROMPT = """
Eres un planificador de viajes. Usa ask_flights para buscar vuelos y
ask_weather para consultar el clima. Consolida ambos resultados en una
respuesta clara para el usuario.

Si en el contexto del usuario (etiqueta <user_context>) aparece una preferencia
de aerolínea, menciónala explícitamente al proponer vuelos y prioriza las
opciones de esa aerolínea. Tampoco ignores otras preferencias que aparezcan
(horario, asiento). No inventes preferencias que no estén en ese contexto.
"""


# Endpoints de los especialistas A2A (se completan después de desplegarlos)
FLIGHTS_URL = os.environ.get("FLIGHTS_AGENT_URL", "")
WEATHER_URL = os.environ.get("WEATHER_AGENT_URL", "")

# Vacío -> el agente sigue funcionando sin memoria gestionada.
MEMORY_ID = os.environ.get("TRIP_MEMORY_ID") or None
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Define a collection of tools used by the model
tools = []

# Delega en el Flights Agent (servidor A2A) la búsqueda de vuelos
@tool
def ask_flights(request: str) -> str:
    """Busca vuelos delegando en el Flights Agent (servidor A2A remoto)."""
    remote = A2AAgent(endpoint=FLIGHTS_URL)
    return str(remote(request).message)
tools.append(ask_flights)

# Delega en el Weather Agent (servidor A2A) la consulta de clima
@tool
def ask_weather(request: str) -> str:
    """Consulta el clima delegando en el Weather Agent (servidor A2A remoto)."""
    remote = A2AAgent(endpoint=WEATHER_URL)
    return str(remote(request).message)
tools.append(ask_weather)


# Add MCP client to tools if available
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)


def _make_conversation_manager():
    return NullConversationManager()


def _build_session_manager(session_id: str, actor_id: str):
    """Gestor de memoria gestionada de AgentCore. None si no hay MEMORY_ID."""
    if not MEMORY_ID:
        return None
    config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,  # una conversación concreta
        actor_id=actor_id,      # la identidad del usuario
        # Namespaces de largo plazo que se inyectan al modelo en cada turno.
        # Usan las mismas variables que los namespaceTemplates del agentcore.json.
        retrieval_config={
            "/preferences/{actorId}/": RetrievalConfig(top_k=5, relevance_score=0.2),
            "/facts/{actorId}/": RetrievalConfig(top_k=5, relevance_score=0.2),
        },
    )
    return AgentCoreMemorySessionManager(config, region_name=AWS_REGION)

# Reuses one Agent per session_id so each session keeps its own in-process
# conversation history (best-effort; resets on cold start). The cache is bounded
# to 128 sessions with LRU eviction (least-recently-used is dropped and its
# history reset) so a single process serving many sessions cannot leak history
# between them or grow without limit. For durable history, attach a session manager.
def agent_factory():
    cache = OrderedDict()
    def get_or_create_agent(session_id, actor_id):
        key = (actor_id, session_id)
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        if len(cache) >= 128:
            cache.popitem(last=False)

        session_manager = _build_session_manager(session_id, actor_id)
        agent_kwargs = {
            "model": load_model(),
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "tools": tools,
            "callback_handler": None,
            "hooks": [],
        }
        if session_manager is not None:
            # El session manager gestiona el historial automáticamente.
            agent_kwargs["session_manager"] = session_manager
        else:
            agent_kwargs["conversation_manager"] = _make_conversation_manager()

        cache[key] = Agent(**agent_kwargs)
        return cache[key]
    return get_or_create_agent
get_or_create_agent = agent_factory()


def strip_trailing_tool_use(messages: Any) -> list[dict]:
    """Strip toolUse blocks from the tail until the last message has none."""
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")

    messages = list(messages)
    while messages:
        last = messages[-1]
        if not isinstance(last, dict):
            raise ValueError("each message must be an object")
        original_content = last.get("content", [])
        if not isinstance(original_content, list) or not all(isinstance(block, dict) for block in original_content):
            raise ValueError("each message content value must be a list of content blocks")

        content = [block for block in original_content if "toolUse" not in block]
        if len(content) == len(original_content):
            break
        if content:
            messages[-1] = {**last, "content": content}
            break
        messages.pop()

    return messages


def _extract_prompt(payload: dict):
    """Accept validated harness messages, tool results, or a plain prompt string."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if "messages" in payload:
        return strip_trailing_tool_use(payload["messages"])
    if "tool_results" in payload:
        tool_results = payload["tool_results"]
        if not isinstance(tool_results, list) or not all(
            isinstance(tool_result, dict) and isinstance(tool_result.get("toolUseId"), str)
            for tool_result in tool_results
        ):
            raise ValueError("tool_results must contain objects with a toolUseId string")
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in tool_results]}]
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    return prompt



@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")


    session_id = getattr(context, "session_id", None) or "default-session"
    actor_id = (
        getattr(context, "actor_id", None)
        or (payload.get("actor_id") if isinstance(payload, dict) else None)
        or "default-user"
    )
    agent = get_or_create_agent(session_id, actor_id)

    prompt = _extract_prompt(payload)


    async for event in agent.stream_async(
        prompt,
    ):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        yield event


if __name__ == "__main__":
    app.run()