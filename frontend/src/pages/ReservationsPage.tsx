import { useMemo, useState } from "react";
import { api } from "../api/client";
import type { Reservation, ReservaEstado, ReservaTipo } from "../api/types";
import { ReservationList, ReservationStatusBadge } from "../components/domain";
import { IconPlus } from "../components/icons";
import ReservationForm from "../components/ReservationForm";
import { Alert, Button, EmptyState, LoadingBlock, Modal, PageHeader, Select } from "../components/ui";
import { useData } from "../lib/useData";

export default function ReservationsPage() {
  const reservations = useData(() => api.listReservations());
  const trips = useData(api.listTrips);
  const [modal, setModal] = useState<{ open: boolean; reservation?: Reservation }>({ open: false });
  const [estado, setEstado] = useState<"" | ReservaEstado>("");
  const [tipo, setTipo] = useState<"" | ReservaTipo>("");
  const [tripId, setTripId] = useState("");

  const tripLabels = useMemo(
    () => Object.fromEntries((trips.data ?? []).map((t) => [t.tripId, `${t.origen} → ${t.destino}`])),
    [trips.data],
  );

  const visible = useMemo(
    () =>
      [...(reservations.data ?? [])]
        .filter((r) => (!estado || r.estado === estado) && (!tipo || r.tipo === tipo) && (!tripId || r.tripId === tripId))
        .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
    [reservations.data, estado, tipo, tripId],
  );

  return (
    <>
      <PageHeader
        title="Reservas"
        subtitle="Vuelos, hoteles y actividades asociados a tus viajes."
        actions={<Button onClick={() => setModal({ open: true })} disabled={!trips.data?.length}><IconPlus className="h-4 w-4" /> Nueva reserva</Button>}
      />

      <div className="mb-4 flex flex-wrap items-center gap-3 text-xs text-slate-500">
        <span>Estados:</span>
        <ReservationStatusBadge estado="SIMULADA" /> <span>sin proveedor externo</span>
        <ReservationStatusBadge estado="PENDIENTE" /> <span>a la espera de confirmación</span>
        <ReservationStatusBadge estado="CONFIRMADA" /> <span>confirmada por proveedor real</span>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <Select value={tripId} onChange={(e) => setTripId(e.target.value)} aria-label="Filtrar por viaje">
          <option value="">Todos los viajes</option>
          {(trips.data ?? []).map((t) => <option key={t.tripId} value={t.tripId}>{tripLabels[t.tripId]} ({t.fecha_inicio})</option>)}
        </Select>
        <Select value={tipo} onChange={(e) => setTipo(e.target.value as ReservaTipo | "")} aria-label="Filtrar por tipo">
          <option value="">Todos los tipos</option>
          <option value="VUELO">Vuelos</option>
          <option value="HOTEL">Hoteles</option>
          <option value="ACTIVIDAD">Actividades</option>
        </Select>
        <Select value={estado} onChange={(e) => setEstado(e.target.value as ReservaEstado | "")} aria-label="Filtrar por estado">
          <option value="">Todos los estados</option>
          <option value="SIMULADA">Simulada</option>
          <option value="PENDIENTE">Pendiente</option>
          <option value="CONFIRMADA">Confirmada</option>
        </Select>
      </div>

      {(reservations.error || trips.error) && <Alert>{reservations.error || trips.error}</Alert>}
      {reservations.loading && !reservations.data ? (
        <LoadingBlock label="Cargando reservas..." />
      ) : visible.length ? (
        <ReservationList reservations={visible} tripLabels={tripLabels} onEdit={(r) => setModal({ open: true, reservation: r })} />
      ) : (
        <EmptyState
          title="No hay reservas"
          description={trips.data?.length ? "Registra una reserva simulada o pídesela al asistente." : "Primero crea un viaje para poder asociarle reservas."}
        />
      )}

      <Modal title={modal.reservation ? "Editar reserva" : "Nueva reserva"} open={modal.open} onClose={() => setModal({ open: false })}>
        <ReservationForm
          trips={trips.data ?? []}
          reservation={modal.reservation}
          onCancel={() => setModal({ open: false })}
          onSaved={() => { setModal({ open: false }); reservations.reload(); }}
        />
      </Modal>
    </>
  );
}
