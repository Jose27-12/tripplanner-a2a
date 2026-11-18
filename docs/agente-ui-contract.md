# Contrato de Salida de Agentes — Agent-Driven UI

## Formato general

Los agentes responden con texto libre más bloques estructurados delimitados por etiquetas `<ui>`. El frontend detecta esas etiquetas, extrae el JSON y renderiza el componente correspondiente.

```
<texto explicativo del agente>

<ui type="<tipo>"><json_serializado></ui>
```

Reglas:
- El JSON dentro de `<ui>` debe ser válido y parseable.
- Puede haber múltiples bloques `<ui>` en una misma respuesta.
- El texto fuera de las etiquetas se renderiza como markdown en el chat.
- El frontend ignora etiquetas con `type` desconocido (no rompe).

---

## Tipos de bloques

### `flights` — Lista de vuelos

Producido por: **FlightsAgent** (reenviado por Orchestrator sin modificar).

```json
<ui type="flights">
[
  {
    "aerolinea": "Avianca",
    "vuelo": "AV9821",
    "origen": "BOG",
    "destino": "CTG",
    "salida": "07:15",
    "llegada": "08:30",
    "duracion_min": 75,
    "precio_usd": 89,
    "clase": "ECONOMICA"
  },
  {
    "aerolinea": "LATAM",
    "vuelo": "LA4410",
    "origen": "BOG",
    "destino": "CTG",
    "salida": "12:40",
    "llegada": "13:55",
    "duracion_min": 75,
    "precio_usd": 76,
    "clase": "ECONOMICA"
  }
]
</ui>
```

Componente frontend: `FlightCards` — tarjetas comparativas, resalta la más barata.

---

### `weather` — Pronóstico del clima

Producido por: **WeatherAgent** (reenviado por Orchestrator sin modificar).

```json
<ui type="weather">
[
  {
    "fecha": "2026-12-10",
    "ciudad": "Cartagena",
    "temp_max_c": 32,
    "temp_min_c": 26,
    "condicion": "Soleado",
    "lluvia_prob_pct": 10,
    "humedad_pct": 75,
    "icono": "sunny"
  },
  {
    "fecha": "2026-12-11",
    "ciudad": "Cartagena",
    "temp_max_c": 30,
    "temp_min_c": 25,
    "condicion": "Parcialmente nublado",
    "lluvia_prob_pct": 35,
    "humedad_pct": 80,
    "icono": "partly_cloudy"
  }
]
</ui>
```

Componente frontend: `WeatherCards` — una tarjeta por día.

---

### `trip` — Viaje creado o actualizado

Producido por: **OrchestratorAgent** después de usar la tool `create_trip` o `update_trip`.

```json
<ui type="trip">
{
  "tripId": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "origen": "Bogotá",
  "destino": "Cartagena",
  "fecha_inicio": "2026-12-10",
  "fecha_fin": "2026-12-14",
  "viajeros": 3,
  "presupuesto": 5000000,
  "moneda": "COP",
  "estado": "PLANIFICANDO"
}
</ui>
```

Componente frontend: `TripCard` — refresca la lista de viajes.

---

### `itinerary` — Itinerario creado o actualizado

Producido por: **OrchestratorAgent** después de usar `create_itinerary` o `update_itinerary`.

```json
<ui type="itinerary">
{
  "tripId": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "destino": "Cartagena",
  "dias": [
    {
      "dia": 1,
      "fecha": "2026-12-10",
      "actividades": [
        "Llegada al aeropuerto Rafael Núñez",
        "Check-in en el hotel",
        "Recorrido por el centro histórico amurallado"
      ]
    },
    {
      "dia": 2,
      "fecha": "2026-12-11",
      "actividades": [
        "Visita a las Islas del Rosario",
        "Almuerzo de mariscos en la playa",
        "Atardecer en el Café del Mar"
      ]
    }
  ]
}
</ui>
```

Componente frontend: `ItineraryAgenda` — vista agenda por día.

---

### `reservation` — Reserva creada o actualizada

Producido por: **OrchestratorAgent** después de usar `create_reservation` o `update_reservation`.

```json
<ui type="reservation">
{
  "resId": "01ARZ3NDEKTSV4RRFFQ69G5FAW",
  "tripId": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "tipo": "VUELO",
  "estado": "SIMULADA",
  "detalle": {
    "aerolinea": "LATAM",
    "vuelo": "LA4410",
    "salida": "12:40",
    "llegada": "13:55",
    "precio_usd": 76
  }
}
</ui>
```

Componente frontend: `ReservationList` — refresca la lista de reservas con badge de estado.

---

## Instrucción al Orchestrator (extracto del system prompt)

```
Al responder, incluye siempre bloques <ui type="..."> con JSON válido cuando:
- Presentes opciones de vuelos: usa <ui type="flights">[...]</ui>
- Presentes pronóstico del clima: usa <ui type="weather">[...]</ui>
- Crees o actualices un viaje: usa <ui type="trip">{...}</ui>
- Generes un itinerario: usa <ui type="itinerary">{...}</ui>
- Crees o actualices una reserva: usa <ui type="reservation">{...}</ui>

Reenvía los bloques de FlightsAgent y WeatherAgent sin modificarlos.
El JSON debe ser serializado en una sola línea dentro de la etiqueta.
Nunca incluyas campos de pago (tarjeta, CVV, PIN) en ningún bloque.
```

---

## Parser en el frontend

```typescript
// Extrae pares [tipo, jsonString] de una respuesta del agente
function parseAgentBlocks(text: string): Array<{ type: string; data: unknown }> {
  const regex = /<ui type="([^"]+)">([\s\S]*?)<\/ui>/g;
  const blocks: Array<{ type: string; data: unknown }> = [];
  let match;
  while ((match = regex.exec(text)) !== null) {
    try {
      blocks.push({ type: match[1], data: JSON.parse(match[2].trim()) });
    } catch {
      // JSON inválido — ignorar bloque sin romper el render
    }
  }
  return blocks;
}
```
