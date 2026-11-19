import { EmptyState, PageHeader } from "../components/ui";

export default function TripsPage() {
  return (
    <>
      <PageHeader title="Mis viajes" subtitle="Tus viajes guardados." />
      <EmptyState title="Próximamente" description="Este módulo se construye en la siguiente sesión." />
    </>
  );
}
