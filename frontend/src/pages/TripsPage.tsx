import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { TripCard } from "../components/domain";
import { IconPlus } from "../components/icons";
import TripForm from "../components/TripForm";
import { Alert, Button, EmptyState, LoadingBlock, Modal, PageHeader, cx } from "../components/ui";
import { todayIso } from "../lib/format";
import { useData } from "../lib/useData";

type Filter = "proximos" | "pasados" | "todos";

export default function TripsPage() {
  const navigate = useNavigate();
  const { data: trips, error, loading } = useData(api.listTrips);
  const [creating, setCreating] = useState(false);
  const [filter, setFilter] = useState<Filter>("proximos");

  const visible = useMemo(() => {
    const today = todayIso();
    const list = [...(trips ?? [])].sort((a, b) => a.fecha_inicio.localeCompare(b.fecha_inicio));
    if (filter === "proximos") return list.filter((t) => t.fecha_fin >= today && t.estado !== "CANCELADO");
    if (filter === "pasados") return list.filter((t) => t.fecha_fin < today || t.estado === "CANCELADO").reverse();
    return list;
  }, [trips, filter]);

  return (
    <>
      <PageHeader
        title="Mis viajes"
        subtitle="Tus viajes guardados, con su itinerario y reservas."
        actions={<Button onClick={() => setCreating(true)}><IconPlus className="h-4 w-4" /> Nuevo viaje</Button>}
      />

      <div className="mb-5 inline-flex rounded-lg border border-slate-200 bg-white p-1 text-sm">
        {(["proximos", "pasados", "todos"] as Filter[]).map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={cx("rounded-md px-3 py-1.5 capitalize", filter === f ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100")}>
            {f === "proximos" ? "Próximos" : f === "pasados" ? "Pasados" : "Todos"}
          </button>
        ))}
      </div>

      {error && <Alert>{error}</Alert>}
      {loading && !trips ? (
        <LoadingBlock label="Cargando viajes..." />
      ) : visible.length === 0 ? (
        <EmptyState
          title={filter === "proximos" ? "No tienes viajes próximos" : "No hay viajes en esta vista"}
          description="Crea un viaje aquí o pídeselo al asistente: “Quiero 4 días en Cartagena desde Bogotá”."
          action={<Button onClick={() => setCreating(true)}>Crear mi primer viaje</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((t) => <TripCard key={t.tripId} trip={t} />)}
        </div>
      )}

      <Modal title="Nuevo viaje" open={creating} onClose={() => setCreating(false)}>
        <TripForm onCancel={() => setCreating(false)} onSaved={(t) => navigate(`/viajes/${t.tripId}`)} />
      </Modal>
    </>
  );
}
