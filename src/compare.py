import json
from pathlib import Path
from typing import Optional


def get_sorted_runs(runs_dir: str = "runs") -> list:
    """Run filenames are timestamp-prefixed, so sorting them sorts chronologically."""
    return sorted(Path(runs_dir).glob("run_*.json"))


def load_run(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def compare_runs(
    current: dict,
    previous: Optional[dict],
    warn_threshold: float = 0.03,
    critical_threshold: float = 0.08,
) -> dict:
    """Diffs two eval runs and classifies the result as pass/warning/critical.

    Thresholds exist because a 2-out-of-80 flip is noise, not signal — see
    the README for how to tune these for your own dataset size.
    """
    if previous is None:
        return {
            "status": "baseline",
            "message": "No previous run to compare against. This is the new baseline.",
            "pass_rate_delta": None,
            "regressions": [],
            "improvements": [],
        }

    pass_rate_delta = current["pass_rate"] - previous["pass_rate"]

    prev_by_id = {r["case_id"]: r for r in previous["results"]}
    regressions = []
    improvements = []

    for r in current["results"]:
        prev = prev_by_id.get(r["case_id"])
        if prev is None:
            continue  # new test case, nothing to diff against
        if prev["category_match"] and not r["category_match"]:
            regressions.append({
                "case_id": r["case_id"],
                "input": r["input"],
                "old_output": prev["actual_category"],
                "new_output": r["actual_category"],
                "expected": r["expected_category"],
            })
        elif not prev["category_match"] and r["category_match"]:
            improvements.append({
                "case_id": r["case_id"],
                "input": r["input"],
                "old_output": prev["actual_category"],
                "new_output": r["actual_category"],
                "expected": r["expected_category"],
            })

    if pass_rate_delta < 0 and abs(pass_rate_delta) >= critical_threshold:
        status = "critical"
    elif pass_rate_delta < 0 and abs(pass_rate_delta) >= warn_threshold:
        status = "warning"
    else:
        status = "pass"

    return {
        "status": status,
        "message": f"Pass rate changed from {previous['pass_rate']:.1%} to {current['pass_rate']:.1%}",
        "pass_rate_delta": pass_rate_delta,
        "regressions": regressions,
        "improvements": improvements,
    }


def rolling_drift_check(runs_dir: str = "runs", window: int = 7, drop_threshold: float = 0.05) -> Optional[str]:
    """Slow-drift detector: flags gradual degradation that per-run diffs miss.

    Compares the average pass rate of the last `window` runs against the
    `window` runs before that. Returns a warning string, or None if healthy.
    """
    all_runs = get_sorted_runs(runs_dir)
    if len(all_runs) < window * 2:
        return None  # not enough history yet

    recent = [load_run(p)["pass_rate"] for p in all_runs[-window:]]
    prior = [load_run(p)["pass_rate"] for p in all_runs[-window * 2:-window]]

    recent_avg = sum(recent) / len(recent)
    prior_avg = sum(prior) / len(prior)

    if prior_avg - recent_avg >= drop_threshold:
        return (
            f"Slow drift detected: {window}-run average pass rate dropped from "
            f"{prior_avg:.1%} to {recent_avg:.1%}. No single run triggered an alert, "
            f"but the trend is degrading."
        )
    return None
