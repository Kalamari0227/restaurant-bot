import os
from pathlib import Path

import dotenv

try:
    import streamlit as st
except Exception:  # pragma: no cover - defensive fallback for non-Streamlit contexts
    st = None

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return any(
        marker in normalized
        for marker in (
            "your-api-key",
            "your_actual_api_key",
            "your-openai-api-key",
            "replace-with",
            "replace_me",
        )
    )


def _read_streamlit_secret() -> str | None:
    if st is None:
        return None

    try:
        secret_value = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        return None

    return secret_value if isinstance(secret_value, str) else None


def load_openai_api_key() -> str:
    file_values = dotenv.dotenv_values(ENV_PATH)
    openai_api_key = (
        file_values.get("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or _read_streamlit_secret()
    )
    if openai_api_key:
        openai_api_key = openai_api_key.strip()
        if _is_placeholder(openai_api_key):
            raise RuntimeError(
                "OPENAI_API_KEY is still a placeholder value. Set a real key in .env or Streamlit secrets."
            )

        # Keep downstream SDKs aligned with the project-local key.
        os.environ["OPENAI_API_KEY"] = openai_api_key
        return openai_api_key

    raise RuntimeError(
        f"OPENAI_API_KEY is not set. Checked environment, Streamlit secrets, and {ENV_PATH}."
    )
