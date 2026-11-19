import { useCallback, useEffect, useRef, useState } from "react";
import { MUTATING_TOOLS, newSessionId, streamAgent } from "./agentStream";
import { notifyDataChanged } from "./useData";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  tools: string[];
  error?: string;
  done: boolean;
}

interface Stored {
  sessionId: string;
  messages: ChatMessage[];
}

function load(key: string): Stored {
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw) as Stored;
      // Un mensaje que quedó a medias (pestaña cerrada) se marca como terminado.
      parsed.messages = parsed.messages.map((m) => ({ ...m, done: true }));
      return parsed;
    }
  } catch {
    /* almacenamiento no disponible: conversación nueva */
  }
  return { sessionId: newSessionId(), messages: [] };
}

/**
 * Conversación con el Orchestrator. El session id se mantiene estable para que
 * AgentCore y su memoria conserven el contexto; el historial se guarda en el
 * navegador solo para volver a mostrarlo (la fuente de verdad es el backend).
 */
export function useAgentChat(storageKey: string) {
  const [state, setState] = useState<Stored>(() => load(storageKey));
  const [busy, setBusy] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(state));
    } catch {
      /* ignorar */
    }
  }, [storageKey, state]);

  const update = (id: string, fn: (m: ChatMessage) => ChatMessage) =>
    setState((s) => ({ ...s, messages: s.messages.map((m) => (m.id === id ? fn(m) : m)) }));

  const send = useCallback(async (prompt: string) => {
    const text = prompt.trim();
    if (!text || busy) return;
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", text, tools: [], done: true };
    const botId = crypto.randomUUID();
    const botMsg: ChatMessage = { id: botId, role: "assistant", text: "", tools: [], done: false };
    setState((s) => ({ ...s, messages: [...s.messages, userMsg, botMsg] }));
    setBusy(true);

    const controller = new AbortController();
    abortRef.current = controller;
    let mutated = false;
    try {
      for await (const ev of streamAgent(text, state.sessionId, controller.signal)) {
        if (ev.kind === "text") {
          setActiveTool(null);
          update(botId, (m) => ({ ...m, text: m.text + ev.text }));
        } else if (ev.kind === "tool") {
          setActiveTool(ev.name);
          if (MUTATING_TOOLS.has(ev.name)) mutated = true;
          update(botId, (m) => ({ ...m, tools: [...m.tools, ev.name] }));
        } else {
          update(botId, (m) => ({ ...m, error: ev.message }));
        }
      }
    } finally {
      update(botId, (m) => ({ ...m, done: true }));
      setBusy(false);
      setActiveTool(null);
      abortRef.current = null;
      // El agente creó o modificó datos: refrescar Dashboard, Mis viajes, Reservas...
      if (mutated) notifyDataChanged();
    }
  }, [busy, state.sessionId]);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState({ sessionId: newSessionId(), messages: [] });
  }, []);

  return { messages: state.messages, sessionId: state.sessionId, busy, activeTool, send, stop, reset };
}
