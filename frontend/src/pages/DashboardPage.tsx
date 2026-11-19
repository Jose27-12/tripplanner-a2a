import { EmptyState, PageHeader } from "../components/ui";

export default function DashboardPage() {
  return (
    <>
      <PageHeader title="Dashboard" subtitle="Tus próximos viajes y reservas recientes." />
      <EmptyState title="Próximamente" description="Este módulo se construye en la siguiente sesión." />
    </>
  );
}
