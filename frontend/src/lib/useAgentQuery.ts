import { useCallback, useRef, useState } from "react";
import { newSessionId, streamAgent } from "./agentStream";
import { parseAgentText, type Segment } from "./uiBlocks";

/** Consulta puntual al Orchestrator (pantallas Vuelos y Clima), con streaming. */
export function useAgentQuery() {
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tool, setTool] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (prompt: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setText("");
    setError("");
    setBusy(true);
    try {
      for await (const ev of streamAgent(prompt, newSessionId(), controller.signal)) {
        if (ev.kind === "text") { setTool(null); setText((t) => t + ev.text); }
        else if (ev.kind === "tool") setTool(ev.name);
        else setError(ev.message);
      }
    } finally {
      if (abortRef.current === controller) {
        setBusy(false);
        setTool(null);
      }
    }
  }, []);

  const segments: Segment[] = parseAgentText(text);
  return { run, text, segments, error, busy, tool };
}
