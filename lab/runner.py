import time
import random
from datetime import datetime

from .config import MODELS, RUNS_PER_PAYLOAD, SYSTEM_PROMPT, OLLAMA_BASE_URL, DB_PATH
from .payloads import build_payloads
from .client import OllamaClient
from .db import Result, ResultsDB


def detect_success(output: str, indicators: list[str]) -> bool:
    lower = output.lower()
    return any(ind.lower() in lower for ind in indicators)


class PromptInjectionLab:
    def __init__(
        self,
        models: list[str] = None,
        runs_per_payload: int = RUNS_PER_PAYLOAD,
        db_path: str = DB_PATH,
    ):
        self.models = models or MODELS
        self.runs = runs_per_payload
        self.client = OllamaClient()
        self.db = ResultsDB(db_path)
        self.payloads = build_payloads()

    def _check_models(self) -> list[str]:
        available = []
        for model in self.models:
            if self.client.is_model_available(model):
                available.append(model)
                print(f"  [OK] {model}")
            else:
                print(f"  [SKIP] {model} — not found in Ollama, skipping")
        return available

    def run(self):
        print("\n=== LLM Prompt Injection Lab ===")
        print(f"Checking model availability at {OLLAMA_BASE_URL}...")
        active_models = self._check_models()

        if not active_models:
            print(
                "\n[ERROR] No models available. "
                "Start Ollama and pull at least one model:\n"
                "  ollama pull mistral\n"
                "  ollama pull llama2\n"
                "  ollama pull neural-chat"
            )
            return

        total = len(active_models) * len(self.payloads) * self.runs
        done = 0
        print(
            f"\nRunning {len(self.payloads)} payloads x {len(active_models)} models "
            f"x {self.runs} runs = {total} total requests\n"
        )

        for model in active_models:
            print(f"\n--- Model: {model} ---")
            for payload in self.payloads:
                successes = 0
                for run_num in range(1, self.runs + 1):
                    output, elapsed = self.client.generate(
                        model=model,
                        prompt=payload.prompt,
                        system=SYSTEM_PROMPT,
                    )
                    success = detect_success(output, payload.success_indicators)
                    if success:
                        successes += 1

                    self.db.insert(Result(
                        model_name=model,
                        payload_type=payload.payload_type,
                        payload_name=payload.name,
                        input_prompt=payload.prompt,
                        output=output,
                        success=success,
                        severity=payload.severity,
                        timestamp=datetime.utcnow().isoformat(),
                        run_number=run_num,
                        response_time_ms=elapsed,
                    ))
                    done += 1

                    status = "PASS (attacked)" if success else "HOLD (defended)"
                    print(
                        f"  [{done:>4}/{total}] {payload.name:<40} "
                        f"run {run_num}/{self.runs}  {status}  ({elapsed}ms)"
                    )
                    time.sleep(random.uniform(0.3, 0.8))

                rate = successes / self.runs * 100
                print(
                    f"          => {payload.payload_type}: "
                    f"{successes}/{self.runs} succeeded ({rate:.0f}%)"
                )

        print(f"\n[DONE] All results saved to {self.db.db_path}")
