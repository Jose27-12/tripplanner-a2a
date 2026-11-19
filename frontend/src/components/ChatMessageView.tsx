import { TOOL_LABELS } from "../lib/agentStream";
import type { ChatMessage } from "../lib/useAgentChat";
import { parseAgentText } from "../lib/uiBlocks";
import { AgentBlock, AgentBlockPending } from "./AgentBlock";
import Markdown from "./Markdown";
import { Alert, Spinner } from "./ui";

export function ProcessingIndicator({ tool }: { tool: string | null }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500">
      <Spinner className="h-4 w-4 text-brand-600" />
      <span>{tool ? `${TOOL_LABELS[tool] ?? "Trabajando"}...` : "Pensando..."}</span>
    </div>
  );
}

export default function ChatMessageView({ message, activeTool }: { message: ChatMessage; activeTool?: string | null }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2.5 text-sm text-white">
          {message.text}
        </div>
      </div>
    );
  }

  const segments = parseAgentText(message.text);
  return (
    <div className="flex gap-3">
      <img src="/favicon.svg" alt="" className="mt-1 h-7 w-7 shrink-0" />
      <div className="min-w-0 flex-1 space-y-3">
        {message.tools.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {[...new Set(message.tools)].map((t) => (
              <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">⚙ {TOOL_LABELS[t]?.split(" ")[0] ?? t}</span>
            ))}
          </div>
        )}
        {segments.map((s, i) => {
          if (s.kind === "text")
            return <div key={i} className="rounded-2xl rounded-tl-sm bg-white px-4 py-2.5 text-slate-700 shadow-sm ring-1 ring-slate-200"><Markdown text={s.text} /></div>;
          if (s.kind === "ui") return <AgentBlock key={i} type={s.type} data={s.data} />;
          if (s.kind === "ui-pending") return <AgentBlockPending key={i} type={s.type} />;
          return <Alert key={i}>No se pudo mostrar un resultado del agente ({s.type}).</Alert>;
        })}
        {!message.done && <ProcessingIndicator tool={activeTool ?? null} />}
        {message.error && <Alert>{message.error}</Alert>}
        {message.done && !message.text && !message.error && (
          <p className="text-sm text-slate-400">(sin respuesta)</p>
        )}
      </div>
    </div>
  );
}
