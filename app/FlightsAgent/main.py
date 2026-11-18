from strands import Agent, tool
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from model.load import load_model


@tool
def search_flights(origin: str, destination: str, date: str) -> list[dict]:
    """Busca vuelos entre dos ciudades para una fecha (datos simulados)."""
    return [
        {"flight": "AV9821", "depart": "07:15", "price_usd": 89},
        {"flight": "LA4410", "depart": "12:40", "price_usd": 76},
        {"flight": "AV9835", "depart": "18:05", "price_usd": 102},
    ]


tools = [search_flights]


SYSTEM_PROMPT = """
Eres un agente especializado en búsqueda de vuelos. Usa la herramienta
search_flights para responder cualquier pregunta sobre vuelos entre ciudades
en una fecha dada.
"""

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))