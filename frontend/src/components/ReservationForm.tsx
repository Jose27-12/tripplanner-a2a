import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Reservation, ReservaEstado, ReservaTipo, Trip } from "../api/types";
import { ReservationStatusBadge } from "./domain";
import { Alert, Button, Field, Input, Select } from "./ui";

// Campos del detalle por tipo. Nunca se piden datos de pago (prohibido por el PDF
// y rechazado también en el servidor).
const FIELDS: Record<ReservaTipo, { key: string; label: string; type?: string; placeholder?: string }[]> = {
  VUELO: [
    { key: "aerolinea", label: "Aerolínea", placeholder: "Avianca" },
    { key: "vuelo", label: "N.º de vuelo", placeholder: "AV9821" },
    { key: "fecha", label: "Fecha", type: "date" },
    { key: "salida", label: "Salida", type: "time" },
    { key: "llegada", label: "Llegada", type: "time" },
    { key: "pasajeros", label: "Pasajeros", type: "number" },
  ],
  HOTEL: [
    { key: "hotel", label: "Hotel", placeholder: "Hotel Caribe" },
    { key: "check_in", label: "Check-in", type: "date" },
    { key: "check_out", label: "Check-out", type: "date" },
    { key: "habitaciones", label: "Habitaciones", type: "number" },
  ],
  ACTIVIDAD: [
    { key: "actividad", label: "Actividad", placeholder: "Tour Islas del Rosario" },
    { key: "fecha", label: "Fecha", type: "date" },
    { key: "hora", label: "Hora", type: "time" },
    { key: "lugar", label: "Lugar", placeholder: "Muelle de La Bodeguita" },
  ],
};

// Avance permitido. CONFIRMADA queda reservado para un proveedor real.
const NEXT: Record<ReservaEstado, ReservaEstado[]> = {
  SIMULADA: ["SIMULADA", "PENDIENTE"],
  PENDIENTE: ["PENDIENTE"],
  CONFIRMADA: ["CONFIRMADA"],
};

export default function ReservationForm({
  trips, reservation, defaultTripId, onSaved, onCancel,
}: {
  trips: Trip[];
  reservation?: Reservation;
  defaultTripId?: string;
  onSaved: (r: Reservation) => void;
  onCancel: () => void;
}) {
  const editing = !!reservation;
  const [tripId, setTripId] = useState(reservation?.tripId ?? defaultTripId ?? trips[0]?.tripId ?? "");
  const [tipo, setTipo] = useState<ReservaTipo>(reservation?.tipo ?? "VUELO");
  const [estado, setEstado] = useState<ReservaEstado>(reservation?.estado ?? "SIMULADA");
  const [detalle, setDetalle] = useState<Record<string, string>>(
    Object.fromEntries(Object.entries(reservation?.detalle ?? {}).map(([k, v]) => [k, v == null ? "" : String(v)])),
  );
  const [precio, setPrecio] = useState(String(reservation?.detalle?.precio_cop ?? reservation?.detalle?.precio ?? ""));
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!tripId) return setError("Asocia la reserva a un viaje.");
    setError("");
    setSaving(true);
    const clean: Record<string, unknown> = {};
    const original = reservation?.detalle ?? {};
    for (const [k, v] of Object.entries(detalle)) {
      if (v === "" || k === "precio" || k === "precio_cop") continue;
      const field = FIELDS[tipo].find((f) => f.key === k);
      // Campos que el formulario no muestra (p. ej. los que guardó el agente) conservan su valor original.
      if (!field && k in original) clean[k] = original[k];
      else clean[k] = field?.type === "number" ? Number(v) : v;
    }
    if (precio) {
      clean.precio_cop = Number(precio);
      clean.moneda = "COP";
    }
    try {
      onSaved(
        editing
          ? await api.updateReservation(reservation!.resId, { detalle: clean, ...(estado !== reservation!.estado ? { estado } : {}) })
          : await api.createReservation({ tripId, tipo, detalle: clean }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar la reserva.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Alert kind="info">Las reservas son <b>simuladas</b>: no se procesan pagos ni se piden datos de tarjeta.</Alert>
      {error && <Alert>{error}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Viaje">
          <Select value={tripId} onChange={(e) => setTripId(e.target.value)} disabled={editing} required>
            {!trips.length && <option value="">No tienes viajes</option>}
            {trips.map((t) => (
              <option key={t.tripId} value={t.tripId}>{t.origen} → {t.destino} ({t.fecha_inicio})</option>
            ))}
          </Select>
        </Field>
        <Field label="Tipo">
          <Select value={tipo} onChange={(e) => setTipo(e.target.value as ReservaTipo)} disabled={editing}>
            <option value="VUELO">Vuelo</option>
            <option value="HOTEL">Hotel</option>
            <option value="ACTIVIDAD">Actividad turística</option>
          </Select>
        </Field>
        {FIELDS[tipo].map((f) => (
          <Field key={f.key} label={f.label}>
            <Input type={f.type ?? "text"} placeholder={f.placeholder} min={f.type === "number" ? 1 : undefined}
              value={detalle[f.key] ?? ""} onChange={(e) => setDetalle({ ...detalle, [f.key]: e.target.value })} />
          </Field>
        ))}
        <Field label="Precio total (COP)">
          <Input type="number" min={0} step="any" value={precio} onChange={(e) => setPrecio(e.target.value)} />
        </Field>
        {editing && (
          <Field label="Estado" hint="Confirmada solo aplica con un proveedor real.">
            <div className="flex items-center gap-3">
              <Select value={estado} onChange={(e) => setEstado(e.target.value as ReservaEstado)}>
                {NEXT[reservation!.estado].map((s) => (
                  <option key={s} value={s}>{s === "SIMULADA" ? "Simulada" : s === "PENDIENTE" ? "Pendiente" : "Confirmada"}</option>
                ))}
              </Select>
              <ReservationStatusBadge estado={estado} />
            </div>
          </Field>
        )}
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
        <Button type="submit" loading={saving} disabled={!trips.length && !editing}>
          {editing ? "Guardar cambios" : "Registrar reserva"}
        </Button>
      </div>
    </form>
  );
}
