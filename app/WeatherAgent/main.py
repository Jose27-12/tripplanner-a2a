import json

from bedrock_agentcore.runtime import serve_a2a
from strands import Agent, tool
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from mcp_connection import McpRuntimeConnection
from model.load import load_model

# Servidor MCP de clima (runtime WeatherMCP en AgentCore, datos de Open-Meteo)
weather_mcp = McpRuntimeConnection("WeatherMCP", "WEATHER_MCP_URL")


@tool
def get_forecast(city: str, start_date: str, end_date: str = "", country_code: str = "CO") -> str:
    """Pronóstico del clima por día para una ciudad y un rango de fechas, consultando el MCP de clima.

    Args:
        city: Nombre de la ciudad (ej. 'Cartagena').
        start_date: Fecha inicial YYYY-MM-DD.
        end_date: Fecha final YYYY-MM-DD (opcional; por defecto igual a start_date).
        country_code: Código ISO del país para desambiguar la ciudad (por defecto 'CO').

    Returns:
        Bloque <ui type="weather"> con un objeto por día, o un mensaje de error.
    """
    data = weather_mcp.call_tool("get_forecast", {
        "city": city,
        "start_date": start_date,
        "end_date": end_date or start_date,
        "country_code": country_code,
    })
    if "error" in data:
        return f"No fue posible consultar el clima: {data['error']}"
    days = data.get("dias") or []
    if not days:
        return "No hay datos del clima para esas fechas."
    historic = any(d.get("tipo") == "estimado_historico" for d in days)
    note = (
        "Nota: algunas fechas superan los 16 días de pronóstico y se estiman con "
        "datos históricos de años anteriores.\n" if historic else ""
    )
    return f'{note}<ui type="weather">{json.dumps(days, ensure_ascii=False)}</ui>'


tools = [get_forecast]

SYSTEM_PROMPT = """
Eres un agente especializado en pronósticos del clima. Tus datos vienen de un
servicio meteorológico real (Open-Meteo) expuesto por MCP (herramienta get_forecast).

- Llama a get_forecast UNA vez con la ciudad y el rango completo de fechas.
- Tu respuesta SIEMPRE debe incluir, sin modificarlo, el bloque
  <ui type="weather">[...]</ui> que devuelve la herramienta.
- Antes del bloque escribe un resumen breve: rango de temperaturas, condición
  predominante, días con mayor probabilidad de lluvia y si conviene llevar
  paraguas o ropa ligera.
- Si la herramienta indica que hay días estimados con datos históricos, dilo.
- Nunca inventes datos que no vengan de get_forecast.
"""

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
