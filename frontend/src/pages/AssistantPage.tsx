import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import ChatMessageView from "../components/ChatMessageView";
import { IconSend } from "../components/icons";
import { Button, Textarea } from "../components/ui";
import { useAgentChat } from "../lib/useAgentChat";

const SUGGESTIONS = [
  "Quiero organizar unas vacaciones de cuatro días en Cartagena. Salgo desde Bogotá, viajo con dos personas más y tengo un presupuesto de 5 millones de pesos. Quiero conocer el clima, encontrar vuelos y organizar algunas actividades turísticas.",
  "¿Qué viajes tengo guardados?",
  "¿Cómo estará el clima en Santa Marta la próxima semana?",
  "Muéstrame mis reservas",
];

export default function AssistantPage() {
  const { user } = useAuth();
  const chat = useAgentChat(`tripplanner:chat:${user?.sub ?? "anon"}`);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const lastText = chat.messages[chat.messages.length - 1]?.text;
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chat.messages.length, lastText]);

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!input.trim() || chat.busy) return;
    chat.send(input);
    setInput("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col lg:h-[calc(100vh-4rem)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Asistente</h1>
          <p className="text-sm text-slate-500">El orquestador coordina a los agentes de vuelos y clima y gestiona tus viajes.</p>
        </div>
        {chat.messages.length > 0 && (
          <Button variant="secondary" onClick={chat.reset} disabled={chat.busy}>Nueva conversación</Button>
        )}
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto rounded-2xl bg-slate-100/60 p-4 sm:p-6">
        {chat.messages.length === 0 ? (
          <div className="mx-auto max-w-2xl py-6 text-center">
            <img src="/favicon.svg" alt="" className="mx-auto h-12 w-12" />
            <h2 className="mt-3 text-lg font-semibold text-slate-900">¿A dónde quieres viajar?</h2>
            <p className="mt-1 text-sm text-slate-500">
              Puedo buscar vuelos, consultar el clima, crear tu viaje, armar el itinerario y registrar reservas simuladas.
            </p>
            <div className="mt-6 grid gap-2 text-left">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => chat.send(s)}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm transition hover:border-brand-500/50 hover:shadow">
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          chat.messages.map((m, i) => (
            <ChatMessageView key={m.id} message={m} activeTool={i === chat.messages.length - 1 ? chat.activeTool : null} />
          ))
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="mt-3 flex items-end gap-2">
        <Textarea
          rows={2}
          className="min-h-[3rem] flex-1 resize-none"
          placeholder="Escribe tu mensaje… (Enter para enviar, Shift+Enter para salto de línea)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Mensaje para el asistente"
        />
        {chat.busy ? (
          <Button type="button" variant="secondary" onClick={chat.stop}>Detener</Button>
        ) : (
          <Button type="submit" disabled={!input.trim()} aria-label="Enviar"><IconSend className="h-4 w-4" /> Enviar</Button>
        )}
      </form>
      <p className="mt-1 text-center text-[11px] text-slate-400">
        Las reservas son simuladas. Nunca compartas datos de tarjetas: el asistente no los solicita.
      </p>
    </div>
  );
}
