import json
import os
from collections import OrderedDict
from typing import Any

from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.agent.a2a_agent import A2AAgent
from strands.agent.conversation_manager.null_conversation_manager import (
    NullConversationManager,
)

from a2a_auth import build_client_config
from lambda_tools.client import invoke_lambda
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model
import ui_blocks
from user_context import (
    UnauthenticatedError,
    current_user_id,
    reset_current_user_id,
    resolve_user_id,
    set_current_user_id,
)

app = BedrockAgentCoreApp()
log = app.logger

# ── Configuración de entorno ──────────────────────────────────────────────────
FLIGHTS_URL = os.environ.get("FLIGHTS_AGENT_URL", "")
WEATHER_URL = os.environ.get("WEATHER_AGENT_URL", "")
MEMORY_ID   = os.environ.get("TRIP_MEMORY_ID") or None
AWS_REGION  = os.environ.get("AWS_REGION", "us-east-1")

# ── MCP client (Exa AI web search) ───────────────────────────────────────────
mcp_clients = [get_streamable_http_mcp_client()]

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
Eres TripPlanner AI, un asistente experto en planificación de viajes.

## Capacidades
- Busca vuelos con ask_flights (delega en FlightsAgent A2A).
- Consulta el clima con ask_weather (delega en WeatherAgent A2A).
- Gestiona viajes, itinerarios y reservas con las tools de base de datos.
- Busca información adicional con las tools de MCP (Exa AI).

## Reglas de comportamiento

### Antes de crear o modificar datos
Pide siempre confirmación explícita al usuario antes de llamar a
create_trip, create_itinerary, create_reservation, update_trip,
update_itinerary o update_reservation.

### Reservas
- Todas las reservas se crean como SIMULADA. Nunca como CONFIRMADA.
- Nunca solicites ni almacenes datos de tarjeta, CVV, PIN o medios de pago.
- Informa al usuario que la reserva es simulada y no genera cargo real.

### Preferencias del usuario
- Al empezar a planificar un viaje, consulta get_preferences y tenlas en
  cuenta (aerolíneas, tipo de presupuesto, actividades, restricciones).
- Si el contexto del usuario (etiqueta <user_context>) o get_preferences
  contienen preferencias de aerolínea, horario o asiento, menciónalas y
  prioriza esas opciones.
- Si el usuario expresa una preferencia nueva, ofrece guardarla con
  update_preferences (previa confirmación).
- No inventes preferencias que no estén en esas fuentes.
- La memoria conversacional ayuda a conversar; la fuente de verdad de viajes,
  itinerarios, reservas y preferencias es la base de datos (tools).

### Salida estructurada (Agent-Driven UI)
Los resultados de vuelos, clima, viajes, itinerarios y reservas los muestra
el sistema automáticamente como tarjetas cuando usas las tools. NO escribas
bloques <ui>, JSON ni tablas con esos datos: limítate a una explicación breve
(resumen, opción recomendada, siguiente paso) en texto.
"""

# ── Tools de delegación A2A ───────────────────────────────────────────────────

async def _ask_remote(endpoint: str, request: str) -> str:
    """Delega una petición en un agente A2A remoto (firmado con SigV4 en AWS)."""
    if not endpoint:
        return "El agente especialista no está configurado (falta su URL)."
    endpoint = endpoint if endpoint.endswith("/") else endpoint + "/"
    config = build_client_config(endpoint, current_user_id())
    try:
        remote = A2AAgent(endpoint=endpoint, client_config=config)
        result = await remote.invoke_async(request)
        return ui_blocks.forward_blocks_from(str(result.message))
    except Exception:
        log.exception("Falló la llamada A2A a %s", endpoint)
        return "El agente especialista no está disponible en este momento."
    finally:
        if config is not None and config.httpx_client is not None:
            await config.httpx_client.aclose()


@tool
async def ask_flights(request: str) -> str:
    """Busca vuelos delegando en el FlightsAgent (A2A remoto).
    Incluye en la petición origen, destino, fecha(s) y número de pasajeros.
    Los vuelos se muestran al usuario como tarjetas automáticamente.
    """
    return await _ask_remote(FLIGHTS_URL, request)


@tool
async def ask_weather(request: str) -> str:
    """Consulta el pronóstico del clima delegando en el WeatherAgent (A2A remoto).
    Incluye en la petición la ciudad y el rango de fechas.
    El pronóstico se muestra al usuario como tarjetas automáticamente.
    """
    return await _ask_remote(WEATHER_URL, request)


# ── Tools de base de datos (invocan Lambdas) ──────────────────────────────────
# IMPORTANTE: user_id se inyecta aquí desde el contexto de sesión.
# El LLM nunca lo ve ni lo manipula como parámetro.

@tool
def create_trip(
    origen: str,
    destino: str,
    fecha_inicio: str,
    fecha_fin: str,
    viajeros: int,
    presupuesto: float = None,
    moneda: str = "COP",
) -> str:
    """Crea un nuevo viaje en la base de datos.
    Llama a esta tool SOLO después de que el usuario haya confirmado los datos.

    Args:
        origen: Ciudad de origen (ej. 'Bogotá').
        destino: Ciudad de destino (ej. 'Cartagena').
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD.
        fecha_fin: Fecha de fin en formato YYYY-MM-DD.
        viajeros: Número de viajeros (mínimo 1).
        presupuesto: Presupuesto total (número positivo).
        moneda: Moneda del presupuesto ('COP' o 'USD').
    """
    body = {
        "origen": origen,
        "destino": destino,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "viajeros": viajeros,
        "moneda": moneda,
    }
    if presupuesto is not None:
        body["presupuesto"] = presupuesto

    result = invoke_lambda("CreateTrip", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
        "body": json.dumps(body),
    })

    if "error" in result:
        return f"Error al crear el viaje: {result['error']}"

    return f"Viaje creado exitosamente.\n{ui_blocks.emit('trip', result)}"


@tool
def get_trips() -> str:
    """Lista todos los viajes guardados del usuario."""
    result = invoke_lambda("GetTrips", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
    })
    if "error" in result:
        return f"Error al obtener viajes: {result['error']}"

    trips = result.get("trips", [])
    if not trips:
        return "No tienes viajes guardados aún."
    return f"Tienes {len(trips)} viaje(s).\n{ui_blocks.emit('trips', trips)}"


@tool
def update_trip(
    trip_id: str,
    origen: str = None,
    destino: str = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    viajeros: int = None,
    presupuesto: float = None,
    estado: str = None,
) -> str:
    """Actualiza un viaje existente.
    Llama a esta tool SOLO después de que el usuario haya confirmado los cambios.

    Args:
        trip_id: ID del viaje a actualizar.
        origen: Nueva ciudad de origen (opcional).
        destino: Nueva ciudad de destino (opcional).
        fecha_inicio: Nueva fecha de inicio YYYY-MM-DD (opcional).
        fecha_fin: Nueva fecha de fin YYYY-MM-DD (opcional).
        viajeros: Nuevo número de viajeros (opcional).
        presupuesto: Nuevo presupuesto (opcional).
        estado: Nuevo estado: PLANIFICANDO, CONFIRMADO o CANCELADO (opcional).
    """
    body = {}
    if origen is not None:      body["origen"] = origen
    if destino is not None:     body["destino"] = destino
    if fecha_inicio is not None: body["fecha_inicio"] = fecha_inicio
    if fecha_fin is not None:   body["fecha_fin"] = fecha_fin
    if viajeros is not None:    body["viajeros"] = viajeros
    if presupuesto is not None: body["presupuesto"] = presupuesto
    if estado is not None:      body["estado"] = estado

    result = invoke_lambda("UpdateTrip", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
        "pathParameters": {"id": trip_id},
        "body": json.dumps(body),
    })
    if "error" in result:
        return f"Error al actualizar el viaje: {result['error']}"
    return f"Viaje actualizado.\n{ui_blocks.emit('trip', result)}"


@tool
def create_itinerary(trip_id: str, dias: list) -> str:
    """Crea o reemplaza el itinerario de un viaje.
    Llama a esta tool SOLO después de que el usuario haya confirmado el itinerario.

    Args:
        trip_id: ID del viaje al que pertenece el itinerario.
        dias: Lista de días. Cada día es un objeto con:
              - dia (int): número de día (1, 2, 3...)
              - fecha (str): fecha en YYYY-MM-DD
              - actividades (list[str]): lista de actividades del día
    """
    result = invoke_lambda("CreateItinerary", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
        "pathParameters": {"id": trip_id},
        "body": json.dumps({"dias": dias}),
    })
    if "error" in result:
        return f"Error al crear el itinerario: {result['error']}"
    return f"Itinerario creado.\n{ui_blocks.emit('itinerary', result)}"


@tool
def update_itinerary(trip_id: str, dias: list) -> str:
    """Actualiza el itinerario de un viaje existente.
    Llama a esta tool SOLO después de que el usuario haya confirmado los cambios.

    Args:
        trip_id: ID del viaje.
        dias: Lista de días actualizada (misma estructura que create_itinerary).
    """
    result = invoke_lambda("UpdateItinerary", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
        "pathParameters": {"id": trip_id},
        "body": json.dumps({"dias": dias}),
    })
    if "error" in result:
        return f"Error al actualizar el itinerario: {result['error']}"
    return f"Itinerario actualizado.\n{ui_blocks.emit('itinerary', result)}"


@tool
def create_reservation(trip_id: str, tipo: str, detalle: dict) -> str:
    """Crea una reserva simulada asociada a un viaje.
    Llama a esta tool SOLO después de que el usuario haya confirmado.
    La reserva queda como SIMULADA — no genera cargo real alguno.

    Args:
        trip_id: ID del viaje al que pertenece la reserva.
        tipo: Tipo de reserva: 'VUELO', 'HOTEL' o 'ACTIVIDAD'.
        detalle: Diccionario con los detalles (aerolinea, vuelo, precio, etc.).
                 NUNCA incluyas datos de tarjeta, CVV o PIN.
    """
    result = invoke_lambda("CreateReservation", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
        "body": json.dumps({"tripId": trip_id, "tipo": tipo, "detalle": detalle}),
    })
    if "error" in result:
        return f"Error al crear la reserva: {result['error']}"
    return (
        f"Reserva creada (estado: SIMULADA — no genera cargo real).\n"
        f"{ui_blocks.emit('reservation', result)}"
    )


@tool
def get_reservations(trip_id: str = None) -> str:
    """Lista las reservas del usuario. Opcionalmente filtra por viaje.

    Args:
        trip_id: ID del viaje para filtrar (opcional). Si no se pasa, lista todas.
    """
    qs = {}
    if trip_id:
        qs["tripId"] = trip_id

    result = invoke_lambda("GetReservations", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
        "queryStringParameters": qs if qs else None,
    })
    if "error" in result:
        return f"Error al obtener reservas: {result['error']}"

    reservations = result.get("reservations", [])
    if not reservations:
        return "No hay reservas guardadas."
    return f"{len(reservations)} reserva(s).\n{ui_blocks.emit('reservations', reservations)}"


@tool
def update_reservation(res_id: str, estado: str = None, detalle: dict = None) -> str:
    """Actualiza una reserva (estado o detalle).
    Llama a esta tool SOLO después de que el usuario haya confirmado.
    Secuencia válida de estado: SIMULADA -> PENDIENTE -> CONFIRMADA.

    Args:
        res_id: ID de la reserva a actualizar.
        estado: Nuevo estado (opcional): 'SIMULADA', 'PENDIENTE' o 'CONFIRMADA'.
        detalle: Nuevos detalles (opcional). Sin campos de pago.
    """
    body = {}
    if estado is not None:  body["estado"] = estado
    if detalle is not None: body["detalle"] = detalle

    result = invoke_lambda("UpdateReservation", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
        "pathParameters": {"id": res_id},
        "body": json.dumps(body),
    })
    if "error" in result:
        return f"Error al actualizar la reserva: {result['error']}"
    return f"Reserva actualizada.\n{ui_blocks.emit('reservation', result)}"


@tool
def get_itinerary(trip_id: str) -> str:
    """Obtiene el itinerario guardado de un viaje.

    Args:
        trip_id: ID del viaje.
    """
    result = invoke_lambda("GetItinerary", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
        "pathParameters": {"id": trip_id},
    })
    if "error" in result:
        return f"No se encontró el itinerario: {result['error']}"
    return f"Itinerario del viaje.\n{ui_blocks.emit('itinerary', result)}"


@tool
def get_preferences() -> str:
    """Obtiene las preferencias de viaje guardadas del usuario
    (actividades, tipo de presupuesto, restricciones, aerolíneas, asiento)."""
    result = invoke_lambda("GetPreferences", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
    })
    if "error" in result:
        return f"Error al obtener preferencias: {result['error']}"
    if not result:
        return "El usuario aún no tiene preferencias guardadas."
    return f"Preferencias guardadas del usuario: {json.dumps(result, ensure_ascii=False)}"


@tool
def update_preferences(
    actividades: list = None,
    presupuesto_tipo: str = None,
    restricciones: list = None,
    aerolineas_preferidas: list = None,
    asiento_preferido: str = None,
) -> str:
    """Guarda las preferencias de viaje del usuario (reemplaza las anteriores).
    Llama a esta tool SOLO después de que el usuario haya confirmado.
    Primero usa get_preferences para conservar los valores que no cambian.

    Args:
        actividades: Tipos de actividad preferidos (ej. ['playa', 'gastronomia']).
        presupuesto_tipo: 'ECONOMICO', 'MODERADO' o 'PREMIUM'.
        restricciones: Restricciones (ej. ['vegetariano', 'movilidad reducida']).
        aerolineas_preferidas: Aerolíneas preferidas (ej. ['Avianca']).
        asiento_preferido: 'ventana', 'pasillo' o 'indiferente'.
    """
    body = {k: v for k, v in {
        "actividades": actividades,
        "presupuesto_tipo": presupuesto_tipo,
        "restricciones": restricciones,
        "aerolineas_preferidas": aerolineas_preferidas,
        "asiento_preferido": asiento_preferido,
    }.items() if v is not None}
    result = invoke_lambda("UpdatePreferences", {
        "requestContext": {"authorizer": {"claims": {"sub": current_user_id()}}},
        "body": json.dumps(body),
    })
    if "error" in result:
        return f"Error al guardar preferencias: {result['error']}"
    return f"Preferencias guardadas: {json.dumps(result, ensure_ascii=False)}"


# ── Registro de tools ──────────────────────────────────────────────────────────
tools = [
    ask_flights,
    ask_weather,
    create_trip,
    get_trips,
    update_trip,
    create_itinerary,
    update_itinerary,
    create_reservation,
    get_reservations,
    update_reservation,
    get_itinerary,
    get_preferences,
    update_preferences,
]

for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)


# ── Memoria AgentCore ─────────────────────────────────────────────────────────

def _build_session_manager(session_id: str, actor_id: str):
    if not MEMORY_ID:
        return None
    config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        retrieval_config={
            "/preferences/{actorId}/": RetrievalConfig(top_k=5, relevance_score=0.2),
            "/facts/{actorId}/": RetrievalConfig(top_k=5, relevance_score=0.2),
        },
    )
    return AgentCoreMemorySessionManager(config, region_name=AWS_REGION)


def _make_conversation_manager():
    return NullConversationManager()


# ── Cache de agentes por sesión (LRU, máx 128) ───────────────────────────────

def _agent_factory():
    cache = OrderedDict()

    def get_or_create(session_id: str, actor_id: str) -> Agent:
        key = (actor_id, session_id)
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        if len(cache) >= 128:
            cache.popitem(last=False)

        session_manager = _build_session_manager(session_id, actor_id)
        kwargs = {
            "model": load_model(),
            "system_prompt": SYSTEM_PROMPT,
            "tools": tools,
            "callback_handler": None,
            "hooks": [],
        }
        if session_manager is not None:
            kwargs["session_manager"] = session_manager
        else:
            kwargs["conversation_manager"] = _make_conversation_manager()

        cache[key] = Agent(**kwargs)
        return cache[key]

    return get_or_create


get_or_create_agent = _agent_factory()


# ── Helpers de payload ────────────────────────────────────────────────────────

def strip_trailing_tool_use(messages: Any) -> list[dict]:
    """Elimina bloques toolUse del final del historial."""
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")
    messages = list(messages)
    while messages:
        last = messages[-1]
        if not isinstance(last, dict):
            raise ValueError("each message must be an object")
        original = last.get("content", [])
        if not isinstance(original, list) or not all(isinstance(b, dict) for b in original):
            raise ValueError("each message content value must be a list of content blocks")
        content = [b for b in original if "toolUse" not in b]
        if len(content) == len(original):
            break
        if content:
            messages[-1] = {**last, "content": content}
            break
        messages.pop()
    return messages


def _extract_prompt(payload: dict):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if "messages" in payload:
        return strip_trailing_tool_use(payload["messages"])
    if "tool_results" in payload:
        trs = payload["tool_results"]
        if not isinstance(trs, list) or not all(
            isinstance(tr, dict) and isinstance(tr.get("toolUseId"), str) for tr in trs
        ):
            raise ValueError("tool_results must contain objects with a toolUseId string")
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in trs]}]
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    return prompt


# ── Entrypoint ────────────────────────────────────────────────────────────────

@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking OrchestratorAgent")

    # user_id = claim `sub` del JWT de Cognito ya validado por AgentCore.
    # Nunca se toma del payload: el navegador no puede elegir identidad.
    try:
        user_id = resolve_user_id(context)
    except UnauthenticatedError as exc:
        yield {"error": str(exc)}
        return

    session_id = getattr(context, "session_id", None) or "default-session"
    token = set_current_user_id(user_id)
    ui_token = ui_blocks.start_collecting()
    try:
        # La memoria de AgentCore (actor_id) y la caché de agentes también se
        # aíslan por usuario.
        agent = get_or_create_agent(session_id, user_id)
        prompt = _extract_prompt(payload)

        async for event in agent.stream_async(prompt):
            if not isinstance(event, dict) or "event" not in event:
                continue
            cbs = event["event"].get("contentBlockStart")
            if cbs is not None and not cbs.get("start"):
                continue
            yield event
            # Bloques <ui> producidos por las tools: se envían al navegador tal
            # cual, sin pasar por el modelo (ver ui_blocks.py).
            for block in ui_blocks.drain():
                yield _text_event(block)
        for block in ui_blocks.drain():
            yield _text_event(block)
    finally:
        ui_blocks.stop_collecting(ui_token)
        reset_current_user_id(token)


def _text_event(text: str) -> dict:
    """Evento de texto con el mismo formato que los deltas del modelo."""
    return {"event": {"contentBlockDelta": {"delta": {"text": text}}}}


if __name__ == "__main__":
    app.run()
