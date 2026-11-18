import os

from strands.models.gemini import GeminiModel

# Modelo configurable por variable de entorno.
DEFAULT_GEMINI_MODEL = "gemini-3.7-flash"


def load_model() -> GeminiModel:
    """Cliente de Gemini. La API key se lee de GEMINI_API_KEY."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")
    return GeminiModel(
        client_args={"api_key": api_key},
        model_id=os.environ.get("GEMINI_MODEL_ID", DEFAULT_GEMINI_MODEL),
    )