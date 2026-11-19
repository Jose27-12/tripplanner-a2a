import { useMemo } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ReservationList, TripCard } from "../components/domain";
import { IconChat, IconMap, IconPlane, IconSun, IconTicket } from "../components/icons";
import { Alert, Card, EmptyState, LoadingBlock, PageHeader } from "../components/ui";
import { daysBetween, formatDate, parseDate, todayIso } from "../lib/format";
import { useData } from "../lib/useData";

const QUICK = [
  { to: "/asistente", label: "Planear con el asistente", icon: IconChat, color: "bg-brand-600 text-white" },
  { to: "/vuelos", label: "Buscar vuelos", icon: IconPlane, color: "bg-sky-100 text-sky-700" },
  { to: "/clima", label: "Ver el clima", icon: IconSun, color: "bg-amber-100 text-amber-700" },
  { to: "/viajes", label: "Mis viajes", icon: IconMap, color: "bg-violet-100 text-violet-700" },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const trips = useData(api.listTrips);
  const reservations = useData(() => api.listReservations());

  const upcoming = useMemo(() => {
    const today = todayIso();
    return (trips.data ?? [])
      .filter((t) => t.fecha_fin >= today && t.estado !== "CANCELADO")
      .sort((a, b) => a.fecha_inicio.localeCompare(b.fecha_inicio));
  }, [trips.data]);

  const recent = useMemo(
    () => [...(reservations.data ?? [])].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 5),
    [reservations.data],
  );

  const tripLabels = useMemo(
    () => Object.fromEntries((trips.data ?? []).map((t) => [t.tripId, `${t.origen} → ${t.destino}`])),
    [trips.data],
  );

  const next = upcoming[0];
  const daysToNext = next ? Math.ceil((parseDate(next.fecha_inicio).getTime() - parseDate(todayIso()).getTime()) / 86_400_000) : null;

  return (
    <>
      <PageHeader title={`Hola${user?.name ? `, ${user.name.split(" ")[0]}` : ""} 👋`} subtitle="Este es el resumen de tus viajes." />
      {(trips.error || reservations.error) && <Alert>{trips.error || reservations.error}</Alert>}

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {QUICK.map(({ to, label, icon: Icon, color }) => (
          <Link key={to} to={to} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md">
            <span className={`flex h-10 w-10 items-center justify-center rounded-lg ${color}`}><Icon className="h-5 w-5" /></span>
            <span className="text-sm font-medium text-slate-800">{label}</span>
          </Link>
        ))}
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-sm text-slate-500">Próximo viaje</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">{next ? next.destino : "—"}</p>
          <p className="text-sm text-slate-500">
            {next ? (daysToNext! <= 0 ? "¡En curso!" : `en ${daysToNext} días · ${formatDate(next.fecha_inicio)}`) : "Sin viajes próximos"}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">Viajes planificados</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">{upcoming.length}</p>
          <p className="text-sm text-slate-500">
            {upcoming.reduce((n, t) => n + daysBetween(t.fecha_inicio, t.fecha_fin), 0)} días de viaje por delante
          </p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">Reservas</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">{reservations.data?.length ?? 0}</p>
          <p className="text-sm text-slate-500">
            {(reservations.data ?? []).filter((r) => r.estado === "SIMULADA").length} simuladas ·{" "}
            {(reservations.data ?? []).filter((r) => r.estado === "PENDIENTE").length} pendientes
          </p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="lg:col-span-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Próximos viajes</h2>
            <Link to="/viajes" className="text-sm font-medium text-brand-700">Ver todos</Link>
          </div>
          {trips.loading && !trips.data ? (
            <LoadingBlock />
          ) : upcoming.length ? (
            <div className="grid gap-4 sm:grid-cols-2">{upcoming.slice(0, 4).map((t) => <TripCard key={t.tripId} trip={t} />)}</div>
          ) : (
            <EmptyState title="Aún no tienes viajes" description="Pídele al asistente que te ayude a planear tus próximas vacaciones."
              action={<Link to="/asistente" className="text-sm font-medium text-brand-700">Abrir el asistente</Link>} />
          )}
        </section>
        <section className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Reservas recientes</h2>
            <Link to="/reservas" className="text-sm font-medium text-brand-700">Ver todas</Link>
          </div>
          {reservations.loading && !reservations.data ? (
            <LoadingBlock />
          ) : recent.length ? (
            <ReservationList reservations={recent} tripLabels={tripLabels} />
          ) : (
            <EmptyState title="Sin reservas todavía" description="Las reservas que registres aparecerán aquí."
              action={<Link to="/reservas" className="inline-flex items-center gap-1 text-sm font-medium text-brand-700"><IconTicket className="h-4 w-4" /> Ir a reservas</Link>} />
          )}
        </section>
      </div>
    </>
  );
}
