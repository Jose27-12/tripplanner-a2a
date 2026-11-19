"""FlightsMCP — servidor MCP de vuelos (AgentCore Runtime, protocolo MCP).

Las APIs comerciales de vuelos requieren contrato o claves de pago, y el
trabajo permite reservas simuladas, así que este MCP SIMULA un proveedor de
vuelos de forma dinámica y reproducible (no datos fijos):

- Aeropuertos reales (IATA y coordenadas) de Colombia y destinos frecuentes.
- Aerolíneas reales según el tipo de ruta (nacional / internacional).
- Duración calculada por distancia geodésica; escala en BOG o PTY cuando no
  hay vuelo directo.
- Precio según distancia, aerolínea (low-cost vs. tradicional), hora de
  salida, día de la semana, temporada alta y anticipación de la compra.
- La misma consulta (ruta + fecha) siempre devuelve los mismos vuelos.

Todos los resultados llevan "fuente": "simulado". Contrato AgentCore MCP:
streamable-http, sin estado, 0.0.0.0:8000/mcp.
"""
import hashlib
import json
import math
import random
import unicodedata
from datetime import date, datetime, timedelta

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TripPlannerFlightsMCP", host="0.0.0.0", stateless_http=True)

COP_PER_USD = 4000  # tasa de referencia fija para la simulación

# IATA: (ciudad, país, lat, lon, alias)
AIRPORTS = {
    "BOG": ("Bogotá", "CO", 4.7016, -74.1469, ["bogota", "el dorado"]),
    "MDE": ("Medellín", "CO", 6.1645, -75.4231, ["medellin", "rionegro"]),
    "CTG": ("Cartagena", "CO", 10.4424, -75.5130, ["cartagena", "cartagena de indias"]),
    "CLO": ("Cali", "CO", 3.5432, -76.3816, ["cali"]),
    "BAQ": ("Barranquilla", "CO", 10.8896, -74.7808, ["barranquilla"]),
    "SMR": ("Santa Marta", "CO", 11.1196, -74.2306, ["santa marta"]),
    "ADZ": ("San Andrés", "CO", 12.5836, -81.7112, ["san andres"]),
    "PEI": ("Pereira", "CO", 4.8127, -75.7395, ["pereira"]),
    "BGA": ("Bucaramanga", "CO", 7.1265, -73.1848, ["bucaramanga"]),
    "CUC": ("Cúcuta", "CO", 7.9276, -72.5115, ["cucuta"]),
    "MTR": ("Montería", "CO", 8.8237, -75.8258, ["monteria"]),
    "LET": ("Leticia", "CO", -4.1936, -69.9432, ["leticia"]),
    "PTY": ("Ciudad de Panamá", "PA", 9.0714, -79.3835, ["panama", "ciudad de panama"]),
    "MIA": ("Miami", "US", 25.7959, -80.2870, ["miami"]),
    "JFK": ("Nueva York", "US", 40.6413, -73.7781, ["nueva york", "new york"]),
    "MEX": ("Ciudad de México", "MX", 19.4361, -99.0719, ["ciudad de mexico", "mexico"]),
    "CUN": ("Cancún", "MX", 21.0365, -86.8771, ["cancun"]),
    "LIM": ("Lima", "PE", -12.0219, -77.1143, ["lima"]),
    "UIO": ("Quito", "EC", -0.1292, -78.3575, ["quito"]),
    "SCL": ("Santiago de Chile", "CL", -33.3930, -70.7858, ["santiago", "santiago de chile"]),
    "EZE": ("Buenos Aires", "AR", -34.8222, -58.5358, ["buenos aires"]),
    "GRU": ("São Paulo", "BR", -23.4356, -46.4731, ["sao paulo"]),
    "MAD": ("Madrid", "ES", 40.4983, -3.5676, ["madrid"]),
}

# código: (nombre, factor de precio, equipaje incluido)
AIRLINES = {
    "AV": ("Avianca", 1.00, "Artículo personal + equipaje de mano 10 kg"),
    "LA": ("LATAM", 0.94, "Artículo personal + equipaje de mano 10 kg"),
    "JA": ("JetSMART", 0.72, "Solo artículo personal"),
    "CM": ("Copa Airlines", 1.05, "Equipaje de mano + maleta 23 kg"),
    "AA": ("American Airlines", 1.12, "Equipaje de mano 10 kg"),
    "IB": ("Iberia", 1.08, "Equipaje de mano + maleta 23 kg"),
}
DOMESTIC_AIRLINES = ["AV", "LA", "JA"]
INTERNATIONAL_AIRLINES = {
    "US": ["AV", "LA", "AA", "CM"],
    "ES": ["AV", "IB"],
    "DEFAULT": ["AV", "LA", "CM"],
}
# Destinos internacionales con vuelo directo desde Colombia (desde BOG/MDE)
DIRECT_INTERNATIONAL = {"PTY", "MIA", "MEX", "CUN", "LIM", "UIO", "MAD", "JFK", "SCL", "GRU"}
HUBS = {"AV": "BOG", "LA": "BOG", "JA": "MDE", "CM": "PTY", "AA": "MIA", "IB": "MAD"}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.strip().lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _resolve_airport(value: str) -> str | None:
    if not value:
        return None
    code = value.strip().upper()
    if code in AIRPORTS:
        return code
    norm = _normalize(value)
    for iata, (city, _, _, _, aliases) in AIRPORTS.items():
        if norm == _normalize(city) or norm in aliases:
            return iata
    for iata, (city, _, _, _, aliases) in AIRPORTS.items():
        if any(alias in norm for alias in aliases):
            return iata
    return None


def _distance_km(a: str, b: str) -> float:
    _, _, lat1, lon1, _ = AIRPORTS[a]
    _, _, lat2, lon2, _ = AIRPORTS[b]
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _block_minutes(km: float) -> int:
    return int(round((km / 780) * 60 + 35))


def _season_factor(day: date) -> float:
    md = (day.month, day.day)
    if md >= (12, 15) or md <= (1, 15):
        return 1.35   # vacaciones de fin de año
    if (6, 15) <= md <= (7, 31):
        return 1.25   # vacaciones de mitad de año
    return 1.0


def _advance_factor(day: date) -> float:
    days = (day - date.today()).days
    if days < 7:
        return 1.5
    if days < 21:
        return 1.2
    if days > 60:
        return 0.9
    return 1.0


def _hour_factor(hour: int) -> float:
    if hour < 7 or hour >= 20:
        return 0.88   # madrugada / nocturno
    if 7 <= hour < 10 or 17 <= hour < 20:
        return 1.08   # horas pico
    return 1.0


def _round_price(cop: float) -> int:
    return int(round(cop / 100) * 100)


@mcp.tool()
def search_flights(origin: str, destination: str, date: str, passengers: int = 1) -> str:
    """Busca vuelos de ida entre dos ciudades para una fecha.

    Devuelve un JSON con la lista de vuelos ordenada por precio: aerolinea,
    vuelo, origen/destino (ciudad e IATA), fecha, salida, llegada,
    duracion_min, escalas, precio_usd y precio_cop por persona,
    precio_total_cop para todos los pasajeros, asientos_disponibles, equipaje.
    Para ida y vuelta, llama dos veces (ida y regreso).

    Args:
        origin: Ciudad o código IATA de origen (ej. "Bogotá" o "BOG").
        destination: Ciudad o código IATA de destino (ej. "Cartagena" o "CTG").
        date: Fecha del vuelo YYYY-MM-DD.
        passengers: Número de pasajeros (1-9).
    """
    flight_date = _parse_date(date)
    if isinstance(flight_date, str):
        return json.dumps({"error": flight_date}, ensure_ascii=False)
    if not isinstance(passengers, int) or not 1 <= passengers <= 9:
        return json.dumps({"error": "passengers debe estar entre 1 y 9"})

    o, d = _resolve_airport(origin), _resolve_airport(destination)
    if not o or not d:
        missing = origin if not o else destination
        return json.dumps({
            "error": f"No hay vuelos registrados para '{missing}'",
            "ciudades_disponibles": sorted({v[0] for v in AIRPORTS.values()}),
        }, ensure_ascii=False)
    if o == d:
        return json.dumps({"error": "El origen y el destino deben ser diferentes"})

    flights = _generate(o, d, flight_date, passengers)
    return json.dumps({
        "origen": AIRPORTS[o][0], "origen_iata": o,
        "destino": AIRPORTS[d][0], "destino_iata": d,
        "fecha": flight_date.isoformat(),
        "pasajeros": passengers,
        "tasa_cop_usd": COP_PER_USD,
        "fuente": "simulado",
        "vuelos": flights,
    }, ensure_ascii=False)


@mcp.tool()
def list_destinations() -> str:
    """Lista las ciudades y aeropuertos (IATA) disponibles en el proveedor."""
    return json.dumps(
        [{"iata": k, "ciudad": v[0], "pais": v[1]} for k, v in sorted(AIRPORTS.items())],
        ensure_ascii=False,
    )


def _parse_date(value: str) -> date | str:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return "La fecha debe tener formato YYYY-MM-DD"
    if parsed < date.today():
        return "La fecha del vuelo ya pasó"
    if parsed > date.today() + timedelta(days=330):
        return "Solo hay vuelos publicados para los próximos 330 días"
    return parsed


def _generate(o: str, d: str, day: date, passengers: int) -> list[dict]:
    seed = int(hashlib.sha256(f"{o}-{d}-{day.isoformat()}".encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)

    domestic = AIRPORTS[o][1] == "CO" and AIRPORTS[d][1] == "CO"
    km = _distance_km(o, d)
    if domestic:
        carriers = DOMESTIC_AIRLINES
        base_usd = 38 + 0.11 * km
    else:
        foreign = AIRPORTS[d][1] if AIRPORTS[d][1] != "CO" else AIRPORTS[o][1]
        carriers = INTERNATIONAL_AIRLINES.get(foreign, INTERNATIONAL_AIRLINES["DEFAULT"])
        base_usd = 110 + 0.085 * km

    weekend = 1.1 if day.weekday() in (4, 6) else 1.0   # viernes y domingo
    n_flights = rng.randint(4, 7)
    hours = sorted(rng.sample(range(5, 22), n_flights))

    flights = []
    for hour in hours:
        code = rng.choice(carriers)
        name, airline_factor, baggage = AIRLINES[code]
        minute = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])

        hub = HUBS.get(code)
        direct = (
            domestic and (o in ("BOG", "MDE") or d in ("BOG", "MDE") or rng.random() < 0.55)
        ) or (not domestic and (o in DIRECT_INTERNATIONAL or d in DIRECT_INTERNATIONAL) and rng.random() < 0.8)
        if direct or hub in (o, d, None):
            duration, stops, via = _block_minutes(km), 0, None
        else:
            duration = _block_minutes(_distance_km(o, hub)) + _block_minutes(_distance_km(hub, d))
            duration += rng.randint(60, 150)
            stops, via = 1, hub

        departure = datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)
        arrival = departure + timedelta(minutes=duration)

        price_usd = (
            base_usd * airline_factor * _hour_factor(hour) * weekend
            * _season_factor(day) * _advance_factor(day) * rng.uniform(0.9, 1.12)
        )
        if stops:
            price_usd *= 0.9
        price_cop = _round_price(price_usd * COP_PER_USD)

        flights.append({
            "aerolinea": name,
            "codigo_aerolinea": code,
            "vuelo": f"{code}{rng.randint(100, 9899)}",
            "origen": AIRPORTS[o][0],
            "origen_iata": o,
            "destino": AIRPORTS[d][0],
            "destino_iata": d,
            "fecha": day.isoformat(),
            "salida": departure.strftime("%H:%M"),
            "llegada": arrival.strftime("%H:%M") + (" (+1)" if arrival.date() > day else ""),
            "duracion_min": duration,
            "escalas": stops,
            "escala_en": AIRPORTS[via][0] if via else None,
            "clase": "ECONOMICA",
            "precio_usd": round(price_usd),
            "precio_cop": price_cop,
            "pasajeros": passengers,
            "precio_total_cop": price_cop * passengers,
            "asientos_disponibles": rng.randint(2, 9),
            "equipaje": baggage,
            "fuente": "simulado",
        })

    flights.sort(key=lambda f: f["precio_cop"])
    if flights:
        flights[0]["mas_economico"] = True
    return flights


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
