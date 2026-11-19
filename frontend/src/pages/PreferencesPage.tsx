import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Preferences } from "../api/types";
import { Alert, Button, Card, Field, Input, LoadingBlock, PageHeader, Select, cx } from "../components/ui";
import { useData } from "../lib/useData";

const ACTIVIDADES = ["playa", "cultura", "gastronomia", "naturaleza", "aventura", "vida nocturna", "compras", "museos"];
const AEROLINEAS = ["Avianca", "LATAM", "JetSMART", "Copa Airlines"];

const splitList = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

export default function PreferencesPage() {
  const { data, error, loading } = useData(api.getPreferences);
  const [prefs, setPrefs] = useState<Preferences>({});
  const [restricciones, setRestricciones] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) {
      setPrefs(data);
      setRestricciones((data.restricciones ?? []).join(", "));
    }
  }, [data]);

  const toggle = (key: "actividades" | "aerolineas_preferidas", value: string) => {
    const list = prefs[key] ?? [];
    setPrefs({ ...prefs, [key]: list.includes(value) ? list.filter((v) => v !== value) : [...list, value] });
    setSaved(false);
  };

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError("");
    try {
      const body: Preferences = {
        actividades: prefs.actividades ?? [],
        aerolineas_preferidas: prefs.aerolineas_preferidas ?? [],
        restricciones: splitList(restricciones),
        ...(prefs.presupuesto_tipo ? { presupuesto_tipo: prefs.presupuesto_tipo } : {}),
        ...(prefs.asiento_preferido ? { asiento_preferido: prefs.asiento_preferido } : {}),
      };
      setPrefs(await api.savePreferences(body));
      setSaved(true);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "No se pudieron guardar las preferencias.");
    } finally {
      setSaving(false);
    }
  }

  if (loading && !data) return <LoadingBlock label="Cargando preferencias..." />;

  const chip = (active: boolean) =>
    cx("rounded-full border px-3 py-1.5 text-sm capitalize transition",
      active ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-600 hover:border-slate-400");

  return (
    <>
      <PageHeader title="Preferencias" subtitle="El asistente las tiene en cuenta al recomendar vuelos, hoteles y actividades." />
      {error && <Alert>{error}</Alert>}
      <form onSubmit={onSubmit} className="space-y-6">
        <Card>
          <h2 className="mb-3 font-semibold text-slate-900">Actividades que disfrutas</h2>
          <div className="flex flex-wrap gap-2">
            {ACTIVIDADES.map((a) => (
              <button type="button" key={a} className={chip(!!prefs.actividades?.includes(a))} onClick={() => toggle("actividades", a)}>{a}</button>
            ))}
          </div>
        </Card>
        <Card>
          <h2 className="mb-3 font-semibold text-slate-900">Vuelos</h2>
          <div className="mb-4 flex flex-wrap gap-2">
            {AEROLINEAS.map((a) => (
              <button type="button" key={a} className={chip(!!prefs.aerolineas_preferidas?.includes(a))} onClick={() => toggle("aerolineas_preferidas", a)}>{a}</button>
            ))}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Asiento preferido">
              <Select value={prefs.asiento_preferido ?? ""} onChange={(e) => setPrefs({ ...prefs, asiento_preferido: e.target.value })}>
                <option value="">Indiferente</option>
                <option value="ventana">Ventana</option>
                <option value="pasillo">Pasillo</option>
              </Select>
            </Field>
            <Field label="Tipo de presupuesto">
              <Select value={prefs.presupuesto_tipo ?? ""} onChange={(e) => setPrefs({ ...prefs, presupuesto_tipo: (e.target.value || undefined) as Preferences["presupuesto_tipo"] })}>
                <option value="">Sin definir</option>
                <option value="ECONOMICO">Económico</option>
                <option value="MODERADO">Moderado</option>
                <option value="PREMIUM">Premium</option>
              </Select>
            </Field>
          </div>
        </Card>
        <Card>
          <Field label="Restricciones" hint="Separadas por comas. Ej.: vegetariano, movilidad reducida, viajo con mascota">
            <Input value={restricciones} onChange={(e) => { setRestricciones(e.target.value); setSaved(false); }} />
          </Field>
        </Card>
        {saveError && <Alert>{saveError}</Alert>}
        {saved && <Alert kind="success">Preferencias guardadas.</Alert>}
        <div className="flex justify-end">
          <Button type="submit" loading={saving}>Guardar preferencias</Button>
        </div>
      </form>
    </>
  );
}
