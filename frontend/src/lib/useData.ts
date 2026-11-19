import { useCallback, useEffect, useRef, useState } from "react";

/** Se emite cuando cambian datos de negocio (p. ej. el agente creó un viaje o una reserva). */
export const DATA_CHANGED_EVENT = "tripplanner:data-changed";

export function notifyDataChanged() {
  window.dispatchEvent(new Event(DATA_CHANGED_EVENT));
}

/**
 * Carga datos asíncronos con estado de carga/error y los recarga cuando
 * cambian las dependencias o cuando otra parte de la app (el chat) modifica datos.
 */
export function useData<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await loaderRef.current());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ocurrió un error inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    window.addEventListener(DATA_CHANGED_EVENT, reload);
    return () => window.removeEventListener(DATA_CHANGED_EVENT, reload);
  }, [reload]);

  return { data, error, loading, reload, setData };
}
