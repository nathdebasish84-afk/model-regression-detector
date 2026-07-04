import os
import requests


def send_slack_alert(current: dict, comparison: dict, report_url: str = "") -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[alert] SLACK_WEBHOOK_URL not set, skipping Slack alert")
        return

    emoji = {"pass": "✅", "warning": "⚠️", "critical": "🚨", "baseline": "🆕"}.get(comparison["status"], "ℹ️")
    text = (
        f"{emoji} *Eval run {current['run_id']}* — status: *{comparison['status'].upper()}*\n"
        f"Prompt version: `{current['prompt_version']}` | Model: `{current['model']}`\n"
        f"{comparison['message']}\n"
        f"Regressions: {len(comparison['regressions'])} | Improvements: {len(comparison['improvements'])}"
    )
    if report_url:
        text += f"\nReport: {report_url}"

    try:
        requests.post(webhook_url, json={"text": text}, timeout=10)
    except requests.RequestException as e:
        print(f"[alert] Failed to send Slack alert: {e}")
