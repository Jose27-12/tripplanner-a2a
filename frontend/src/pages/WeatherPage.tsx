import { EmptyState, PageHeader } from "../components/ui";

export default function WeatherPage() {
  return (
    <>
      <PageHeader title="Clima" subtitle="Pronóstico por destino y fechas." />
      <EmptyState title="Próximamente" description="Este módulo se construye en la siguiente sesión." />
    </>
  );
}
