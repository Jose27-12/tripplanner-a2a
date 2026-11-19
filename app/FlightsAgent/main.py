import json

from bedrock_agentcore.runtime import serve_a2a
from strands import Agent, tool
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from mcp_connection import McpRuntimeConnection
from model.load import load_model

# Servidor MCP de vuelos (runtime FlightsMCP en AgentCore)
flights_mcp = McpRuntimeConnection("FlightsMCP", "FLIGHTS_MCP_URL")


@tool
def search_flights(origin: str, destination: str, date: str, passengers: int = 1) -> str:
    """Busca vuelos de ida entre dos ciudades para una fecha, consultando el MCP de vuelos.

    Args:
        origin: Ciudad o código IATA de origen (ej. 'Bogotá' o 'BOG').
        destination: Ciudad o código IATA de destino (ej. 'Cartagena' o 'CTG').
        date: Fecha del vuelo en formato YYYY-MM-DD.
        passengers: Número de pasajeros (1-9).

    Returns:
        Bloque <ui type="flights"> con los vuelos disponibles, o un mensaje de error.
    """
    data = flights_mcp.call_tool("search_flights", {
        "origin": origin,
        "destination": destination,
        "date": date,
        "passengers": int(passengers),
    })
    if "error" in data:
        extra = data.get("ciudades_disponibles")
        hint = f" Ciudades disponibles: {', '.join(extra)}." if extra else ""
        return f"No fue posible buscar vuelos: {data['error']}.{hint}"
    if not data.get("vuelos"):
        return "No hay vuelos disponibles para esa ruta y fecha."
    return f'<ui type="flights">{json.dumps(data["vuelos"], ensure_ascii=False)}</ui>'


tools = [search_flights]

SYSTEM_PROMPT = """
Eres un agente especializado en búsqueda de vuelos. Tus datos vienen de un
proveedor de vuelos expuesto por MCP (herramienta search_flights).

- Usa search_flights para cada tramo. Si piden ida y vuelta, llama una vez
  para la ida y otra para el regreso (origen y destino invertidos).
- Pasa siempre el número de pasajeros si el usuario lo indica.
- Tu respuesta SIEMPRE debe incluir, sin modificarlo, cada bloque
  <ui type="flights">[...]</ui> que devuelve la herramienta.
- Antes de los bloques escribe un resumen breve: aerolíneas, rango de
  precios por persona y total en COP, horarios y la opción más económica.
- Aclara que las tarifas provienen de un proveedor simulado.
- Nunca inventes vuelos que no vengan de search_flights.
"""

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
