// Cliente del canal 1: navegador -> API Gateway (autorizador Cognito) -> Lambda -> DynamoDB.
// Adjunta el ID Token de Cognito; nunca usa credenciales AWS ni toca DynamoDB.
import { currentSession } from "../auth/cognito";
import { SESSION_EXPIRED_EVENT } from "../auth/AuthContext";
import { config } from "../config";
import type { Itinerary, ItineraryDay, Preferences, Reservation, ReservaEstado, Trip, TripInput } from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const session = await currentSession();
  if (!session) {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    throw new ApiError(401, "Tu sesión expiró. Inicia sesión de nuevo.");
  }

  let response: Response;
  try {
    response = await fetch(`${config.apiUrl}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${session.idToken}`,
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "No hay conexión con el servidor. Revisa tu conexión a internet.");
  }

  if (response.status === 401) {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    throw new ApiError(401, "Tu sesión expiró. Inicia sesión de nuevo.");
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      (data as { error?: string }).error ??
      (response.status === 429 ? "Demasiadas solicitudes. Espera un momento." : "Ocurrió un error inesperado.");
    throw new ApiError(response.status, message);
  }
  return data as T;
}

export const api = {
  // Viajes
  listTrips: () => request<{ trips: Trip[] }>("GET", "/trips").then((r) => r.trips),
  getTrip: (id: string) => request<Trip>("GET", `/trips/${encodeURIComponent(id)}`),
  createTrip: (input: TripInput) => request<Trip>("POST", "/trips", input),
  updateTrip: (id: string, input: Partial<TripInput>) =>
    request<Trip>("PUT", `/trips/${encodeURIComponent(id)}`, input),

  // Itinerario (404 si el viaje aún no tiene)
  getItinerary: async (tripId: string): Promise<Itinerary | null> => {
    try {
      return await request<Itinerary>("GET", `/trips/${encodeURIComponent(tripId)}/itinerary`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  },
  saveItinerary: (tripId: string, dias: ItineraryDay[], exists: boolean) =>
    request<Itinerary>(exists ? "PUT" : "POST", `/trips/${encodeURIComponent(tripId)}/itinerary`, { dias }),

  // Reservas
  listReservations: (tripId?: string) =>
    request<{ reservations: Reservation[] }>(
      "GET",
      tripId ? `/reservations?tripId=${encodeURIComponent(tripId)}` : "/reservations",
    ).then((r) => r.reservations),
  createReservation: (input: { tripId: string; tipo: Reservation["tipo"]; detalle: Record<string, unknown> }) =>
    request<Reservation>("POST", "/reservations", input),
  updateReservation: (id: string, input: { estado?: ReservaEstado; detalle?: Record<string, unknown> }) =>
    request<Reservation>("PUT", `/reservations/${encodeURIComponent(id)}`, input),

  // Preferencias
  getPreferences: () => request<Preferences>("GET", "/preferences"),
  savePreferences: (prefs: Preferences) => request<Preferences>("PUT", "/preferences", prefs),
};
