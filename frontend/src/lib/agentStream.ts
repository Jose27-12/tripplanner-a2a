// Canal 2: navegador -> HTTP streaming directo a Amazon Bedrock AgentCore (sin API Gateway).
// Se autentica con el Access Token de Cognito (authorizer CUSTOM_JWT del runtime);
// el navegador nunca tiene credenciales AWS. El user_id lo saca AgentCore del token.
import { currentSession } from "../auth/cognito";
import { SESSION_EXPIRED_EVENT } from "../auth/AuthContext";
import { agentInvocationUrl } from "../config";

export type AgentEvent =
  | { kind: "text"; text: string }
  | { kind: "tool"; name: string }
  | { kind: "error"; message: string };

/** Envía un mensaje al Orchestrator y produce los eventos según llegan. */
export async function* streamAgent(prompt: string, sessionId: string, signal?: AbortSignal): AsyncGenerator<AgentEvent> {
  const session = await currentSession();
  if (!session) {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    yield { kind: "error", message: "Tu sesión expiró. Inicia sesión de nuevo." };
    return;
  }

  let response: Response;
  try {
    response = await fetch(agentInvocationUrl, {
      method: "POST",
      signal,
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        // Mismo id durante toda la conversación: AgentCore enruta a la misma
        // sesión y la memoria del agente conserva el contexto.
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": sessionId,
      },
      body: JSON.stringify({ prompt }),
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") return;
    yield { kind: "error", message: "No hay conexión con el asistente. Revisa tu conexión a internet." };
    return;
  }

  if (response.status === 401 || response.status === 403) {
    yield { kind: "error", message: "No autorizado. Cierra sesión y vuelve a entrar." };
    return;
  }
  if (!response.ok || !response.body) {
    yield {
      kind: "error",
      message: response.status === 429
        ? "El asistente está recibiendo muchas solicitudes. Inténtalo en un momento."
        : "El asistente no está disponible en este momento.",
    };
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const event = parseLine(line);
        if (event) yield event;
      }
    }
    const last = parseLine(buffer);
    if (last) yield last;
  } catch (e) {
    if ((e as Error).name !== "AbortError") yield { kind: "error", message: "Se interrumpió la conexión con el asistente." };
  }
}

function parseLine(raw: string): AgentEvent | null {
  const line = raw.trim();
  if (!line.startsWith("data:")) return null;
  const data = line.slice(5).trim();
  if (!data) return null;
  let event: unknown;
  try {
    event = JSON.parse(data);
  } catch {
    return { kind: "text", text: data };
  }
  if (typeof event === "string") return { kind: "text", text: event };
  if (!event || typeof event !== "object") return null;
  const e = event as Record<string, any>;
  if (e.error) return { kind: "error", message: "El asistente tuvo un problema procesando tu mensaje. Inténtalo de nuevo." };
  const inner = e.event ?? {};
  const text = inner.contentBlockDelta?.delta?.text;
  if (typeof text === "string") return { kind: "text", text };
  const toolName = inner.contentBlockStart?.start?.toolUse?.name;
  if (typeof toolName === "string") return { kind: "tool", name: toolName };
  return null;
}

/** Tools que modifican datos: al usarlas, las pantallas del canal 1 se refrescan. */
export const MUTATING_TOOLS = new Set([
  "create_trip", "update_trip", "create_itinerary", "update_itinerary",
  "create_reservation", "update_reservation", "update_preferences",
]);

export const TOOL_LABELS: Record<string, string> = {
  ask_flights: "Consultando vuelos con el agente de vuelos",
  ask_weather: "Consultando el clima con el agente meteorológico",
  create_trip: "Guardando el viaje",
  get_trips: "Revisando tus viajes",
  update_trip: "Actualizando el viaje",
  create_itinerary: "Guardando el itinerario",
  update_itinerary: "Actualizando el itinerario",
  get_itinerary: "Consultando el itinerario",
  create_reservation: "Registrando la reserva simulada",
  get_reservations: "Revisando tus reservas",
  update_reservation: "Actualizando la reserva",
  get_preferences: "Revisando tus preferencias",
  update_preferences: "Guardando tus preferencias",
};

export function newSessionId() {
  // AgentCore exige ids de sesión de al menos 33 caracteres.
  return `chat-${crypto.randomUUID()}`;
}
