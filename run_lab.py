"""
Entry point for the LLM Prompt Injection Lab.

Usage:
    python run_lab.py                        # full run: all models, all payloads
    python run_lab.py --models mistral       # single model
    python run_lab.py --runs 3               # 3 runs per payload instead of 5
    python run_lab.py --report-only          # regenerate HTML from existing DB
    python run_lab.py --list-payloads        # print payload list and exit
"""

import argparse
import sys

from lab import PromptInjectionLab, MODELS, RUNS_PER_PAYLOAD, build_payloads
from report import generate_report


def main():
    parser = argparse.ArgumentParser(
        description="LLM Prompt Injection Lab — test open-source models via Ollama"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=MODELS,
        metavar="MODEL",
        help=f"Ollama model names to test (default: {MODELS})",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=RUNS_PER_PAYLOAD,
        help=f"Runs per payload (default: {RUNS_PER_PAYLOAD})",
    )
    parser.add_argument(
        "--db",
        default="results.db",
        help="SQLite database path (default: results.db)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Skip testing; regenerate HTML report from existing DB",
    )
    parser.add_argument(
        "--list-payloads",
        action="store_true",
        help="List all payload names and types, then exit",
    )

    args = parser.parse_args()

    if args.list_payloads:
        payloads = build_payloads()
        print(f"\n{'#':<4}  {'Name':<40}  {'Type':<35}  Severity")
        print("-" * 95)
        for i, p in enumerate(payloads, 1):
            print(f"{i:<4}  {p.name:<40}  {p.payload_type:<35}  {p.severity}")
        print(f"\nTotal: {len(payloads)} payloads")
        sys.exit(0)

    if not args.report_only:
        lab = PromptInjectionLab(
            models=args.models,
            runs_per_payload=args.runs,
            db_path=args.db,
        )
        lab.run()

    generate_report(db_path=args.db)
    print("\nOpen report.html in a browser to view results.")


if __name__ == "__main__":
    main()
