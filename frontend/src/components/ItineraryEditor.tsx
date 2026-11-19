import { useState } from "react";
import { api } from "../api/client";
import type { Itinerary, ItineraryDay, Trip } from "../api/types";
import { addDays, daysBetween, formatDate } from "../lib/format";
import { Alert, Button, Textarea } from "./ui";

/** Edita el itinerario día por día (una actividad por línea). */
export default function ItineraryEditor({
  trip, itinerary, onSaved, onCancel,
}: { trip: Trip; itinerary: Itinerary | null; onSaved: (it: Itinerary) => void; onCancel: () => void }) {
  const total = Math.min(daysBetween(trip.fecha_inicio, trip.fecha_fin), 60);
  const [days, setDays] = useState<string[]>(() =>
    Array.from({ length: total }, (_, i) => {
      const existing = itinerary?.dias.find((d) => d.dia === i + 1);
      return (existing?.actividades ?? []).join("\n");
    }),
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    setError("");
    const dias: ItineraryDay[] = days.map((text, i) => ({
      dia: i + 1,
      fecha: addDays(trip.fecha_inicio, i),
      actividades: text.split("\n").map((s) => s.trim()).filter(Boolean),
    }));
    try {
      onSaved(await api.saveItinerary(trip.tripId, dias, !!itinerary));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar el itinerario.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      {error && <Alert>{error}</Alert>}
      {days.map((text, i) => (
        <div key={i}>
          <p className="mb-1 text-sm font-medium text-slate-700">
            Día {i + 1} <span className="font-normal capitalize text-slate-500">· {formatDate(addDays(trip.fecha_inicio, i), { weekday: "long", day: "numeric", month: "short" })}</span>
          </p>
          <Textarea rows={3} placeholder={"Una actividad por línea\nEj.: Tour por la Ciudad Amurallada"} value={text}
            onChange={(e) => setDays(days.map((d, j) => (j === i ? e.target.value : d)))} />
        </div>
      ))}
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>Cancelar</Button>
        <Button onClick={save} loading={saving}>Guardar itinerario</Button>
      </div>
    </div>
  );
}
