"""WeatherMCP — servidor MCP de clima (AgentCore Runtime, protocolo MCP).

Fuente de datos real: Open-Meteo (https://open-meteo.com), gratuita y sin API key.

- Fechas dentro de la ventana de pronóstico (hoy … +15 días): pronóstico real
  (temperatura máx/mín, condición, probabilidad de lluvia, humedad).
- Fechas más lejanas: estimación climatológica con los datos históricos de los
  mismos días en los 3 años anteriores (temperaturas promedio y probabilidad de
  lluvia = % de años con lluvia ≥ 1 mm). Se marca con "tipo": "estimado_historico".

Contrato AgentCore MCP: streamable-http, sin estado, 0.0.0.0:8000/mcp.
"""
import json
import logging
import unicodedata
from datetime import date, timedelta
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("weather-mcp")

mcp = FastMCP("TripPlannerWeatherMCP", host="0.0.0.0", stateless_http=True)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_DAYS = 16
MAX_RANGE_DAYS = 31
HISTORY_YEARS = 3
HTTP_TIMEOUT = 15.0

# Códigos WMO → (condición en español, icono para el frontend)
_WMO = {
    0: ("Despejado", "sunny"),
    1: ("Mayormente despejado", "sunny"),
    2: ("Parcialmente nublado", "partly_cloudy"),
    3: ("Nublado", "cloudy"),
    45: ("Niebla", "fog"),
    48: ("Niebla con escarcha", "fog"),
    51: ("Llovizna ligera", "rainy"),
    53: ("Llovizna", "rainy"),
    55: ("Llovizna intensa", "rainy"),
    61: ("Lluvia ligera", "rainy"),
    63: ("Lluvia", "rainy"),
    65: ("Lluvia fuerte", "rainy"),
    66: ("Lluvia helada", "rainy"),
    67: ("Lluvia helada fuerte", "rainy"),
    71: ("Nieve ligera", "snow"),
    73: ("Nieve", "snow"),
    75: ("Nieve intensa", "snow"),
    77: ("Granizo fino", "snow"),
    80: ("Chubascos ligeros", "rainy"),
    81: ("Chubascos", "rainy"),
    82: ("Chubascos fuertes", "storm"),
    85: ("Chubascos de nieve", "snow"),
    86: ("Chubascos de nieve fuertes", "snow"),
    95: ("Tormenta eléctrica", "storm"),
    96: ("Tormenta con granizo", "storm"),
    99: ("Tormenta fuerte con granizo", "storm"),
}


def _condition(code: Any) -> tuple[str, str]:
    try:
        return _WMO.get(int(code), ("Variable", "partly_cloudy"))
    except (TypeError, ValueError):
        return ("Sin dato", "partly_cloudy")


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def _round(value: Any, digits: int = 0):
    if value is None:
        return None
    value = round(float(value), digits)
    return int(value) if digits == 0 else value


async def _get_json(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    response = await client.get(url, params=params, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return response.json()


async def _geocode(client: httpx.AsyncClient, city: str, country_code: str) -> dict | None:
    """Busca la ciudad; prioriza el país indicado (Cartagena existe en CO y en ES)."""
    for name in (city, _strip_accents(city)):
        data = await _get_json(
            client, GEOCODING_URL, {"name": name, "count": 10, "language": "es", "format": "json"}
        )
        results = data.get("results") or []
        if results:
            preferred = [r for r in results if r.get("country_code") == country_code.upper()]
            return (preferred or results)[0]
    return None


def _daily_rows(daily: dict) -> list[dict]:
    keys = [k for k in daily if k != "time"]
    return [
        {"fecha": day, **{k: daily[k][i] for k in keys}}
        for i, day in enumerate(daily.get("time", []))
    ]


async def _forecast(client, lat, lon, start: date, end: date) -> list[dict]:
    data = await _get_json(client, FORECAST_URL, {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join([
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_probability_max", "relative_humidity_2m_mean",
        ]),
        "timezone": "auto",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    })
    days = []
    for row in _daily_rows(data.get("daily", {})):
        condicion, icono = _condition(row.get("weather_code"))
        days.append({
            "fecha": row["fecha"],
            "temp_max_c": _round(row.get("temperature_2m_max")),
            "temp_min_c": _round(row.get("temperature_2m_min")),
            "condicion": condicion,
            "lluvia_prob_pct": _round(row.get("precipitation_probability_max")),
            "humedad_pct": _round(row.get("relative_humidity_2m_mean")),
            "icono": icono,
            "tipo": "pronostico",
        })
    return days


def _same_day_in_year(day: date, year: int) -> date:
    try:
        return day.replace(year=year)
    except ValueError:  # 29 de febrero
        return day.replace(year=year, day=28)


async def _climatology(client, lat, lon, start: date, end: date) -> list[dict]:
    """Promedio de los mismos días en los últimos HISTORY_YEARS años."""
    per_day: dict[str, list[dict]] = {}
    for back in range(1, HISTORY_YEARS + 1):
        year_start = _same_day_in_year(start, start.year - back)
        year_end = year_start + (end - start)
        data = await _get_json(client, ARCHIVE_URL, {
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join([
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "precipitation_sum", "relative_humidity_2m_mean",
            ]),
            "timezone": "auto",
            "start_date": year_start.isoformat(),
            "end_date": year_end.isoformat(),
        })
        for offset, row in enumerate(_daily_rows(data.get("daily", {}))):
            target = (start + timedelta(days=offset)).isoformat()
            per_day.setdefault(target, []).append(row)

    days = []
    for target in sorted(per_day):
        rows = per_day[target]

        def avg(key):
            values = [r[key] for r in rows if r.get(key) is not None]
            return sum(values) / len(values) if values else None

        rainy = [r for r in rows if (r.get("precipitation_sum") or 0) >= 1.0]
        codes = [r.get("weather_code") for r in rows if r.get("weather_code") is not None]
        # Condición representativa: la más frecuente en esos años
        code = max(set(codes), key=codes.count) if codes else None
        condicion, icono = _condition(code)
        if not rainy and icono in ("rainy", "storm"):
            # Ningún año tuvo lluvia apreciable ese día: no mostrar condición lluviosa
            condicion, icono = "Parcialmente nublado", "partly_cloudy"
        days.append({
            "fecha": target,
            "temp_max_c": _round(avg("temperature_2m_max")),
            "temp_min_c": _round(avg("temperature_2m_min")),
            "condicion": condicion,
            "lluvia_prob_pct": round(100 * len(rainy) / len(rows)) if rows else None,
            "humedad_pct": _round(avg("relative_humidity_2m_mean")),
            "icono": icono,
            "tipo": "estimado_historico",
        })
    return days


@mcp.tool()
async def get_forecast(city: str, start_date: str, end_date: str = "", country_code: str = "CO") -> str:
    """Pronóstico del clima por día para una ciudad y un rango de fechas.

    Devuelve un JSON con una entrada por día: fecha, ciudad, temp_max_c,
    temp_min_c, condicion, lluvia_prob_pct, humedad_pct, icono y tipo
    ("pronostico" o "estimado_historico" si la fecha supera los 16 días).

    Args:
        city: Ciudad (ej. "Cartagena").
        start_date: Fecha inicial YYYY-MM-DD.
        end_date: Fecha final YYYY-MM-DD (opcional; por defecto = start_date).
        country_code: Código ISO del país para desambiguar (por defecto "CO").
    """
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date) if end_date else start
    except ValueError:
        return json.dumps({"error": "Las fechas deben tener formato YYYY-MM-DD"})
    if end < start:
        return json.dumps({"error": "end_date debe ser mayor o igual a start_date"})
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        return json.dumps({"error": f"El rango máximo es de {MAX_RANGE_DAYS} días"})

    today = date.today()
    if end < today:
        return json.dumps({"error": "Las fechas ya pasaron; indica fechas futuras"})
    start = max(start, today)

    try:
        async with httpx.AsyncClient() as client:
            place = await _geocode(client, city, country_code)
            if not place:
                return json.dumps({"error": f"No se encontró la ciudad '{city}'"}, ensure_ascii=False)
            lat, lon = place["latitude"], place["longitude"]

            horizon = today + timedelta(days=FORECAST_DAYS - 1)
            days: list[dict] = []
            if start <= horizon:
                days += await _forecast(client, lat, lon, start, min(end, horizon))
            if end > horizon:
                days += await _climatology(client, lat, lon, max(start, horizon + timedelta(days=1)), end)
    except httpx.HTTPError as exc:
        logger.error("Error consultando Open-Meteo: %s", exc)
        return json.dumps({"error": "El servicio meteorológico no está disponible en este momento"})

    ciudad = place.get("name", city)
    for day in days:
        day["ciudad"] = ciudad
    return json.dumps(
        {
            "ciudad": ciudad,
            "pais": place.get("country"),
            "latitud": lat,
            "longitud": lon,
            "fuente": "Open-Meteo",
            "dias": days,
        },
        ensure_ascii=False,
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
