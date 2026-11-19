import { EmptyState, PageHeader } from "../components/ui";

export default function AssistantPage() {
  return (
    <>
      <PageHeader title="Asistente" subtitle="Conversa con TripPlanner AI." />
      <EmptyState title="Próximamente" description="Este módulo se construye en la siguiente sesión." />
    </>
  );
}
