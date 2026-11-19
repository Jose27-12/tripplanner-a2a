"""Agent-Driven UI: emisión determinista de bloques <ui type="...">.

Los bloques que producen las tools (vuelos y clima de los especialistas A2A,
viajes/itinerarios/reservas de las Lambdas) NO pasan por el LLM: se encolan
aquí y el entrypoint los inyecta tal cual en el stream HTTP hacia el
navegador. Así se reenvían sin modificaciones (no hay riesgo de que el modelo
altere el JSON) y la respuesta es más rápida (el modelo no reescribe miles de
tokens). Al LLM solo se le devuelve un resumen con los datos para razonar.

La cola vive en un ContextVar por invocación; las tools síncronas que Strands
ejecuta en hilos heredan una copia del contexto que apunta a la misma lista.
"""
import json
import re
from contextvars import ContextVar, Token

_queue: ContextVar[list[str] | None] = ContextVar("ui_block_queue", default=None)

_BLOCK = re.compile(r"""<ui\s+type\s*=\s*["']([\w-]+)["']\s*>([\s\S]*?)</ui>""")


def start_collecting() -> Token:
    return _queue.set([])


def stop_collecting(token: Token) -> None:
    _queue.reset(token)


def drain() -> list[str]:
    queue = _queue.get()
    if not queue:
        return []
    items = list(queue)
    queue.clear()
    return items


def emit(ui_type: str, data) -> str:
    """Encola un bloque para el usuario y devuelve el texto que verá el LLM."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    queue = _queue.get()
    if queue is not None:
        queue.append(f'\n<ui type="{ui_type}">{payload}</ui>\n')
    return (
        f"[El sistema ya mostró al usuario estos datos como tarjetas '{ui_type}'. "
        f"NO escribas el bloque <ui> ni repitas la tabla; usa los datos solo para "
        f"tu explicación]: {payload}"
    )


def forward_blocks_from(text: str) -> str:
    """Extrae los bloques <ui> de la respuesta de un especialista, los encola sin
    modificarlos y devuelve el texto para el LLM con los datos resumidos."""
    notes = []
    for ui_type, raw in _BLOCK.findall(text):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        notes.append(emit(ui_type, data))
    clean = _BLOCK.sub("", text).strip()
    return "\n".join([clean, *notes]).strip()
