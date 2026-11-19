import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Reservation } from "../api/types";
import { ItineraryAgenda, ReservationList, TripCard } from "../components/domain";
import { IconPlus } from "../components/icons";
import ItineraryEditor from "../components/ItineraryEditor";
import ReservationForm from "../components/ReservationForm";
import TripForm from "../components/TripForm";
import { Alert, Button, Card, EmptyState, LoadingBlock, Modal, PageHeader } from "../components/ui";
import { useData } from "../lib/useData";

export default function TripDetailPage() {
  const { tripId = "" } = useParams();
  const trip = useData(() => api.getTrip(tripId), [tripId]);
  const itinerary = useData(() => api.getItinerary(tripId), [tripId]);
  const reservations = useData(() => api.listReservations(tripId), [tripId]);

  const [editingTrip, setEditingTrip] = useState(false);
  const [editingItinerary, setEditingItinerary] = useState(false);
  const [resModal, setResModal] = useState<{ open: boolean; reservation?: Reservation }>({ open: false });

  if (trip.loading && !trip.data) return <LoadingBlock label="Cargando viaje..." />;
  if (trip.error || !trip.data) {
    return (
      <EmptyState title="No encontramos este viaje" description={trip.error}
        action={<Link to="/viajes" className="text-sm font-medium text-brand-700">Volver a mis viajes</Link>} />
    );
  }
  const t = trip.data;

  return (
    <>
      <PageHeader
        title={`${t.origen} → ${t.destino}`}
        subtitle="Detalle del viaje, itinerario y reservas asociadas."
        actions={
          <>
            <Link to="/viajes"><Button variant="ghost">Volver</Button></Link>
            <Button variant="secondary" onClick={() => setEditingTrip(true)}>Editar viaje</Button>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-1">
          <TripCard trip={t} linkTo={false} />
          <Card>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Reservas</h2>
              <Button variant="ghost" className="px-2 py-1" onClick={() => setResModal({ open: true })}>
                <IconPlus className="h-4 w-4" /> Agregar
              </Button>
            </div>
            {reservations.error && <Alert>{reservations.error}</Alert>}
            {reservations.loading && !reservations.data ? (
              <LoadingBlock />
            ) : reservations.data?.length ? (
              <ReservationList reservations={reservations.data} onEdit={(r) => setResModal({ open: true, reservation: r })} />
            ) : (
              <p className="text-sm text-slate-500">Aún no hay reservas para este viaje.</p>
            )}
          </Card>
        </div>

        <Card className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Itinerario</h2>
            {!editingItinerary && (
              <Button variant="secondary" onClick={() => setEditingItinerary(true)}>
                {itinerary.data ? "Editar itinerario" : "Crear itinerario"}
              </Button>
            )}
          </div>
          {itinerary.error && <Alert>{itinerary.error}</Alert>}
          {editingItinerary ? (
            <ItineraryEditor
              trip={t}
              itinerary={itinerary.data ?? null}
              onCancel={() => setEditingItinerary(false)}
              onSaved={(it) => { itinerary.setData(it); setEditingItinerary(false); }}
            />
          ) : itinerary.loading && itinerary.data === undefined ? (
            <LoadingBlock />
          ) : itinerary.data ? (
            <ItineraryAgenda itinerary={itinerary.data} />
          ) : (
            <EmptyState title="Este viaje aún no tiene itinerario"
              description="Créalo aquí o pídele al asistente que te proponga actividades para cada día." />
          )}
        </Card>
      </div>

      <Modal title="Editar viaje" open={editingTrip} onClose={() => setEditingTrip(false)}>
        <TripForm trip={t} onCancel={() => setEditingTrip(false)} onSaved={(nt) => { trip.setData(nt); setEditingTrip(false); }} />
      </Modal>

      <Modal title={resModal.reservation ? "Editar reserva" : "Nueva reserva"} open={resModal.open} onClose={() => setResModal({ open: false })}>
        <ReservationForm
          trips={[t]}
          reservation={resModal.reservation}
          defaultTripId={t.tripId}
          onCancel={() => setResModal({ open: false })}
          onSaved={() => { setResModal({ open: false }); reservations.reload(); }}
        />
      </Modal>
    </>
  );
}
