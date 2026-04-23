import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from settings import load_openai_api_key


class LoadOpenAIApiKeyTests(unittest.TestCase):
    def test_loads_api_key_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
            fake_streamlit = SimpleNamespace(secrets={})

            with patch.dict("os.environ", {}, clear=True):
                with patch("settings.ENV_PATH", env_path):
                    with patch("settings.st", fake_streamlit):
                        self.assertEqual(load_openai_api_key(), "test-key")

    def test_env_file_overrides_shell_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("OPENAI_API_KEY=real-project-key\n", encoding="utf-8")
            fake_streamlit = SimpleNamespace(secrets={})

            with patch.dict(
                "os.environ",
                {"OPENAI_API_KEY": "your_actual_api_key_here"},
                clear=True,
            ):
                with patch("settings.ENV_PATH", env_path):
                    with patch("settings.st", fake_streamlit):
                        self.assertEqual(load_openai_api_key(), "real-project-key")

    def test_raises_when_api_key_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("LAW_OC=test-value\n", encoding="utf-8")
            fake_streamlit = SimpleNamespace(secrets={})

            with patch.dict("os.environ", {}, clear=True):
                with patch("settings.ENV_PATH", env_path):
                    with patch("settings.st", fake_streamlit):
                        with self.assertRaises(RuntimeError):
                            load_openai_api_key()

    def test_raises_when_only_placeholder_key_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("", encoding="utf-8")
            fake_streamlit = SimpleNamespace(secrets={})

            with patch.dict(
                "os.environ",
                {"OPENAI_API_KEY": "your_actual_api_key_here"},
                clear=True,
            ):
                with patch("settings.ENV_PATH", env_path):
                    with patch("settings.st", fake_streamlit):
                        with self.assertRaises(RuntimeError):
                            load_openai_api_key()

    def test_loads_api_key_from_streamlit_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("", encoding="utf-8")

            fake_streamlit = SimpleNamespace(secrets={"OPENAI_API_KEY": "streamlit-key"})

            with patch.dict("os.environ", {}, clear=True):
                with patch("settings.ENV_PATH", env_path):
                    with patch("settings.st", fake_streamlit):
                        self.assertEqual(load_openai_api_key(), "streamlit-key")


if __name__ == "__main__":
    unittest.main()
