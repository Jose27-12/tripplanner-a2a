// Parser de la Agent-Driven UI: separa el texto del agente de los bloques
// <ui type="...">JSON</ui> (contrato en docs/agente-ui-contract.md).

export type Segment =
  | { kind: "text"; text: string }
  | { kind: "ui"; type: string; data: unknown }
  | { kind: "ui-error"; type: string; raw: string }
  | { kind: "ui-pending"; type: string };

const BLOCK = /<ui\s+type\s*=\s*["']([\w-]+)["']\s*>([\s\S]*?)<\/ui>/g;
const OPEN = /<ui\s+type\s*=\s*["']([\w-]+)["']\s*>[\s\S]*$/;

export function parseAgentText(text: string): Segment[] {
  const segments: Segment[] = [];
  const seen = new Set<string>();
  let last = 0;
  for (const match of text.matchAll(BLOCK)) {
    const start = match.index ?? 0;
    if (start > last) segments.push({ kind: "text", text: text.slice(last, start) });
    const [, type, raw] = match;
    try {
      const data = JSON.parse(raw.trim());
      // El servidor ya emite los bloques de las tools; si el modelo repite uno idéntico, se ignora.
      const key = `${type}:${JSON.stringify(data)}`;
      if (!seen.has(key)) segments.push({ kind: "ui", type, data });
      seen.add(key);
    } catch {
      segments.push({ kind: "ui-error", type, raw });
    }
    last = start + match[0].length;
  }
  let rest = text.slice(last);
  // Durante el streaming puede llegar un bloque abierto aún sin cerrar:
  // no se muestra el JSON a medias, solo un marcador de "preparando".
  const open = rest.match(OPEN);
  if (open) {
    const before = rest.slice(0, open.index);
    if (before) segments.push({ kind: "text", text: before });
    segments.push({ kind: "ui-pending", type: open[1] });
    rest = "";
  } else {
    // Un "<u" o "<ui ty" incompleto al final tampoco se muestra.
    rest = rest.replace(/<(u(i(\s[^>]*)?)?)?$/, "");
  }
  if (rest) segments.push({ kind: "text", text: rest });
  return segments.filter((s) => s.kind !== "text" || s.text.trim() !== "");
}
