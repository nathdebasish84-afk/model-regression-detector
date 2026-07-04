import argparse
import sys
from pathlib import Path

from src.eval_runner import run_eval
from src.compare import get_sorted_runs, load_run, compare_runs, rolling_drift_check
from src.report import generate_html_report
from src.alert import send_slack_alert


def main():
    parser = argparse.ArgumentParser(description="Run the LLM regression eval pipeline")
    parser.add_argument("--prompt", default="prompts/email_classifier_v1.yaml")
    parser.add_argument("--dataset", default="data/golden_dataset.json")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--no-alert", action="store_true", help="Skip sending a Slack alert")
    args = parser.parse_args()

    print(f"Running eval — prompt: {args.prompt} | dataset: {args.dataset}")
    run_file = run_eval(args.prompt, args.dataset, args.runs_dir)
    current = load_run(Path(run_file))

    all_runs = get_sorted_runs(args.runs_dir)
    previous = load_run(all_runs[-2]) if len(all_runs) >= 2 else None

    comparison = compare_runs(current, previous)
    report_path = generate_html_report(current, comparison, output_path=f"{args.runs_dir}/latest_report.html")

    drift_warning = rolling_drift_check(args.runs_dir)
    if drift_warning:
        print(f"\n⚠️  {drift_warning}")

    print(f"\nStatus: {comparison['status'].upper()}")
    print(f"Pass rate: {current['pass_rate']:.1%}")
    print(f"Regressions: {len(comparison['regressions'])} | Improvements: {len(comparison['improvements'])}")
    print(f"Report: {report_path}")

    if not args.no_alert:
        send_slack_alert(current, comparison, report_url=report_path)

    if comparison["status"] == "critical":
        print("\nCritical regression detected — failing CI.")
        sys.exit(1)


if __name__ == "__main__":
    main()
