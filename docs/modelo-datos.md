# Modelo de Datos — TripPlannerTable

## Tabla única (Single-Table Design)

**Nombre:** `TripPlannerTable`  
**Billing:** PAY_PER_REQUEST  
**Región:** us-east-1

### Justificación

El 100 % de las consultas son "por usuario". Una tabla única con `PK = USER#<sub>` garantiza:
- Aislamiento natural de datos entre usuarios (el filtro es estructural, no condicional).
- Consultas baratas con `begins_with` sobre el SK para cada tipo de entidad.
- Un solo recurso IAM para controlar acceso.

---

## Claves

| Atributo | Tipo | Rol |
|---|---|---|
| `PK` | String | Partition Key — siempre `USER#<cognito_sub>` |
| `SK` | String | Sort Key — prefijo identifica la entidad |
| `GSI1PK` | String | GSI Partition Key — `TRIP#<tripId>` |
| `GSI1SK` | String | GSI Sort Key — `RES#<resId>` |

---

## Entidades

### Usuario — perfil básico

| PK | SK | Atributos |
|---|---|---|
| `USER#<sub>` | `PROFILE` | `nombre`, `email`, `createdAt` |

### Preferencias de viaje

| PK | SK | Atributos |
|---|---|---|
| `USER#<sub>` | `PREFS` | `actividades[]`, `presupuesto_tipo` (`ECONOMICO`/`MODERADO`/`PREMIUM`), `restricciones[]`, `aerolineas_preferidas[]`, `asiento_preferido`, `updatedAt` |

### Viaje

| PK | SK | Atributos |
|---|---|---|
| `USER#<sub>` | `TRIP#<tripId>` | `tripId`, `origen`, `destino`, `fecha_inicio` (ISO 8601), `fecha_fin` (ISO 8601), `viajeros` (≥ 1), `presupuesto` (número), `moneda` (`COP`/`USD`), `estado` (`PLANIFICANDO`/`CONFIRMADO`/`CANCELADO`), `createdAt`, `updatedAt` |

**Validaciones:**
- `fecha_fin >= fecha_inicio`
- `viajeros >= 1`
- `estado` solo acepta los 3 valores listados

### Itinerario

| PK | SK | Atributos |
|---|---|---|
| `USER#<sub>` | `ITIN#<tripId>` | `tripId`, `dias[]` donde cada día es `{ dia: int, fecha: string, actividades: string[] }`, `updatedAt` |

### Reserva

| PK | SK | GSI1PK | GSI1SK | Atributos |
|---|---|---|---|---|
| `USER#<sub>` | `RES#<resId>` | `TRIP#<tripId>` | `RES#<resId>` | `resId`, `tripId`, `tipo` (`VUELO`/`HOTEL`/`ACTIVIDAD`), `estado` (`SIMULADA`/`PENDIENTE`/`CONFIRMADA`), `detalle` (objeto libre), `createdAt`, `updatedAt` |

**Validaciones:**
- `tipo` solo acepta los 3 valores listados
- `estado` solo acepta los 3 valores listados
- El objeto `detalle` **nunca** contiene campos de pago (tarjeta, CVV, etc.)

---

## GSI

### GSI1 — Reservas por viaje

Permite listar todas las reservas de un viaje específico sin conocer el `user_id` en la query secundaria.

| Atributo | Valor |
|---|---|
| `GSI1PK` | `TRIP#<tripId>` |
| `GSI1SK` | `RES#<resId>` |
| Proyección | ALL |

---

## Patrones de acceso

| Operación | Acceso DynamoDB |
|---|---|
| Listar viajes del usuario | `Query PK=USER#<sub>, begins_with(SK, "TRIP#")` |
| Obtener viaje | `GetItem PK=USER#<sub>, SK=TRIP#<tripId>` |
| Listar reservas del usuario | `Query PK=USER#<sub>, begins_with(SK, "RES#")` |
| Listar reservas de un viaje | `Query GSI1 GSI1PK=TRIP#<tripId>` |
| Obtener itinerario | `GetItem PK=USER#<sub>, SK=ITIN#<tripId>` |
| Obtener preferencias | `GetItem PK=USER#<sub>, SK=PREFS` |

---

## Estados de Reserva

```
SIMULADA  →  PENDIENTE  →  CONFIRMADA
```

Solo el sistema avanza el estado. El usuario nunca puede saltar de `SIMULADA` a `CONFIRMADA` directamente.

---

## IDs

- `tripId`: `ulid()` generado en la Lambda (no auto-increment, seguro para distribuido)
- `resId`: `ulid()` generado en la Lambda
- `sub`: JWT claim `sub` de Cognito — nunca un parámetro libre del cliente
