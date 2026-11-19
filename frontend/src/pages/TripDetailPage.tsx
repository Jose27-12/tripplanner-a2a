import { EmptyState, PageHeader } from "../components/ui";

export default function TripDetailPage() {
  return (
    <>
      <PageHeader title="Detalle del viaje" subtitle="Itinerario y reservas del viaje." />
      <EmptyState title="Próximamente" description="Este módulo se construye en la siguiente sesión." />
    </>
  );
}
