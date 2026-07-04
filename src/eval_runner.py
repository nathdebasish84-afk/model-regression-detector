import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .classifier import classify_email, load_prompt_config
from .llm_client import get_client

# Model used to grade summary quality. Kept separate from the model under
# test so a bad model isn't grading its own homework.
JUDGE_MODEL = "llama-3.3-70b-versatile"


def judge_summary(email_text: str, expected_summary: str, generated_summary: str):
    """LLM-as-judge: scores 1-5 how well the generated summary matches intent."""
    client = get_client()
    prompt = f"""You are grading how well a generated summary captures the key point \
of a customer email compared to an ideal summary.

Email: {email_text}
Ideal summary: {expected_summary}
Generated summary: {generated_summary}

Rate the generated summary's quality from 1 to 5 \
(5 = fully captures the key point, 1 = irrelevant or wrong).
Respond with ONLY a JSON object: {{"score": <int 1-5>, "reason": "<one sentence>"}}"""

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=100,
        response_format={"type": "json_object"},
    )
    try:
        parsed = json.loads(response.choices[0].message.content)
        return int(parsed["score"]), parsed.get("reason", "")
    except Exception:
        return None, "judge_parse_error"


def load_golden_dataset(path: str) -> list:
    with open(path) as f:
        return json.load(f)["cases"]


def run_eval(prompt_config_path: str, dataset_path: str, output_dir: str = "runs") -> str:
    """Runs every case in the golden dataset through the classifier, scores it,
    and writes a timestamped run record to disk. Returns the path to that file.
    """
    config = load_prompt_config(prompt_config_path)
    cases = load_golden_dataset(dataset_path)

    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()
    results = []

    for case in cases:
        try:
            output = classify_email(case["input"], config)
            category_match = output["category"] == case["expected_category"]
            judge_score, judge_reason = judge_summary(
                case["input"], case["expected_summary"], output["summary"]
            )
            results.append({
                "case_id": case["id"],
                "difficulty": case.get("expected_difficulty", "normal"),
                "input": case["input"],
                "expected_category": case["expected_category"],
                "actual_category": output["category"],
                "category_match": category_match,
                "expected_summary": case["expected_summary"],
                "actual_summary": output["summary"],
                "summary_score": judge_score,
                "summary_judge_reason": judge_reason,
                "latency_seconds": output["latency_seconds"],
                "input_tokens": output["input_tokens"],
                "output_tokens": output["output_tokens"],
                "error": None,
            })
        except Exception as e:
            results.append({
                "case_id": case["id"],
                "difficulty": case.get("expected_difficulty", "normal"),
                "input": case["input"],
                "expected_category": case["expected_category"],
                "actual_category": None,
                "category_match": False,
                "expected_summary": case["expected_summary"],
                "actual_summary": None,
                "summary_score": None,
                "summary_judge_reason": None,
                "latency_seconds": None,
                "input_tokens": None,
                "output_tokens": None,
                "error": str(e),
            })

    total = len(results)
    passed = sum(1 for r in results if r["category_match"])
    pass_rate = passed / total if total else 0.0
    avg_summary_score = _safe_avg([r["summary_score"] for r in results if r["summary_score"] is not None])
    avg_latency = _safe_avg([r["latency_seconds"] for r in results if r["latency_seconds"] is not None])

    run_record = {
        "run_id": run_id,
        "timestamp": timestamp,
        "prompt_version": config.version,
        "model": config.model,
        "total_cases": total,
        "passed": passed,
        "pass_rate": pass_rate,
        "avg_summary_score": avg_summary_score,
        "avg_latency_seconds": avg_latency,
        "results": results,
    }

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    safe_ts = timestamp.replace(":", "-")
    run_file = out_path / f"run_{safe_ts}_{run_id}.json"
    with open(run_file, "w") as f:
        json.dump(run_record, f, indent=2)

    return str(run_file)


def _safe_avg(values):
    return sum(values) / len(values) if values else None
