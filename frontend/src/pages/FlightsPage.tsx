import { EmptyState, PageHeader } from "../components/ui";

export default function FlightsPage() {
  return (
    <>
      <PageHeader title="Vuelos" subtitle="Busca y compara vuelos." />
      <EmptyState title="Próximamente" description="Este módulo se construye en la siguiente sesión." />
    </>
  );
}
