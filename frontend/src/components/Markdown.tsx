// Render mínimo y seguro de markdown (sin HTML crudo): párrafos, títulos,
// listas, **negrita**, *cursiva* y `código`.
import { Fragment, type ReactNode } from "react";

function inline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) return <strong key={i}>{p.slice(2, -2)}</strong>;
    if (p.startsWith("`") && p.endsWith("`")) return <code key={i} className="rounded bg-slate-100 px-1 text-[0.85em]">{p.slice(1, -1)}</code>;
    if (p.startsWith("*") && p.endsWith("*") && p.length > 2) return <em key={i}>{p.slice(1, -1)}</em>;
    return <Fragment key={i}>{p}</Fragment>;
  });
}

export default function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r/g, "").split("\n");
  const out: ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flush = () => {
    if (!list) return;
    const items = list.items.map((it, i) => <li key={i}>{inline(it)}</li>);
    out.push(list.ordered
      ? <ol key={out.length} className="my-2 list-decimal space-y-1 pl-5">{items}</ol>
      : <ul key={out.length} className="my-2 list-disc space-y-1 pl-5">{items}</ul>);
    list = null;
  };

  for (const line of lines) {
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const heading = line.match(/^\s*#{1,6}\s+(.*)$/);
    if (bullet || ordered) {
      const isOrdered = !!ordered;
      if (!list || list.ordered !== isOrdered) { flush(); list = { ordered: isOrdered, items: [] }; }
      list.items.push((bullet ?? ordered)![1]);
      continue;
    }
    flush();
    if (heading) out.push(<p key={out.length} className="mt-3 font-semibold text-slate-900">{inline(heading[1])}</p>);
    else if (line.trim()) out.push(<p key={out.length} className="my-1.5">{inline(line)}</p>);
  }
  flush();
  return <div className="text-sm leading-relaxed">{out}</div>;
}
