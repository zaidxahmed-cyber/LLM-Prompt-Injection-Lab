"""
HTML report generator for the Prompt Injection Lab.
Reads from the SQLite database and produces a self-contained HTML file.
"""

import json
from datetime import datetime
from lab import ResultsDB, DB_PATH

SEVERITY_COLOR = {
    "Critical": "#dc2626",
    "High":     "#ea580c",
    "Medium":   "#d97706",
    "Low":      "#65a30d",
}

REPORT_PATH = "report.html"


# ---------------------------------------------------------------------------
# Chart data helpers
# ---------------------------------------------------------------------------

def _bar_chart_js(labels: list[str], datasets: list[dict], chart_id: str, title: str) -> str:
    """Return a Chart.js canvas + init script for a grouped bar chart."""
    return f"""
<canvas id="{chart_id}" style="max-height:320px;"></canvas>
<script>
new Chart(document.getElementById('{chart_id}'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(labels)},
    datasets: {json.dumps(datasets)}
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position: 'top' }},
      title: {{ display: true, text: {json.dumps(title)} }}
    }},
    scales: {{
      y: {{ beginAtZero: true, max: 100, title: {{ display: true, text: 'Success Rate (%)' }} }}
    }}
  }}
}});
</script>
"""


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _model_section(model_stats: list[dict]) -> str:
    rows = ""
    for s in model_stats:
        rate = s["successes"] / s["total"] * 100 if s["total"] else 0
        bar_color = "#dc2626" if rate >= 50 else "#f59e0b" if rate >= 20 else "#22c55e"
        rows += f"""
        <tr>
          <td>{s['model_name']}</td>
          <td>{s['total']}</td>
          <td>{s['successes']}</td>
          <td>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:{rate:.0f}%;height:14px;background:{bar_color};border-radius:4px;min-width:2px;"></div>
              <span>{rate:.1f}%</span>
            </div>
          </td>
        </tr>"""
    return f"""
<section>
  <h2>Success Rate by Model</h2>
  <table>
    <thead><tr><th>Model</th><th>Total Runs</th><th>Bypassed</th><th>Attack Success Rate</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>"""


def _payload_section(type_stats: list[dict]) -> str:
    rows = ""
    for s in type_stats:
        rate = s["successes"] / s["total"] * 100 if s["total"] else 0
        sev = s.get("severity", "Medium")
        sev_color = SEVERITY_COLOR.get(sev, "#888")
        bar_color = "#dc2626" if rate >= 50 else "#f59e0b" if rate >= 20 else "#22c55e"
        rows += f"""
        <tr>
          <td>{s['payload_type']}</td>
          <td><span class="badge" style="background:{sev_color}">{sev}</span></td>
          <td>{s['total']}</td>
          <td>{s['successes']}</td>
          <td>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:{rate:.0f}%;height:14px;background:{bar_color};border-radius:4px;min-width:2px;"></div>
              <span>{rate:.1f}%</span>
            </div>
          </td>
        </tr>"""
    return f"""
<section>
  <h2>Success Rate by Payload Type</h2>
  <table>
    <thead>
      <tr>
        <th>Payload Type</th><th>Severity</th>
        <th>Total Runs</th><th>Bypassed</th><th>Attack Success Rate</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>"""


def _samples_section(samples: list[dict]) -> str:
    cards = ""
    for s in samples:
        success_label = (
            '<span class="badge" style="background:#dc2626">BYPASSED</span>'
            if s["success"] == "yes"
            else '<span class="badge" style="background:#22c55e">DEFENDED</span>'
        )
        # Truncate long prompts / outputs for readability
        prompt_preview = s["input_prompt"][:400].replace("<", "&lt;").replace(">", "&gt;")
        output_preview = s["output"][:600].replace("<", "&lt;").replace(">", "&gt;")
        if len(s["input_prompt"]) > 400:
            prompt_preview += "…"
        if len(s["output"]) > 600:
            output_preview += "…"

        cards += f"""
<div class="card">
  <div class="card-header">
    <strong>{s['payload_type']}</strong> — {s['model_name']} {success_label}
  </div>
  <div class="card-body">
    <p><em>Prompt (truncated):</em></p>
    <pre>{prompt_preview}</pre>
    <p><em>Model output (truncated):</em></p>
    <pre>{output_preview}</pre>
  </div>
</div>"""

    return f"""
<section>
  <h2>Example Outputs</h2>
  {cards}
</section>"""


def _charts_section(type_stats: list[dict], model_stats: list[dict]) -> str:
    type_labels = [s["payload_type"] for s in type_stats]
    type_rates  = [
        round(s["successes"] / s["total"] * 100, 1) if s["total"] else 0
        for s in type_stats
    ]

    model_labels = [s["model_name"] for s in model_stats]
    model_rates  = [
        round(s["successes"] / s["total"] * 100, 1) if s["total"] else 0
        for s in model_stats
    ]

    type_chart = _bar_chart_js(
        labels=type_labels,
        datasets=[{
            "label": "Attack Success Rate (%)",
            "data": type_rates,
            "backgroundColor": [
                "#dc2626" if r >= 50 else "#f59e0b" if r >= 20 else "#22c55e"
                for r in type_rates
            ],
        }],
        chart_id="typeChart",
        title="Attack Success Rate by Payload Type",
    )

    model_chart = _bar_chart_js(
        labels=model_labels,
        datasets=[{
            "label": "Attack Success Rate (%)",
            "data": model_rates,
            "backgroundColor": [
                "#dc2626" if r >= 50 else "#f59e0b" if r >= 20 else "#22c55e"
                for r in model_rates
            ],
        }],
        chart_id="modelChart",
        title="Attack Success Rate by Model",
    )

    return f"""
<section>
  <h2>Visual Comparison</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:2rem;">
    <div>{type_chart}</div>
    <div>{model_chart}</div>
  </div>
</section>"""


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------

def generate_report(db_path: str = DB_PATH, output_path: str = REPORT_PATH):
    db = ResultsDB(db_path)
    stats = db.fetch_stats()

    model_stats = stats["model_stats"]
    type_stats  = stats["type_stats"]
    samples     = stats["samples"]

    if not model_stats:
        print("[WARN] No results in database. Run the lab first.")
        return

    total_runs    = sum(s["total"]     for s in model_stats)
    total_success = sum(s["successes"] for s in model_stats)
    overall_rate  = total_success / total_runs * 100 if total_runs else 0

    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LLM Prompt Injection Lab — Report</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0f172a; color: #e2e8f0;
      margin: 0; padding: 2rem;
      line-height: 1.6;
    }}
    h1 {{ font-size: 2rem; color: #f8fafc; margin-bottom: 0.25rem; }}
    h2 {{ font-size: 1.3rem; color: #94a3b8; border-bottom: 1px solid #1e293b; padding-bottom: 0.4rem; margin-top: 2rem; }}
    .subtitle {{ color: #64748b; font-size: 0.9rem; margin-bottom: 2rem; }}
    .summary-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem; margin-bottom: 2rem;
    }}
    .stat-card {{
      background: #1e293b; border-radius: 10px; padding: 1.2rem;
      text-align: center; border: 1px solid #334155;
    }}
    .stat-card .value {{ font-size: 2rem; font-weight: 700; color: #f8fafc; }}
    .stat-card .label {{ font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }}
    section {{ margin-bottom: 3rem; }}
    table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 10px; overflow: hidden; }}
    th {{ background: #0f172a; color: #94a3b8; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.75rem 1rem; text-align: left; }}
    td {{ padding: 0.75rem 1rem; border-bottom: 1px solid #0f172a; font-size: 0.9rem; }}
    tr:last-child td {{ border-bottom: none; }}
    .badge {{
      display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px;
      font-size: 0.72rem; font-weight: 700; color: #fff; text-transform: uppercase;
    }}
    .card {{ background: #1e293b; border-radius: 10px; margin-bottom: 1rem; border: 1px solid #334155; overflow: hidden; }}
    .card-header {{ background: #0f172a; padding: 0.75rem 1rem; font-size: 0.9rem; display: flex; align-items: center; gap: 0.5rem; }}
    .card-body {{ padding: 1rem; }}
    pre {{
      background: #0f172a; padding: 0.75rem; border-radius: 6px;
      font-size: 0.78rem; overflow-x: auto; white-space: pre-wrap;
      word-break: break-word; color: #a3e635; margin: 0.25rem 0 0.75rem;
    }}
    canvas {{ background: #1e293b; border-radius: 10px; padding: 1rem; }}
  </style>
</head>
<body>
  <h1>LLM Prompt Injection Attack Lab</h1>
  <p class="subtitle">Generated: {generated_at} &nbsp;|&nbsp; For portfolio / educational use only.</p>

  <div class="summary-grid">
    <div class="stat-card">
      <div class="value">{total_runs}</div>
      <div class="label">Total Runs</div>
    </div>
    <div class="stat-card">
      <div class="value">{total_success}</div>
      <div class="label">Successful Attacks</div>
    </div>
    <div class="stat-card">
      <div class="value" style="color:{'#dc2626' if overall_rate>=50 else '#f59e0b' if overall_rate>=20 else '#22c55e'}">{overall_rate:.1f}%</div>
      <div class="label">Overall Attack Rate</div>
    </div>
    <div class="stat-card">
      <div class="value">{len(model_stats)}</div>
      <div class="label">Models Tested</div>
    </div>
    <div class="stat-card">
      <div class="value">{len(type_stats)}</div>
      <div class="label">Payload Types</div>
    </div>
  </div>

  {_model_section(model_stats)}
  {_payload_section(type_stats)}
  {_charts_section(type_stats, model_stats)}
  {_samples_section(samples)}

  <footer style="color:#334155;font-size:0.75rem;margin-top:3rem;">
    Built with Python · Ollama · Chart.js &nbsp;|&nbsp;
    OWASP LLM01:2025 — Prompt Injection research lab
  </footer>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[DONE] Report written to {output_path}")
