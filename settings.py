import os
from pathlib import Path

import dotenv

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


def load_openai_api_key() -> str:
    file_values = dotenv.dotenv_values(ENV_PATH)
    openai_api_key = file_values.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        openai_api_key = openai_api_key.strip()
        if _is_placeholder(openai_api_key):
            raise RuntimeError(
                "OPENAI_API_KEY is still a placeholder value. Set a real key in .env."
            )

        # Keep downstream SDKs aligned with the project-local key.
        os.environ["OPENAI_API_KEY"] = openai_api_key
        return openai_api_key

    raise RuntimeError(
        f"OPENAI_API_KEY is not set. Checked environment and {ENV_PATH}."
    )
