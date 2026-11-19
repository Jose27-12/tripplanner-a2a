# TripPlanner AI

Asistente de viajes con IA sobre AWS, construido para el trabajo final de
Programación Agéntica. Combina una arquitectura multiagente (Strands Agents
+ Amazon Bedrock AgentCore) con un backend serverless (API Gateway + Lambda +
DynamoDB) y un frontend React, siguiendo el diseño de **dos canales
independientes** exigido por el enunciado.

- **Frontend:** https://d36x9vpivgz7mo.cloudfront.net
- **Documentación detallada:** [`docs/`](docs/) (arquitectura, modelo de datos, contrato de API, contrato de UI agéntica)

## 1. Arquitectura

Diagrama: [`docs/arquitectura-diagrama.svg`](docs/arquitectura-diagrama.svg).

```
Navegador
  ├─ Canal 1 (REST, datos) ──► API Gateway + Cognito ──► 12 Lambdas ──► DynamoDB
  └─ Canal 2 (streaming, IA) ─► AgentCore (JWT Cognito) ──► OrchestratorAgent
                                   ├─ ask_flights ──A2A──► FlightsAgent ──MCP──► FlightsMCP (simulado dinámico)
                                   ├─ ask_weather ──A2A──► WeatherAgent ──MCP──► WeatherMCP (Open-Meteo real)
                                   ├─ Exa AI (MCP, búsqueda web)
                                   └─ 11 tools ──boto3──► las mismas 12 Lambdas del Canal 1
```

Los dos canales nunca se cruzan: el frontend jamás llama a DynamoDB
directamente ni guarda credenciales AWS. El `user_id` nunca es un parámetro
libre — se extrae del JWT de Cognito en ambos canales (claim `sub` en API
Gateway; `actor_id` de la sesión de AgentCore en el canal agéntico).

Detalle completo, diagrama ASCII y decisiones de diseño: [`docs/arquitectura.md`](docs/arquitectura.md).

## 2. Modelo de datos

Tabla única DynamoDB `TripPlannerTable-<stage>` (`PK = USER#<sub>`, `SK`
identifica la entidad: `PROFILE`, `PREFS`, `TRIP#<id>`, `ITIN#<id>`,
`RES#<id>`), más `GSI1` para listar reservas por viaje sin conocer el
usuario dueño. Detalle de claves, atributos, estados y patrones de acceso:
[`docs/modelo-datos.md`](docs/modelo-datos.md).

## 3. API REST (Canal 1)

Base: `https://<api-id>.execute-api.us-east-1.amazonaws.com/prod`, con
`Authorization: Bearer <cognito_token>` en cada request. Endpoints para
viajes, itinerarios, reservas y preferencias (GET/POST/PUT). Contrato
completo con ejemplos de request/response y códigos de error:
[`docs/api-contrato.md`](docs/api-contrato.md).

## 4. Lambdas

12 funciones en `backend/functions/<nombre>/index.py`, Python 3.13,
arquitectura `arm64`, declaradas en [`backend/template.yaml`](backend/template.yaml):

| Dominio | Funciones |
|---|---|
| Viajes | `GetTrips`, `CreateTrip`, `GetTrip`, `UpdateTrip` |
| Itinerario | `GetItinerary`, `CreateItinerary`, `UpdateItinerary` |
| Reservas | `GetReservations`, `CreateReservation`, `UpdateReservation` |
| Preferencias | `GetPreferences`, `UpdatePreferences` |

Cada Lambda sigue el mismo patrón (`backend/common/python/common/`): extrae
`user_id` del JWT (`auth.py`), valida tipos/rangos/fechas/estados
(`validation.py` — rechaza explícitamente cualquier campo de pago), opera
sobre DynamoDB (`db.py`) y responde con códigos y CORS consistentes
(`response.py`). IAM de mínimo privilegio: cada función solo tiene
`GetItem`/`PutItem`/`UpdateItem`/`Query` sobre `TripPlannerTable` y su GSI1
(`LambdaDynamoBasePolicy` en el template).

## 5. Tools de los agentes

El `OrchestratorAgent` (`app/OrchestratorAgent/main.py`) expone 13 tools:

| Tool | Respaldo |
|---|---|
| `ask_flights`, `ask_weather` | Delegación A2A a `FlightsAgent`/`WeatherAgent` (firmado SigV4) |
| `create_trip`, `get_trips`, `update_trip` | Lambdas de viajes |
| `create_itinerary`, `get_itinerary`, `update_itinerary` | Lambdas de itinerario |
| `create_reservation`, `get_reservations`, `update_reservation` | Lambdas de reservas |
| `get_preferences`, `update_preferences` | Lambdas de preferencias |

El `user_id` se inyecta desde la sesión de AgentCore antes de cada tool — el
LLM nunca lo ve ni lo controla. Las tools de escritura exigen confirmación
explícita del usuario (ver system prompt del Orchestrator) y las reservas
siempre nacen en estado `SIMULADA`. `FlightsAgent` y `WeatherAgent` tienen
una única tool cada uno (`search_flights`, `get_forecast`) respaldada por su
propio servidor MCP (`FlightsMCP`, `WeatherMCP`).

## 6. Integración de agentes

- **Streaming:** el frontend llama directo al endpoint de AgentCore
  (`fetch` + `response.body.getReader()`), sin pasar por API Gateway, con
  `Authorization: Bearer <cognito_token>`. El runtime del Orchestrator tiene
  autorizador `CUSTOM_JWT` contra el mismo User Pool de Cognito del Canal 1.
- **MCP:** `FlightsAgent`/`WeatherAgent` consultan su propio servidor MCP
  (protocolo `MCP` en AgentCore); el Orchestrator usa un MCP externo (Exa AI)
  solo para búsqueda web adicional.
- **A2A:** el Orchestrator delega en los especialistas vía protocolo A2A,
  firmando cada request con SigV4 (rol de ejecución, permiso
  `bedrock-agentcore:InvokeAgentRuntime`). El descubrimiento de la
  "agent card" se reconstruye localmente (`a2a_auth.py::build_agent_card`)
  porque AgentCore no expone la ruta `.well-known/agent-card.json` que usa
  el resolver por defecto.
- **Modelo LLM:** proveedor configurable (`MODEL_PROVIDER`, por defecto
  `openrouter`) con una cadena de modelos gratuitos de OpenRouter con
  tool-calling y Gemini como último recurso si toda la cadena está saturada.
  Las API keys se guardan en AgentCore Identity (`ApiKeyCredentialProvider`),
  nunca en texto plano en `agentcore.json`.
- **Agent-driven UI:** los agentes emiten texto más bloques
  `<ui type="...">JSON</ui>` (vuelos, clima, viaje, itinerario, reserva); el
  frontend los parsea y renderiza el componente correspondiente sin una
  segunda llamada a la API. Formato exacto: [`docs/agente-ui-contract.md`](docs/agente-ui-contract.md).
- **Memoria:** `TripPlannerMemory` con tres estrategias de AgentCore
  (`USER_PREFERENCE`, `SUMMARIZATION`, `SEMANTIC`) — ayuda a conversar, pero
  DynamoDB sigue siendo la fuente de verdad de viajes/reservas.

## 7. Instrucciones de ejecución (desde cero)

### Requisitos
AWS CLI configurado, Node.js 20+, Python 3.10+ con `uv`, AWS SAM CLI.

### Backend (Canal 1)
```powershell
cd backend
.\deploy.ps1                      # sam build + sam deploy + publica el stage de API Gateway
.\test_backend.ps1                # prueba el flujo completo contra la API desplegada
```
Anota los outputs (`ApiUrl`, `UserPoolId`, `UserPoolClientId`) — también quedan en `backend/stack-outputs.json`.

### Agentes (Canal 2)
```bash
cd agentcore
# agentcore/.env.local debe tener GEMINI_API_KEY y OPENROUTER_API_KEY (no se versiona)
agentcore validate
agentcore deploy -y               # sintetiza y despliega agentcore/cdk a AWS
```
Las API keys de los modelos se guardan una sola vez en AgentCore Identity:
```bash
aws bedrock-agentcore-control create-api-key-credential-provider --name OpenRouterApiKey --cli-input-json file://credencial.json
```

### Frontend
```powershell
cd frontend
npm install
# frontend/.env.production con VITE_API_URL, VITE_COGNITO_*, VITE_ORCHESTRATOR_ARN (ver backend/stack-outputs.json y agentcore/.cli/deployed-state.json)
.\deploy.ps1                      # build + sube a S3 + invalida CloudFront
```

### Desarrollo local
```bash
cd app/OrchestratorAgent && uv sync && uv run main.py   # o `agentcore dev` desde la raíz para los tres agentes
cd frontend && npm run dev
```

## Repositorio

```
backend/        AWS SAM — Cognito, API Gateway, DynamoDB, 12 Lambdas (Python 3.13)
app/             5 runtimes de AgentCore: OrchestratorAgent, FlightsAgent, WeatherAgent, FlightsMCP, WeatherMCP
agentcore/       Proyecto declarativo de AgentCore (agentcore.json, aws-targets.json, cdk/) — fuente de verdad de la infra de agentes
frontend/        React + Vite + Tailwind, publicado en S3 + CloudFront
docs/            Arquitectura, modelo de datos, contrato de API, contrato de UI agéntica
```

Ver [`CLAUDE.md`](CLAUDE.md) para convenciones de código e invariantes de
seguridad que deben preservarse al modificar este repo.
