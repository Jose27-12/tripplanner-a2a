// Formato de fechas y dinero para Colombia (es-CO).

export function parseDate(iso: string): Date {
  // "YYYY-MM-DD" se interpreta como fecha local (no UTC) para no correr un día.
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

export function formatDate(iso?: string | null, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }) {
  if (!iso) return "—";
  return parseDate(iso).toLocaleDateString("es-CO", opts);
}

export function formatDateRange(start: string, end: string) {
  const s = parseDate(start);
  const e = parseDate(end);
  const sameYear = s.getFullYear() === e.getFullYear();
  const a = s.toLocaleDateString("es-CO", { day: "numeric", month: "short", ...(sameYear ? {} : { year: "numeric" }) });
  const b = e.toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" });
  return `${a} – ${b}`;
}

export function daysBetween(start: string, end: string) {
  return Math.round((parseDate(end).getTime() - parseDate(start).getTime()) / 86_400_000) + 1;
}

export function addDays(iso: string, n: number) {
  const d = parseDate(iso);
  d.setDate(d.getDate() + n);
  return toIso(d);
}

export function toIso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function todayIso() {
  return toIso(new Date());
}

export function formatMoney(amount?: number | null, currency: string = "COP") {
  if (amount === null || amount === undefined || Number.isNaN(Number(amount))) return "—";
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency,
    maximumFractionDigits: currency === "COP" ? 0 : 2,
  }).format(Number(amount));
}

export function formatDuration(minutes?: number) {
  if (!minutes && minutes !== 0) return "—";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h} h ${m ? `${m} min` : ""}`.trim() : `${m} min`;
}
