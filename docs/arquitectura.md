# Arquitectura — TripPlanner AI

Diagrama (imagen, entregable 4 del PDF): [`arquitectura-diagrama.svg`](arquitectura-diagrama.svg).

## Visión general

El sistema tiene **dos canales independientes** para manejar datos y conversación:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USUARIO (Navegador)                        │
│                    React + Vite + Tailwind (S3/CloudFront)          │
└──────────────────────┬──────────────────────────┬───────────────────┘
                       │                          │
              Canal 1  │                Canal 2  │
           (API REST)  │      (Streaming AI, JWT Cognito directo)│
                       ▼                          ▼
        ┌──────────────────────┐    ┌─────────────────────────────┐
        │   Amazon API Gateway │    │   Amazon Bedrock AgentCore  │
        │   + Cognito Auth     │    │   OrchestratorAgent (HTTP)  │
        └──────────┬───────────┘    │   CUSTOM_JWT (Cognito)      │
                   │                └──────────────┬──────────────┘
                   ▼                               │
        ┌──────────────────────┐          ┌────────┼────────────┐
        │  AWS Lambda (12 fns) │          │ A2A    │     Exa AI  │ MCP
        │  Python 3.13         │          ▼        │     ▼       │
        └──────────┬───────────┘  ┌──────────────┐ │ ┌─────────┐ │
                   │              │ FlightsAgent │ │ │ Exa MCP │ │
                   ▼              │ WeatherAgent │ │ │(búsqueda│ │
        ┌──────────────────────┐ │ (AgentCore   │ │ │  web)   │ │
        │  Amazon DynamoDB     │ │  A2A)        │ │ └─────────┘ │
        │  TripPlannerTable    │ └──────┬───────┘ └─────────────┘
        │  (Single Table)      │        │ MCP
        └──────────────────────┘ ┌──────▼───────┐
                   ▲              │ FlightsMCP   │ (simulado, dinámico)
                   │              │ WeatherMCP   │ (Open-Meteo, real)
                   │              └──────────────┘
                   │  boto3 (IAM, no credenciales en código)
        ┌──────────┴───────────┐
        │  OrchestratorAgent   │
        │  (13 tools: 2 A2A +  │
        │   11 → Lambda)       │
        └──────────────────────┘
```

**Modelo LLM:** los tres agentes (Orchestrator, Flights, Weather) usan el mismo
esquema de carga de modelo (`MODEL_PROVIDER`, por defecto `openrouter`): una
cadena de ~10 modelos **gratuitos** de OpenRouter con soporte de tool-calling,
y si toda la cadena está saturada, caen a **Gemini** como último recurso.
Las API keys (OpenRouter, Gemini, Anthropic si se usara) nunca viajan en texto
plano: se guardan como `ApiKeyCredentialProvider` en AgentCore Identity y se
leen en tiempo de petición con el Workload Access Token de la invocación.

---

## Canal 1 — API REST (datos persistentes)

**Propósito:** CRUD directo sobre los datos del usuario. El frontend llama a este canal para operaciones que no requieren IA: ver viajes guardados, editar itinerario, consultar reservas.

**Componentes:**
- **Amazon Cognito** — User Pool para registro/login. El token JWT viaja en cada request.
- **Amazon API Gateway** — Recibe el request, valida el token con el Cognito Authorizer, enruta a la Lambda.
- **AWS Lambda (12 funciones)** — Una por operación. Extraen `user_id` del JWT, operan sobre DynamoDB con permisos mínimos.
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
  - Tiene 13 tools: `ask_flights`/`ask_weather` (delegan por A2A) + 11 que invocan las Lambdas del Canal 1 vía `boto3.client("lambda")`.
  - El `user_id` se inyecta desde el contexto JWT de AgentCore — el LLM nunca lo ve como parámetro.
  - Tiene acceso a memoria persistente (`TripPlannerMemory`) con 3 estrategias.
  - Endpoint protegido con autorizador `CUSTOM_JWT` contra el mismo User Pool de Cognito del Canal 1 — el navegador usa su propio token, sin credenciales AWS.
- **FlightsAgent** — Agente especialista A2A. Responde consultas de vuelos consultando su propio servidor **FlightsMCP** (datos simulados pero dinámicos, no fijos).
- **WeatherAgent** — Agente especialista A2A. Responde consultas de clima consultando su propio servidor **WeatherMCP** (datos reales de Open-Meteo).
- **Exa AI MCP** — Servidor MCP externo que usa el Orchestrator para búsquedas web enriquecidas (no vuelos/clima).

**Flujo de conversación:**
```
Navegador (Bearer token Cognito) → AgentCore (CUSTOM_JWT) → OrchestratorAgent
  ├─→ ask_flights → FlightsAgent (A2A, SigV4) → FlightsMCP → <ui type="flights">
  ├─→ ask_weather → WeatherAgent (A2A, SigV4) → WeatherMCP (Open-Meteo) → <ui type="weather">
  ├─→ create_trip → Lambda CreateTrip → DynamoDB → <ui type="trip">
  ├─→ create_itinerary → Lambda CreateItinerary → DynamoDB → <ui type="itinerary">
  └─→ create_reservation → Lambda CreateReservation → DynamoDB → <ui type="reservation">
```

**Descubrimiento A2A sin red:** AgentCore solo expone una ruta por runtime
(`POST .../invocations`, firmada con SigV4, autorizada vía
`bedrock-agentcore:InvokeAgentRuntime`). El resolver por defecto de `a2a-sdk`
intenta primero un `GET .../invocations/.well-known/agent-card.json`, que
AgentCore no expone (devuelve 403, no es una acción IAM válida). El
Orchestrator reconstruye la `AgentCard` localmente (mismo contrato que usa
`bedrock_agentcore.runtime.serve_a2a` del lado del especialista) y se la
inyecta al cliente A2A para saltar ese descubrimiento por HTTP
(`app/OrchestratorAgent/a2a_auth.py::build_agent_card`).

---

## Autenticación y autorización

| Capa | Mecanismo |
|---|---|
| Frontend → API Gateway | JWT (Cognito ID Token) en header `Authorization: Bearer` |
| Frontend → AgentCore | JWT (Cognito Access Token) — Runtime con autorizador `CUSTOM_JWT` contra el User Pool |
| Lambda → DynamoDB | IAM Role (mínimo privilegio — solo las acciones necesarias sobre la tabla) |
| OrchestratorAgent → Lambda | IAM Role (permiso `lambda:InvokeFunction` solo sobre las 11 Lambdas que invocan sus tools) |
| OrchestratorAgent → Flights/WeatherAgent | IAM Role (`bedrock-agentcore:InvokeAgentRuntime`/`InvokeAgentRuntimeForUser`, SigV4) |
| Agentes → OpenRouter/Gemini | AgentCore Identity (`ApiKeyCredentialProvider`), key nunca en texto plano |
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
| Frontend | React 19 + Vite + Tailwind CSS 4 + react-router |
| Auth | Amazon Cognito (User Pool + App Client SRP, sin secret) |
| API | Amazon API Gateway (REST) + AWS Lambda (Python 3.13, 12 funciones) |
| Base de datos | Amazon DynamoDB (single-table, PAY_PER_REQUEST) |
| Agentes | Amazon Bedrock AgentCore + Strands SDK (Python 3.14) |
| Modelo LLM | OpenRouter (~10 modelos gratuitos con tool-calling, cadena de respaldo) → Gemini como último recurso |
| Herramientas de vuelos/clima | FlightsMCP (simulado dinámico) y WeatherMCP (Open-Meteo real), protocolo MCP, un servidor por especialista |
| Memoria | AgentCore Memory (USER_PREFERENCE + SUMMARIZATION + SEMANTIC) |
| Búsqueda web adicional | Exa AI vía MCP (solo el Orchestrator) |
| IaC agentes | AWS CDK (`@aws/agentcore-cdk`), gestionado por `agentcore/` (la copia en la raíz está obsoleta) |
| IaC backend | AWS SAM (`backend/template.yaml`) |
| Hosting frontend | Amazon S3 + Amazon CloudFront + OAC |
| Región | us-east-1 |
