// Traduce cada bloque <ui type="..."> del agente al componente visual adecuado.
import type { Itinerary, Reservation, Trip } from "../api/types";
import { FlightCards, WeatherCards, type Flight, type WeatherDay } from "./agentCards";
import { ItineraryAgenda, ReservationList, TripCard } from "./domain";
import { Spinner } from "./ui";

const asArray = <T,>(data: unknown): T[] => (Array.isArray(data) ? (data as T[]) : data ? [data as T] : []);

export function AgentBlock({ type, data }: { type: string; data: unknown }) {
  switch (type) {
    case "flights":
      return <FlightCards flights={asArray<Flight>(data)} />;
    case "weather":
      return <WeatherCards days={asArray<WeatherDay>((data as { dias?: unknown })?.dias ?? data)} />;
    case "trip":
      return <div className="max-w-sm"><TripCard trip={data as Trip} /></div>;
    case "trips":
      return (
        <div className="grid gap-3 sm:grid-cols-2">
          {asArray<Trip>(data).map((t) => <TripCard key={t.tripId} trip={t} />)}
        </div>
      );
    case "itinerary":
      return <ItineraryAgenda itinerary={data as Itinerary} />;
    case "reservation":
    case "reservations":
      return <ReservationList reservations={asArray<Reservation>(data)} />;
    default:
      return (
        <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(data, null, 2)}</pre>
      );
  }
}

const PENDING_LABEL: Record<string, string> = {
  flights: "Preparando vuelos",
  weather: "Preparando pronóstico",
  trip: "Preparando viaje",
  itinerary: "Preparando itinerario",
  reservation: "Preparando reserva",
};

export function AgentBlockPending({ type }: { type: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-dashed border-slate-300 px-3 py-2 text-xs text-slate-500">
      <Spinner className="h-3.5 w-3.5" /> {PENDING_LABEL[type] ?? "Preparando resultados"}...
    </div>
  );
}
