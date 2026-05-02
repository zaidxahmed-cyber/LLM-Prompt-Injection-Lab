import time
import requests
from .config import OLLAMA_BASE_URL


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    def is_model_available(self, model: str) -> bool:
        try:
            return any(model in m for m in self.list_models())
        except requests.RequestException:
            return False

    def generate(
        self,
        model: str,
        prompt: str,
        system: str = "",
        timeout: int = 120,
    ) -> tuple[str, int]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 200},
        }
        if system:
            payload["system"] = system

        start = time.time()
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            elapsed_ms = int((time.time() - start) * 1000)
            return resp.json().get("response", ""), elapsed_ms
        except requests.Timeout:
            return "[TIMEOUT — model did not respond in time]", timeout * 1000
        except requests.RequestException as exc:
            return f"[REQUEST ERROR: {exc}]", 0
