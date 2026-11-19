// Componentes de dominio. Se usan en las pantallas (canal 1) y para renderizar
// los bloques <ui type="..."> que devuelven los agentes (canal 2).
import { Link } from "react-router-dom";
import type { Itinerary, ItineraryDay, Reservation, ReservaEstado, Trip } from "../api/types";
import { daysBetween, formatDate, formatDateRange, formatMoney } from "../lib/format";
import { IconCalendar, IconPlane, IconTicket, IconUsers, IconWallet } from "./icons";
import { cx } from "./ui";

// ── Estados ──────────────────────────────────────────────────────────────────

const RES_ESTADO: Record<ReservaEstado, { label: string; className: string; help: string }> = {
  SIMULADA: {
    label: "Simulada",
    className: "bg-amber-100 text-amber-800 ring-amber-200",
    help: "Registrada por el sistema sin proveedor externo. No genera cargos.",
  },
  PENDIENTE: {
    label: "Pendiente",
    className: "bg-sky-100 text-sky-800 ring-sky-200",
    help: "Registrada y a la espera de confirmación.",
  },
  CONFIRMADA: {
    label: "Confirmada",
    className: "bg-emerald-100 text-emerald-800 ring-emerald-200",
    help: "Confirmada por un proveedor real.",
  },
};

export function ReservationStatusBadge({ estado }: { estado: ReservaEstado }) {
  const s = RES_ESTADO[estado] ?? RES_ESTADO.SIMULADA;
  return (
    <span title={s.help} className={cx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1", s.className)}>
      {s.label}
    </span>
  );
}

const TRIP_ESTADO: Record<Trip["estado"], { label: string; className: string }> = {
  PLANIFICANDO: { label: "Planificando", className: "bg-slate-100 text-slate-700" },
  CONFIRMADO: { label: "Confirmado", className: "bg-emerald-100 text-emerald-800" },
  CANCELADO: { label: "Cancelado", className: "bg-rose-100 text-rose-700" },
};

export function TripStatusBadge({ estado }: { estado: Trip["estado"] }) {
  const s = TRIP_ESTADO[estado] ?? TRIP_ESTADO.PLANIFICANDO;
  return <span className={cx("rounded-full px-2.5 py-0.5 text-xs font-medium", s.className)}>{s.label}</span>;
}

// ── Viajes ───────────────────────────────────────────────────────────────────

export function TripCard({ trip, linkTo = true }: { trip: Trip; linkTo?: boolean }) {
  const body = (
    <div className="group h-full rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-500/50 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-slate-400">{trip.origen} →</p>
          <h3 className="truncate text-lg font-semibold text-slate-900 group-hover:text-brand-700">{trip.destino}</h3>
        </div>
        <TripStatusBadge estado={trip.estado} />
      </div>
      <dl className="mt-4 space-y-2 text-sm text-slate-600">
        <div className="flex items-center gap-2">
          <IconCalendar className="h-4 w-4 text-slate-400" />
          <span>{formatDateRange(trip.fecha_inicio, trip.fecha_fin)}</span>
          <span className="text-slate-400">· {daysBetween(trip.fecha_inicio, trip.fecha_fin)} días</span>
        </div>
        <div className="flex items-center gap-2">
          <IconUsers className="h-4 w-4 text-slate-400" />
          <span>{trip.viajeros} {trip.viajeros === 1 ? "viajero" : "viajeros"}</span>
        </div>
        <div className="flex items-center gap-2">
          <IconWallet className="h-4 w-4 text-slate-400" />
          <span>{trip.presupuesto ? formatMoney(trip.presupuesto, trip.moneda) : "Sin presupuesto"}</span>
        </div>
      </dl>
    </div>
  );
  return linkTo && trip.tripId ? <Link to={`/viajes/${trip.tripId}`}>{body}</Link> : body;
}

// ── Itinerario ───────────────────────────────────────────────────────────────

export function ItineraryAgenda({ itinerary }: { itinerary: Pick<Itinerary, "dias"> }) {
  const dias: ItineraryDay[] = [...(itinerary.dias ?? [])].sort((a, b) => a.dia - b.dia);
  if (!dias.length) return <p className="text-sm text-slate-500">El itinerario no tiene días.</p>;
  return (
    <ol className="relative space-y-4 border-l-2 border-brand-100 pl-6">
      {dias.map((d) => (
        <li key={d.dia} className="relative">
          <span className="absolute -left-[33px] flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">
            {d.dia}
          </span>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold text-slate-800">
              Día {d.dia}
              {d.fecha && <span className="ml-2 font-normal capitalize text-slate-500">{formatDate(d.fecha, { weekday: "long", day: "numeric", month: "long" })}</span>}
            </p>
            {d.actividades?.length ? (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                {d.actividades.map((a, i) => <li key={i}>{String(a)}</li>)}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-slate-400">Día libre</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

// ── Reservas ─────────────────────────────────────────────────────────────────

const TIPO_LABEL: Record<Reservation["tipo"], string> = { VUELO: "Vuelo", HOTEL: "Hotel", ACTIVIDAD: "Actividad" };

export function reservationTitle(r: Pick<Reservation, "tipo" | "detalle">): string {
  const d = r.detalle ?? {};
  const pick = (...keys: string[]) => keys.map((k) => d[k]).find((v) => typeof v === "string" && v) as string | undefined;
  if (r.tipo === "VUELO") return [pick("aerolinea"), pick("vuelo")].filter(Boolean).join(" ") || "Vuelo";
  if (r.tipo === "HOTEL") return pick("hotel", "nombre") || "Hotel";
  return pick("actividad", "nombre", "descripcion") || "Actividad";
}

function reservationPrice(d: Record<string, unknown>): string | null {
  const cop = Number(d.precio_total_cop ?? d.precio_cop ?? d.precio);
  if (Number.isFinite(cop) && cop > 0) return formatMoney(cop, String(d.moneda ?? "COP"));
  const usd = Number(d.precio_usd);
  if (Number.isFinite(usd) && usd > 0) return formatMoney(usd, "USD");
  return null;
}

export function ReservationRow({ r, tripLabel, onEdit }: { r: Reservation; tripLabel?: string; onEdit?: () => void }) {
  const d = r.detalle ?? {};
  const fecha = (d.fecha ?? d.check_in) as string | undefined;
  const price = reservationPrice(d);
  return (
    <li className="flex flex-wrap items-center gap-4 px-4 py-3">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
        {r.tipo === "VUELO" ? <IconPlane className="h-5 w-5" /> : <IconTicket className="h-5 w-5" />}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-slate-800">{reservationTitle(r)}</p>
        <p className="truncate text-xs text-slate-500">
          {TIPO_LABEL[r.tipo]}
          {fecha && ` · ${formatDate(fecha)}`}
          {tripLabel && ` · ${tripLabel}`}
        </p>
      </div>
      {price && <span className="text-sm font-medium text-slate-700">{price}</span>}
      <ReservationStatusBadge estado={r.estado} />
      {onEdit && (
        <button onClick={onEdit} className="text-sm font-medium text-brand-700 hover:text-brand-600">Editar</button>
      )}
    </li>
  );
}

export function ReservationList({
  reservations, tripLabels, onEdit,
}: { reservations: Reservation[]; tripLabels?: Record<string, string>; onEdit?: (r: Reservation) => void }) {
  return (
    <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
      {reservations.map((r) => (
        <ReservationRow key={r.resId} r={r} tripLabel={tripLabels?.[r.tripId]} onEdit={onEdit ? () => onEdit(r) : undefined} />
      ))}
    </ul>
  );
}
