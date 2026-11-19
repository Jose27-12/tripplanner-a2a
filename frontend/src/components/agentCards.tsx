// Componentes dirigidos por agentes: vuelos (FlightCards) y clima (WeatherCards).
import { useMemo, useState, type ReactNode } from "react";
import { formatDate, formatDuration, formatMoney } from "../lib/format";
import { IconPlane } from "./icons";
import { cx } from "./ui";

// ── Vuelos ───────────────────────────────────────────────────────────────────

export interface Flight {
  aerolinea: string;
  codigo_aerolinea?: string;
  vuelo: string;
  origen?: string;
  origen_iata?: string;
  destino?: string;
  destino_iata?: string;
  fecha?: string;
  salida: string;
  llegada: string;
  duracion_min?: number;
  escalas?: number;
  escala_en?: string | null;
  clase?: string;
  precio_usd?: number;
  precio_cop?: number;
  precio_total_cop?: number;
  pasajeros?: number;
  asientos_disponibles?: number;
  equipaje?: string;
  fuente?: string;
}

type SortKey = "precio" | "salida" | "duracion";

const priceOf = (f: Flight) => f.precio_cop ?? (f.precio_usd ? f.precio_usd * 4000 : Number.POSITIVE_INFINITY);

export function FlightCards({ flights, action }: { flights: Flight[]; action?: (f: Flight) => ReactNode }) {
  const [sort, setSort] = useState<SortKey>("precio");
  const list = useMemo(() => {
    const copy = [...flights];
    if (sort === "precio") copy.sort((a, b) => priceOf(a) - priceOf(b));
    if (sort === "salida") copy.sort((a, b) => a.salida.localeCompare(b.salida));
    if (sort === "duracion") copy.sort((a, b) => (a.duracion_min ?? 0) - (b.duracion_min ?? 0));
    return copy;
  }, [flights, sort]);
  const cheapest = Math.min(...flights.map(priceOf));
  const fastest = Math.min(...flights.map((f) => f.duracion_min ?? Number.POSITIVE_INFINITY));
  if (!flights.length) return <p className="text-sm text-slate-500">No hay vuelos para mostrar.</p>;
  const first = flights[0];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-slate-700">
          {first.origen ?? first.origen_iata} → {first.destino ?? first.destino_iata}
          {first.fecha && <span className="font-normal text-slate-500"> · {formatDate(first.fecha, { weekday: "short", day: "numeric", month: "short" })}</span>}
          {first.pasajeros && first.pasajeros > 1 && <span className="font-normal text-slate-500"> · {first.pasajeros} pasajeros</span>}
        </p>
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 text-xs">
          {(["precio", "salida", "duracion"] as SortKey[]).map((k) => (
            <button key={k} onClick={() => setSort(k)}
              className={cx("rounded-md px-2.5 py-1", sort === k ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-100")}>
              {k === "precio" ? "Más barato" : k === "salida" ? "Hora" : "Más rápido"}
            </button>
          ))}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {list.map((f) => {
          const isCheapest = priceOf(f) === cheapest;
          const isFastest = f.duracion_min === fastest;
          return (
            <div key={`${f.vuelo}-${f.salida}`}
              className={cx("relative rounded-xl border bg-white p-4 shadow-sm", isCheapest ? "border-emerald-400 ring-1 ring-emerald-200" : "border-slate-200")}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-50 text-sky-700"><IconPlane className="h-5 w-5" /></span>
                  <div>
                    <p className="font-semibold text-slate-900">{f.aerolinea}</p>
                    <p className="text-xs text-slate-500">{f.vuelo}{f.clase ? ` · ${f.clase.toLowerCase()}` : ""}</p>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {isCheapest && <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">Más barato</span>}
                  {isFastest && !isCheapest && <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[11px] font-semibold text-sky-700">Más rápido</span>}
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <div>
                  <p className="text-xl font-semibold text-slate-900">{f.salida}</p>
                  <p className="text-xs text-slate-500">{f.origen_iata ?? f.origen}</p>
                </div>
                <div className="flex-1 px-3 text-center text-xs text-slate-500">
                  <p>{formatDuration(f.duracion_min)}</p>
                  <div className="my-1 h-px bg-slate-300" />
                  <p>{f.escalas ? `${f.escalas} escala${f.escala_en ? ` en ${f.escala_en}` : ""}` : "Directo"}</p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-semibold text-slate-900">{f.llegada}</p>
                  <p className="text-xs text-slate-500">{f.destino_iata ?? f.destino}</p>
                </div>
              </div>
              <div className="mt-4 flex items-end justify-between border-t border-slate-100 pt-3">
                <div className="text-xs text-slate-500">
                  {f.equipaje && <p>{f.equipaje}</p>}
                  {f.asientos_disponibles !== undefined && <p>{f.asientos_disponibles} asientos disponibles</p>}
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold text-slate-900">
                    {f.precio_cop ? formatMoney(f.precio_cop, "COP") : formatMoney(f.precio_usd, "USD")}
                  </p>
                  <p className="text-xs text-slate-500">
                    por persona{f.precio_total_cop && f.pasajeros && f.pasajeros > 1 ? ` · total ${formatMoney(f.precio_total_cop, "COP")}` : ""}
                  </p>
                </div>
              </div>
              {action && <div className="mt-3">{action(f)}</div>}
            </div>
          );
        })}
      </div>
      {flights.some((f) => f.fuente === "simulado") && (
        <p className="text-xs text-slate-400">Tarifas de un proveedor de vuelos simulado (MCP de vuelos). No se realizan cobros.</p>
      )}
    </div>
  );
}

// ── Clima ────────────────────────────────────────────────────────────────────

export interface WeatherDay {
  fecha: string;
  ciudad?: string;
  temp_max_c: number | null;
  temp_min_c: number | null;
  condicion: string;
  lluvia_prob_pct?: number | null;
  humedad_pct?: number | null;
  icono?: string;
  tipo?: "pronostico" | "estimado_historico";
}

const WEATHER_ICON: Record<string, string> = {
  sunny: "☀️", partly_cloudy: "⛅", cloudy: "☁️", rainy: "🌧️", storm: "⛈️", snow: "❄️", fog: "🌫️",
};

export function WeatherCards({ days }: { days: WeatherDay[] }) {
  if (!days.length) return <p className="text-sm text-slate-500">No hay datos del clima.</p>;
  const ciudad = days.find((d) => d.ciudad)?.ciudad;
  const historic = days.some((d) => d.tipo === "estimado_historico");
  return (
    <div className="space-y-2">
      {ciudad && <p className="text-sm font-medium text-slate-700">Clima en {ciudad}</p>}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {days.map((d) => {
          const rain = d.lluvia_prob_pct ?? null;
          return (
            <div key={d.fecha} className="rounded-xl border border-slate-200 bg-gradient-to-b from-sky-50 to-white p-4 text-center shadow-sm">
              <p className="text-xs font-medium capitalize text-slate-500">{formatDate(d.fecha, { weekday: "short", day: "numeric", month: "short" })}</p>
              <p className="my-2 text-3xl" aria-hidden="true">{WEATHER_ICON[d.icono ?? ""] ?? "🌤️"}</p>
              <p className="text-sm font-medium text-slate-700">{d.condicion}</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">
                {d.temp_max_c ?? "—"}° <span className="text-sm font-normal text-slate-500">/ {d.temp_min_c ?? "—"}°</span>
              </p>
              {rain !== null && (
                <div className="mt-2">
                  <div className="h-1.5 rounded-full bg-slate-200">
                    <div className="h-1.5 rounded-full bg-sky-500" style={{ width: `${Math.min(100, Math.max(0, rain))}%` }} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">💧 {rain}% lluvia{d.humedad_pct ? ` · ${d.humedad_pct}% hum.` : ""}</p>
                </div>
              )}
              {d.tipo === "estimado_historico" && <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-400">Estimado</p>}
            </div>
          );
        })}
      </div>
      <p className="text-xs text-slate-400">
        Datos de Open-Meteo (MCP de clima).{historic ? " Los días marcados como “Estimado” superan los 16 días de pronóstico y se calculan con datos históricos." : ""}
      </p>
    </div>
  );
}
