from pathlib import Path
from datetime import datetime


def generate_html_report(current: dict, comparison: dict, output_path: str = "runs/latest_report.html") -> str:
    regressions_html = "".join(
        f"""<tr>
            <td>{r['case_id']}</td>
            <td>{r['input'][:80]}...</td>
            <td>{r['expected']}</td>
            <td style="color:#2e7d32">{r['old_output']}</td>
            <td style="color:#c62828">{r['new_output']}</td>
        </tr>"""
        for r in comparison["regressions"]
    ) or "<tr><td colspan='5'>None — no regressions this run.</td></tr>"

    improvements_html = "".join(
        f"<tr><td>{r['case_id']}</td><td>{r['input'][:80]}...</td>"
        f"<td>{r['old_output']} &rarr; {r['new_output']}</td></tr>"
        for r in comparison["improvements"]
    ) or "<tr><td colspan='3'>None this run.</td></tr>"

    status_colors = {
        "pass": "#2e7d32",
        "warning": "#f9a825",
        "critical": "#c62828",
        "baseline": "#1565c0",
    }
    status_color = status_colors.get(comparison["status"], "#333")
    avg_summary_score = current["avg_summary_score"]
    avg_latency = current["avg_latency_seconds"]

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: -apple-system, Segoe UI, sans-serif; margin: 40px; color: #1a1a1a; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; }}
    th {{ background: #f5f5f5; }}
    .status {{ display: inline-block; padding: 6px 14px; border-radius: 6px; color: white; font-weight: bold; }}
    .metric {{ display: inline-block; margin-right: 30px; font-size: 15px; }}
    h2 {{ margin-top: 40px; }}
</style>
</head>
<body>
    <h1>Eval Diff Report</h1>
    <p>
        <strong>Run:</strong> {current['run_id']} &nbsp;
        <strong>Prompt version:</strong> {current['prompt_version']} &nbsp;
        <strong>Model:</strong> {current['model']} &nbsp;
        <strong>Generated:</strong> {datetime.now().isoformat(timespec='seconds')}
    </p>
    <p><span class="status" style="background:{status_color}">{comparison['status'].upper()}</span></p>
    <p>{comparison['message']}</p>

    <div class="metric"><strong>Pass rate:</strong> {current['pass_rate']:.1%}</div>
    <div class="metric"><strong>Avg summary score:</strong> {avg_summary_score if avg_summary_score is None else f"{avg_summary_score:.2f}/5"}</div>
    <div class="metric"><strong>Avg latency:</strong> {avg_latency if avg_latency is None else f"{avg_latency:.2f}s"}</div>

    <h2>Regressions ({len(comparison['regressions'])})</h2>
    <table>
        <tr><th>Case</th><th>Input</th><th>Expected</th><th>Old Output</th><th>New Output</th></tr>
        {regressions_html}
    </table>

    <h2>Improvements ({len(comparison['improvements'])})</h2>
    <table>
        <tr><th>Case</th><th>Input</th><th>Change</th></tr>
        {improvements_html}
    </table>
</body>
</html>
"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    return output_path
