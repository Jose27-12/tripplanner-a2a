# Contrato de la API REST — Canal 1

## Base

```
https://<api-id>.execute-api.us-east-1.amazonaws.com/prod
```

Todos los endpoints requieren:
```
Authorization: Bearer <cognito_id_token>
Content-Type: application/json
```

El `user_id` se extrae **siempre** de `event.requestContext.authorizer.claims.sub`. Nunca es un parámetro del cliente.

---

## Endpoints

### Viajes

#### `GET /trips`
Lista todos los viajes del usuario autenticado.

**Response 200**
```json
{
  "trips": [
    {
      "tripId": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
      "origen": "Bogotá",
      "destino": "Cartagena",
      "fecha_inicio": "2026-12-10",
      "fecha_fin": "2026-12-14",
      "viajeros": 3,
      "presupuesto": 5000000,
      "moneda": "COP",
      "estado": "PLANIFICANDO",
      "createdAt": "2026-11-18T22:00:00Z"
    }
  ]
}
```

#### `POST /trips`
Crea un nuevo viaje.

**Body**
```json
{
  "origen": "Bogotá",
  "destino": "Cartagena",
  "fecha_inicio": "2026-12-10",
  "fecha_fin": "2026-12-14",
  "viajeros": 3,
  "presupuesto": 5000000,
  "moneda": "COP"
}
```

**Validaciones:** `fecha_fin >= fecha_inicio`, `viajeros >= 1`, `presupuesto > 0`.  
**Response 201** — objeto viaje completo con `tripId` generado.  
**Response 400** — validación fallida: `{ "error": "mensaje descriptivo" }`

#### `GET /trips/{id}`
Obtiene un viaje por ID. Devuelve 404 si no pertenece al usuario.

#### `PUT /trips/{id}`
Actualiza campos del viaje. Mismas validaciones que POST.  
**Response 200** — objeto viaje actualizado.

---

### Itinerario

#### `GET /trips/{id}/itinerary`
Obtiene el itinerario del viaje. 404 si no existe.

**Response 200**
```json
{
  "tripId": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "dias": [
    {
      "dia": 1,
      "fecha": "2026-12-10",
      "actividades": ["Llegada al aeropuerto", "Check-in hotel", "Paseo por el centro histórico"]
    }
  ],
  "updatedAt": "2026-11-18T22:00:00Z"
}
```

#### `POST /trips/{id}/itinerary`
Crea el itinerario del viaje (reemplaza si ya existe).

#### `PUT /trips/{id}/itinerary`
Actualiza el itinerario existente.

---

### Reservas

#### `GET /reservations`
Lista todas las reservas del usuario. Acepta query param `?tripId=<id>` para filtrar por viaje.

**Response 200**
```json
{
  "reservations": [
    {
      "resId": "01ARZ3NDEKTSV4RRFFQ69G5FAW",
      "tripId": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
      "tipo": "VUELO",
      "estado": "SIMULADA",
      "detalle": {
        "aerolinea": "Avianca",
        "vuelo": "AV9821",
        "salida": "07:15",
        "llegada": "08:30",
        "precio_usd": 89
      },
      "createdAt": "2026-11-18T22:00:00Z"
    }
  ]
}
```

#### `POST /reservations`
Crea una reserva. El estado inicial es siempre `SIMULADA`.

**Body**
```json
{
  "tripId": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "tipo": "VUELO",
  "detalle": { ... }
}
```

**Validaciones:** `tipo` en `[VUELO, HOTEL, ACTIVIDAD]`, `tripId` debe existir y pertenecer al usuario, `detalle` no puede contener campos de pago.  
**Response 201** — objeto reserva con `resId` y `estado: SIMULADA`.

#### `PUT /reservations/{id}`
Actualiza una reserva. Permite cambiar `estado` siguiendo la secuencia `SIMULADA → PENDIENTE → CONFIRMADA`.  
**Response 200** — objeto reserva actualizado.

---

### Preferencias

#### `GET /preferences`
Obtiene las preferencias del usuario. Si no existen, devuelve objeto vacío `{}`.

#### `PUT /preferences`
Crea o reemplaza las preferencias.

**Body**
```json
{
  "actividades": ["playa", "gastronomia"],
  "presupuesto_tipo": "MODERADO",
  "restricciones": ["sin_mariscos"],
  "aerolineas_preferidas": ["Avianca"],
  "asiento_preferido": "ventana"
}
```

---

## Códigos de respuesta

| Código | Significado |
|---|---|
| 200 | OK |
| 201 | Creado |
| 400 | Validación fallida |
| 401 | Sin token o token inválido |
| 403 | Token válido pero sin permiso sobre ese recurso |
| 404 | Recurso no encontrado o no pertenece al usuario |
| 500 | Error interno (sin detalles expuestos) |

## CORS

El header `Access-Control-Allow-Origin` se restringe al dominio de CloudFront configurado en la variable de entorno `FRONTEND_ORIGIN`.

## Throttling

- Rate: 100 req/s por etapa
- Burst: 200 req/s

---

## Lambdas

| Ruta + Método | Lambda |
|---|---|
| `GET /trips` | `GetTripsFunction` |
| `POST /trips` | `CreateTripFunction` |
| `GET /trips/{id}` | `GetTripFunction` |
| `PUT /trips/{id}` | `UpdateTripFunction` |
| `GET /trips/{id}/itinerary` | `GetItineraryFunction` |
| `POST /trips/{id}/itinerary` | `CreateItineraryFunction` |
| `PUT /trips/{id}/itinerary` | `UpdateItineraryFunction` |
| `GET /reservations` | `GetReservationsFunction` |
| `POST /reservations` | `CreateReservationFunction` |
| `PUT /reservations/{id}` | `UpdateReservationFunction` |
| `GET /preferences` | `GetPreferencesFunction` |
| `PUT /preferences` | `UpdatePreferencesFunction` |
