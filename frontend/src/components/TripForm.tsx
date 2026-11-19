import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Moneda, Trip, TripEstado, TripInput } from "../api/types";
import { todayIso } from "../lib/format";
import { Alert, Button, Field, Input, Select } from "./ui";

/** Crear o editar un viaje (validación en cliente + validación definitiva en Lambda). */
export default function TripForm({ trip, onSaved, onCancel }: { trip?: Trip; onSaved: (t: Trip) => void; onCancel: () => void }) {
  const [form, setForm] = useState({
    origen: trip?.origen ?? "",
    destino: trip?.destino ?? "",
    fecha_inicio: trip?.fecha_inicio ?? "",
    fecha_fin: trip?.fecha_fin ?? "",
    viajeros: String(trip?.viajeros ?? 1),
    presupuesto: trip?.presupuesto ? String(trip.presupuesto) : "",
    moneda: (trip?.moneda ?? "COP") as Moneda,
    estado: (trip?.estado ?? "PLANIFICANDO") as TripEstado,
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  function validate(): string | null {
    if (!form.origen.trim() || !form.destino.trim()) return "Indica origen y destino.";
    if (!form.fecha_inicio || !form.fecha_fin) return "Indica las fechas del viaje.";
    if (form.fecha_fin < form.fecha_inicio) return "La fecha de regreso debe ser igual o posterior a la de salida.";
    const v = Number(form.viajeros);
    if (!Number.isInteger(v) || v < 1 || v > 50) return "El número de viajeros debe estar entre 1 y 50.";
    if (form.presupuesto && !(Number(form.presupuesto) > 0)) return "El presupuesto debe ser un número positivo.";
    return null;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const err = validate();
    if (err) return setError(err);
    setError("");
    setSaving(true);
    const input: TripInput = {
      origen: form.origen.trim(),
      destino: form.destino.trim(),
      fecha_inicio: form.fecha_inicio,
      fecha_fin: form.fecha_fin,
      viajeros: Number(form.viajeros),
      moneda: form.moneda,
      ...(form.presupuesto ? { presupuesto: Number(form.presupuesto) } : {}),
      ...(trip ? { estado: form.estado } : {}),
    };
    try {
      onSaved(trip ? await api.updateTrip(trip.tripId, input) : await api.createTrip(input));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar el viaje.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {error && <Alert>{error}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Origen"><Input required placeholder="Bogotá" value={form.origen} onChange={set("origen")} /></Field>
        <Field label="Destino"><Input required placeholder="Cartagena" value={form.destino} onChange={set("destino")} /></Field>
        <Field label="Salida"><Input type="date" required min={trip ? undefined : todayIso()} value={form.fecha_inicio} onChange={set("fecha_inicio")} /></Field>
        <Field label="Regreso"><Input type="date" required min={form.fecha_inicio || undefined} value={form.fecha_fin} onChange={set("fecha_fin")} /></Field>
        <Field label="Viajeros"><Input type="number" min={1} max={50} required value={form.viajeros} onChange={set("viajeros")} /></Field>
        <div className="grid grid-cols-[1fr_auto] gap-2">
          <Field label="Presupuesto"><Input type="number" min={0} step="any" placeholder="5000000" value={form.presupuesto} onChange={set("presupuesto")} /></Field>
          <Field label="Moneda">
            <Select value={form.moneda} onChange={set("moneda")}>
              <option value="COP">COP</option>
              <option value="USD">USD</option>
            </Select>
          </Field>
        </div>
        {trip && (
          <Field label="Estado">
            <Select value={form.estado} onChange={set("estado")}>
              <option value="PLANIFICANDO">Planificando</option>
              <option value="CONFIRMADO">Confirmado</option>
              <option value="CANCELADO">Cancelado</option>
            </Select>
          </Field>
        )}
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
        <Button type="submit" loading={saving}>{trip ? "Guardar cambios" : "Crear viaje"}</Button>
      </div>
    </form>
  );
}
