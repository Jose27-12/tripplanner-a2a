# Arquitectura — TripPlanner AI

## Visión general

El sistema tiene **dos canales independientes** para manejar datos y conversación:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USUARIO (Navegador)                        │
│                    React + Vite + Tailwind (S3/CloudFront)          │
└──────────────────────┬──────────────────────────┬───────────────────┘
                       │                          │
              Canal 1  │                Canal 2  │
           (API REST)  │            (Streaming AI)│
                       ▼                          ▼
        ┌──────────────────────┐    ┌─────────────────────────────┐
        │   Amazon API Gateway │    │   Amazon Bedrock AgentCore  │
        │   + Cognito Auth     │    │   OrchestratorAgent (HTTP)  │
        └──────────┬───────────┘    └──────────────┬──────────────┘
                   │                               │
                   ▼                               │  A2A
        ┌──────────────────────┐         ┌─────────┴──────────┐
        │  AWS Lambda (11 fns) │         │   FlightsAgent     │
        │  Python 3.10         │         │   WeatherAgent     │
        └──────────┬───────────┘         │   (AgentCore A2A)  │
                   │                     └────────────────────┘
                   ▼                               │
        ┌──────────────────────┐                   │  MCP
        │  Amazon DynamoDB     │         ┌─────────▼──────────┐
        │  TripPlannerTable    │         │   Exa AI MCP       │
        │  (Single Table)      │         │   (búsqueda web)   │
        └──────────────────────┘         └────────────────────┘
                   ▲
                   │  boto3 (IAM, no credenciales en código)
        ┌──────────┴───────────┐
        │  OrchestratorAgent   │
        │  (8 tools → Lambda)  │
        └──────────────────────┘
```

---

## Canal 1 — API REST (datos persistentes)

**Propósito:** CRUD directo sobre los datos del usuario. El frontend llama a este canal para operaciones que no requieren IA: ver viajes guardados, editar itinerario, consultar reservas.

**Componentes:**
- **Amazon Cognito** — User Pool para registro/login. El token JWT viaja en cada request.
- **Amazon API Gateway** — Recibe el request, valida el token con el Cognito Authorizer, enruta a la Lambda.
- **AWS Lambda (11 funciones)** — Una por operación. Extraen `user_id` del JWT, operan sobre DynamoDB con permisos mínimos.
- **Amazon DynamoDB** — Tabla única `TripPlannerTable`. Todos los datos del usuario viven aquí.

**Flujo típico:**
```
Navegador → API Gateway (valida JWT) → Lambda → DynamoDB → Lambda → API Gateway → Navegador
```

---

## Canal 2 — AgentCore Streaming (conversación IA)

**Propósito:** Interacción conversacional con el agente. El frontend transmite el prompt del usuario y recibe la respuesta en streaming con texto + bloques `<ui>`.

**Componentes:**
- **OrchestratorAgent** — Agente principal (HTTP, Python/Strands). Orquesta todo.
  - Tiene 8 tools que invocan las Lambdas del Canal 1 vía `boto3.client("lambda")`.
  - El `user_id` se inyecta desde el contexto JWT de AgentCore — el LLM nunca lo ve como parámetro.
  - Tiene acceso a memoria persistente (`TripPlannerMemory`) con 3 estrategias.
- **FlightsAgent** — Agente especialista A2A. Responde consultas de vuelos.
- **WeatherAgent** — Agente especialista A2A. Responde consultas de clima.
- **Exa AI MCP** — Servidor MCP externo para búsquedas web enriquecidas.

**Flujo de conversación:**
```
Navegador (Bearer token) → AgentCore → OrchestratorAgent
  ├─→ ask_flights → FlightsAgent A2A → <ui type="flights">
  ├─→ ask_weather → WeatherAgent A2A → <ui type="weather">
  ├─→ create_trip → Lambda CreateTrip → DynamoDB → <ui type="trip">
  ├─→ create_itinerary → Lambda CreateItinerary → DynamoDB → <ui type="itinerary">
  └─→ create_reservation → Lambda CreateReservation → DynamoDB → <ui type="reservation">
```

---

## Autenticación y autorización

| Capa | Mecanismo |
|---|---|
| Frontend → API Gateway | JWT (Cognito ID Token) en header `Authorization: Bearer` |
| Frontend → AgentCore | JWT (Cognito ID Token) — Runtime configurado con JWT authorizer |
| Lambda → DynamoDB | IAM Role (mínimo privilegio — solo las acciones necesarias sobre la tabla) |
| OrchestratorAgent → Lambda | IAM Role (permiso `lambda:InvokeFunction` solo sobre las 8 Lambdas del backend) |
| Nunca | Credenciales AWS en código del navegador |
| Nunca | El frontend llama directamente a DynamoDB |

---

## Decisiones de diseño

### Single-table DynamoDB
Todas las entidades del usuario en una tabla. Consultas baratas, control de acceso natural por `PK = USER#<sub>`.

### `user_id` nunca como parámetro libre
En el Canal 1: extraído de `event.requestContext.authorizer.claims.sub` (API Gateway).  
En el Canal 2: extraído del contexto de sesión de AgentCore e inyectado en el payload Lambda.  
El LLM no puede suplantar a otro usuario porque nunca maneja ese valor.

### Reservas siempre como SIMULADA
Ninguna reserva crea cargos reales. El estado `SIMULADA` es el inicial y obligatorio. El sistema puede avanzarlo, pero no procesa pagos.

### Streaming con bloques `<ui>`
La respuesta del agente combina texto markdown y JSON estructurado en una sola transmisión. El frontend parsea las etiquetas `<ui type="...">` y renderiza componentes específicos sin una segunda llamada a la API.

### app/ se mantiene como nombre de carpeta
Los agentes viven en `app/` porque así los referencia `agentcore.json` y el CDK generado. Renombrar requeriría redeplegar la infraestructura sin beneficio funcional.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Auth | Amazon Cognito (User Pool + App Client SRP) |
| API | Amazon API Gateway (REST) + AWS Lambda (Python 3.10) |
| Base de datos | Amazon DynamoDB (single-table, PAY_PER_REQUEST) |
| Agentes | Amazon Bedrock AgentCore + Strands SDK |
| Modelo LLM | Gemini (gemini-3.7-flash) |
| Memoria | AgentCore Memory (USER_PREFERENCE + SUMMARIZATION + SEMANTIC) |
| Búsqueda web | Exa AI vía MCP |
| IaC agentes | AWS CDK (`@aws/agentcore-cdk`) |
| IaC backend | AWS SAM (template.yaml) |
| Hosting frontend | Amazon S3 + Amazon CloudFront + OAC |
| Región | us-east-1 |
