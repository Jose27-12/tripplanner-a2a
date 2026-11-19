import { EmptyState, PageHeader } from "../components/ui";

export default function ReservationsPage() {
  return (
    <>
      <PageHeader title="Reservas" subtitle="Gestiona tus reservas simuladas." />
      <EmptyState title="Próximamente" description="Este módulo se construye en la siguiente sesión." />
    </>
  );
}
