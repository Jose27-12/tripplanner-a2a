import json
from strands import Agent, tool
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from model.load import load_model


@tool
def get_forecast(city: str, date: str) -> str:
    """Devuelve el pronóstico del clima para una ciudad en una fecha dada.

    Args:
        city: Nombre de la ciudad (ej. 'Cartagena').
        date: Fecha en formato YYYY-MM-DD. Para obtener un rango, llama
              la herramienta varias veces con fechas consecutivas.

    Returns:
        Bloque <ui type="weather"> con el pronóstico del día.
    """
    # Datos simulados — en producción se conectaría a una API meteorológica real
    # Simulamos variación por día para hacer el demo más realista
    day_num = int(date[-2:]) if date else 10
    temp_max = 30 + (day_num % 4)
    temp_min = 24 + (day_num % 3)
    rain_prob = (day_num * 7) % 60
    conditions = ["Soleado", "Parcialmente nublado", "Soleado", "Nublado con lluvias"]
    icons      = ["sunny",   "partly_cloudy",        "sunny",   "rainy"]
    idx = day_num % 4

    forecast = [{
        "fecha": date,
        "ciudad": city,
        "temp_max_c": temp_max,
        "temp_min_c": temp_min,
        "condicion": conditions[idx],
        "lluvia_prob_pct": rain_prob,
        "humedad_pct": 70 + (day_num % 15),
        "icono": icons[idx],
    }]
    return f'<ui type="weather">{json.dumps(forecast, ensure_ascii=False)}</ui>'


tools = [get_forecast]

SYSTEM_PROMPT = """
Eres un agente especializado en pronósticos del clima.

Cuando el usuario solicite el clima para una ciudad y un rango de fechas,
llama a get_forecast una vez por cada día del rango y consolida los
resultados en un único bloque <ui type="weather">[...]</ui>.

Tu respuesta SIEMPRE debe incluir ese bloque sin modificarlo. Antes del bloque,
escribe un resumen breve: temperatura promedio esperada, condición predominante
y si se recomienda llevar paraguas.

Nunca inventes datos que no vengan de get_forecast.
"""

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
