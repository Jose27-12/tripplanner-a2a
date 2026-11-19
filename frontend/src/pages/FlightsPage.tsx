import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Trip } from "../api/types";
import { FlightCards, type Flight } from "../components/agentCards";
import { AgentBlock, AgentBlockPending } from "../components/AgentBlock";
import { ProcessingIndicator } from "../components/ChatMessageView";
import Markdown from "../components/Markdown";
import { Alert, Button, Card, Field, Input, Modal, PageHeader, Select } from "../components/ui";
import { formatMoney, todayIso } from "../lib/format";
import { useAgentQuery } from "../lib/useAgentQuery";
import { notifyDataChanged, useData } from "../lib/useData";

export default function FlightsPage() {
  const q = useAgentQuery();
  const trips = useData(api.listTrips);
  const [form, setForm] = useState({ origen: "Bogotá", destino: "", ida: "", vuelta: "", pasajeros: "1" });
  const [booking, setBooking] = useState<Flight | null>(null);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const n = Number(form.pasajeros) || 1;
    const prompt =
      `Busca vuelos de ${form.origen} a ${form.destino} para el ${form.ida} para ${n} ` +
      `${n === 1 ? "pasajero" : "pasajeros"}` +
      (form.vuelta ? ` y vuelos de regreso de ${form.destino} a ${form.origen} para el ${form.vuelta}.` : ".") +
      " Solo muestra las opciones de vuelo, no crees viajes ni reservas.";
    q.run(prompt);
  }

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <PageHeader title="Vuelos" subtitle="Busca y compara vuelos. La búsqueda la hace el agente de vuelos a través de su MCP." />
      <Card className="mb-6">
        <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6 lg:items-end">
          <div className="lg:col-span-1"><Field label="Origen"><Input required value={form.origen} onChange={set("origen")} /></Field></div>
          <div className="lg:col-span-1"><Field label="Destino"><Input required placeholder="Cartagena" value={form.destino} onChange={set("destino")} /></Field></div>
          <Field label="Ida"><Input type="date" required min={todayIso()} value={form.ida} onChange={set("ida")} /></Field>
          <Field label="Regreso (opcional)"><Input type="date" min={form.ida || todayIso()} value={form.vuelta} onChange={set("vuelta")} /></Field>
          <Field label="Pasajeros"><Input type="number" min={1} max={9} required value={form.pasajeros} onChange={set("pasajeros")} /></Field>
          <Button type="submit" loading={q.busy}>Buscar vuelos</Button>
        </form>
      </Card>

      {q.error && <Alert>{q.error}</Alert>}
      <div className="space-y-4">
        {q.segments.map((s, i) => {
          if (s.kind === "text") return <Card key={i}><Markdown text={s.text} /></Card>;
          if (s.kind === "ui" && s.type === "flights")
            return (
              <FlightCards key={i} flights={s.data as Flight[]}
                action={(f) => <Button variant="secondary" className="w-full" onClick={() => setBooking(f)}>Reservar (simulada)</Button>} />
            );
          if (s.kind === "ui") return <AgentBlock key={i} type={s.type} data={s.data} />;
          if (s.kind === "ui-pending") return <AgentBlockPending key={i} type={s.type} />;
          return null;
        })}
        {q.busy && <ProcessingIndicator tool={q.tool} />}
      </div>

      <Modal title="Reservar vuelo (simulada)" open={!!booking} onClose={() => setBooking(null)}>
        {booking && <BookFlight flight={booking} trips={trips.data ?? []} onDone={() => setBooking(null)} />}
      </Modal>
    </>
  );
}

function BookFlight({ flight, trips, onDone }: { flight: Flight; trips: Trip[]; onDone: () => void }) {
  const [tripId, setTripId] = useState(trips[0]?.tripId ?? "");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [saving, setSaving] = useState(false);

  async function book() {
    setSaving(true);
    setError("");
    try {
      await api.createReservation({
        tripId,
        tipo: "VUELO",
        detalle: {
          aerolinea: flight.aerolinea, vuelo: flight.vuelo, fecha: flight.fecha,
          origen: flight.origen, destino: flight.destino, salida: flight.salida, llegada: flight.llegada,
          pasajeros: flight.pasajeros ?? 1, precio_cop: flight.precio_total_cop ?? flight.precio_cop, moneda: "COP",
          fuente: flight.fuente ?? "simulado",
        },
      });
      notifyDataChanged();
      setDone(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo registrar la reserva.");
    } finally {
      setSaving(false);
    }
  }

  if (done) {
    return (
      <div className="space-y-4">
        <Alert kind="success">Reserva registrada como <b>Simulada</b>. La encontrarás en Reservas y en el detalle del viaje.</Alert>
        <div className="flex justify-end"><Button onClick={onDone}>Listo</Button></div>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        {flight.aerolinea} {flight.vuelo} · {flight.salida} → {flight.llegada} ·{" "}
        <b>{formatMoney(flight.precio_total_cop ?? flight.precio_cop, "COP")}</b>
      </p>
      {trips.length ? (
        <Field label="Asociar al viaje">
          <Select value={tripId} onChange={(e) => setTripId(e.target.value)}>
            {trips.map((t) => <option key={t.tripId} value={t.tripId}>{t.origen} → {t.destino} ({t.fecha_inicio})</option>)}
          </Select>
        </Field>
      ) : (
        <Alert kind="info">Primero crea un viaje en “Mis viajes” para asociarle la reserva.</Alert>
      )}
      <Alert kind="info">Es una reserva simulada: no se procesan pagos ni se piden datos de tarjeta.</Alert>
      {error && <Alert>{error}</Alert>}
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onDone}>Cancelar</Button>
        <Button onClick={book} loading={saving} disabled={!tripId}>Registrar reserva</Button>
      </div>
    </div>
  );
}
