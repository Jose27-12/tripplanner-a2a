import json
from strands import Agent, tool
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from model.load import load_model


@tool
def search_flights(origin: str, destination: str, date: str) -> str:
    """Busca vuelos entre dos ciudades para una fecha dada.

    Args:
        origin: Ciudad o código IATA de origen (ej. 'Bogotá' o 'BOG').
        destination: Ciudad o código IATA de destino (ej. 'Cartagena' o 'CTG').
        date: Fecha del vuelo en formato YYYY-MM-DD.

    Returns:
        Bloque <ui type="flights"> con la lista de vuelos disponibles.
    """
    # Datos simulados — en producción se conectaría a una API de vuelos real
    flights = [
        {
            "aerolinea": "Avianca",
            "vuelo": "AV9821",
            "origen": origin,
            "destino": destination,
            "fecha": date,
            "salida": "07:15",
            "llegada": "08:30",
            "duracion_min": 75,
            "precio_usd": 89,
            "clase": "ECONOMICA",
        },
        {
            "aerolinea": "LATAM",
            "vuelo": "LA4410",
            "origen": origin,
            "destino": destination,
            "fecha": date,
            "salida": "12:40",
            "llegada": "13:55",
            "duracion_min": 75,
            "precio_usd": 76,
            "clase": "ECONOMICA",
        },
        {
            "aerolinea": "Avianca",
            "vuelo": "AV9835",
            "origen": origin,
            "destino": destination,
            "fecha": date,
            "salida": "18:05",
            "llegada": "19:20",
            "duracion_min": 75,
            "precio_usd": 102,
            "clase": "ECONOMICA",
        },
    ]
    return f'<ui type="flights">{json.dumps(flights, ensure_ascii=False)}</ui>'


tools = [search_flights]

SYSTEM_PROMPT = """
Eres un agente especializado en búsqueda de vuelos.

Cuando el usuario solicite vuelos, usa la herramienta search_flights y
presenta los resultados. Tu respuesta SIEMPRE debe incluir el bloque
<ui type="flights">[...]</ui> que devuelve la herramienta, sin modificarlo.

Antes del bloque, escribe una breve descripción de las opciones encontradas
(aerolineas, rango de precios, horarios disponibles). Resalta la opción
más económica.

Nunca inventes vuelos que no vengan de search_flights.
"""

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
