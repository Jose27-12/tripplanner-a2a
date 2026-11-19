import { EmptyState, PageHeader } from "../components/ui";

export default function PreferencesPage() {
  return (
    <>
      <PageHeader title="Preferencias" subtitle="Personaliza tus recomendaciones." />
      <EmptyState title="Próximamente" description="Este módulo se construye en la siguiente sesión." />
    </>
  );
}
