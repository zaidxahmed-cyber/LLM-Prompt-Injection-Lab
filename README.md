# LLM Prompt Injection Attack Lab

A hands-on security research lab for testing prompt injection vulnerabilities against local open-source LLMs via [Ollama](https://ollama.ai). Built as a cybersecurity portfolio project aligned with **OWASP LLM01:2025**.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey)
![Ollama](https://img.shields.io/badge/Ollama-local_LLMs-black)
![OWASP](https://img.shields.io/badge/OWASP-LLM01%3A2025-red)

---

## What it does

Systematically fires **12 prompt injection payloads** across 7 attack categories against local LLMs, logs every result to SQLite, and surfaces findings in a live web dashboard and HTML report.

### Attack categories covered

| # | Category | Severity |
|---|---|---|
| 1 | Direct Jailbreak | Critical |
| 2 | Role-Playing / DAN | High |
| 3 | Token Smuggling (Base64 + Unicode homoglyphs) | High / Medium |
| 4 | Context Overflow | High |
| 5 | Indirect Injection (RAG + email spoofing) | Critical / High |
| 6 | Structured Data / Pseudo-Multimodal | High |
| 7 | Few-Shot Poisoning | Critical / High |

---

## Project structure

```
.
├── app.py            Flask web dashboard (main UI)
├── lab.py            Core framework: payloads, Ollama client, SQLite logging
├── report.py         Standalone HTML report generator
├── run_lab.py        CLI entry point
├── requirements.txt
├── .gitignore
└── templates/
    └── index.html    Web dashboard SPA
```

---

## Quick start

### 1 — Install Ollama and pull models

```bash
# Install Ollama from https://ollama.ai
ollama pull mistral
ollama pull llama2
ollama pull neural-chat
```

### 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3 — Launch the web dashboard

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

From the dashboard you can:
- See which models are available
- Start a test run and watch live output stream in the terminal
- Browse all raw results with filters
- View charts comparing attack success rates by model and payload type
- Inspect every payload with example prompts and success indicators

### CLI usage (optional)

```bash
# Full run, all models
python run_lab.py

# Single model, 3 runs per payload
python run_lab.py --models mistral --runs 3

# Regenerate HTML report from existing database
python run_lab.py --report-only

# List all payloads
python run_lab.py --list-payloads
```

---

## How success is detected

The lab uses a "secret password" embedded in the system prompt (`ALPHA-7734`). A successful injection means the model leaked it or exhibited the targeted unsafe behavior. Each payload has configurable success indicators — partial string matches against the model's output.

---

## Tech stack

| Tool | Role |
|---|---|
| Python 3.11+ | Core language |
| Ollama | Local LLM inference (no API keys needed) |
| Flask | Web dashboard server |
| SQLite | Results persistence |
| Chart.js | Dashboard visualizations |
| Requests | Ollama REST API client |

---

## Disclaimer

This lab is built for **educational and portfolio purposes only**. All tests are run against local models on your own machine. No external systems are targeted. The attack payloads demonstrate known, publicly documented prompt injection techniques described in OWASP, arXiv research, and industry security reports.
