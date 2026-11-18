from strands import Agent, tool
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from model.load import load_model


@tool
def get_forecast(city: str, date: str) -> dict:
    """Devuelve el pronóstico del clima de una ciudad (datos simulados)."""
    return {"city": city, "date": date, "temp_c": 31, "condition": "Soleado"}


tools = [get_forecast]


SYSTEM_PROMPT = """
Eres un agente especializado en pronósticos del clima. Usa la herramienta
get_forecast para responder cualquier pregunta sobre el clima en una ciudad
y fecha dadas.
"""

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))