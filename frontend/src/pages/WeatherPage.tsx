import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import { AgentBlock, AgentBlockPending } from "../components/AgentBlock";
import { ProcessingIndicator } from "../components/ChatMessageView";
import Markdown from "../components/Markdown";
import { Alert, Button, Card, Field, Input, PageHeader, Select } from "../components/ui";
import { addDays, todayIso } from "../lib/format";
import { useAgentQuery } from "../lib/useAgentQuery";
import { useData } from "../lib/useData";

export default function WeatherPage() {
  const q = useAgentQuery();
  const trips = useData(api.listTrips);
  const [form, setForm] = useState({ ciudad: "", desde: todayIso(), hasta: addDays(todayIso(), 3) });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  function ask(ciudad: string, desde: string, hasta: string) {
    q.run(`¿Cómo estará el clima en ${ciudad} del ${desde} al ${hasta}? Muestra el pronóstico por día.`);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    ask(form.ciudad, form.desde, form.hasta);
  }

  const upcoming = (trips.data ?? []).filter((t) => t.fecha_fin >= todayIso() && t.estado !== "CANCELADO");

  return (
    <>
      <PageHeader title="Clima" subtitle="Temperatura, condiciones y probabilidad de lluvia por destino y fechas (agente meteorológico + MCP de clima)." />
      <Card className="mb-6">
        <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-4 sm:items-end">
          <Field label="Destino"><Input required placeholder="Cartagena" value={form.ciudad} onChange={set("ciudad")} /></Field>
          <Field label="Desde"><Input type="date" required min={todayIso()} value={form.desde} onChange={set("desde")} /></Field>
          <Field label="Hasta"><Input type="date" required min={form.desde} max={addDays(form.desde, 30)} value={form.hasta} onChange={set("hasta")} /></Field>
          <Button type="submit" loading={q.busy}>Consultar clima</Button>
        </form>
        {upcoming.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
            <span className="text-xs text-slate-500">Tus próximos viajes:</span>
            <Select className="w-auto" value="" aria-label="Consultar el clima de un viaje"
              onChange={(e) => {
                const t = upcoming.find((x) => x.tripId === e.target.value);
                if (t) { setForm({ ciudad: t.destino, desde: t.fecha_inicio, hasta: t.fecha_fin }); ask(t.destino, t.fecha_inicio, t.fecha_fin); }
              }}>
              <option value="">Elegir viaje…</option>
              {upcoming.map((t) => <option key={t.tripId} value={t.tripId}>{t.destino} ({t.fecha_inicio})</option>)}
            </Select>
          </div>
        )}
      </Card>

      {q.error && <Alert>{q.error}</Alert>}
      <div className="space-y-4">
        {q.segments.map((s, i) => {
          if (s.kind === "text") return <Card key={i}><Markdown text={s.text} /></Card>;
          if (s.kind === "ui") return <AgentBlock key={i} type={s.type} data={s.data} />;
          if (s.kind === "ui-pending") return <AgentBlockPending key={i} type={s.type} />;
          return null;
        })}
        {q.busy && <ProcessingIndicator tool={q.tool} />}
      </div>
    </>
  );
}
