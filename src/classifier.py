import json
import time
import yaml

from .llm_client import get_client
from .schemas import ClassificationResult, PromptConfig


def load_prompt_config(path: str) -> PromptConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return PromptConfig(**raw)


def classify_email(email_text: str, config: PromptConfig) -> dict:
    """Runs one email through the LLM feature and returns a normalized result.

    This is the single function the eval pipeline calls for every test case.
    Everything about *how* it classifies is controlled by `config`, which is
    loaded from a versioned YAML file — never hardcode prompt text here.
    """
    client = get_client()

    messages = [{"role": "system", "content": config.system_prompt}]
    for example in config.few_shot_examples:
        messages.append({"role": "user", "content": example["input"]})
        messages.append({"role": "assistant", "content": json.dumps(example["output"])})
    messages.append({"role": "user", "content": email_text})

    start = time.time()
    response = client.chat.completions.create(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        response_format={"type": "json_object"},
    )
    latency = time.time() - start

    raw_content = response.choices[0].message.content
    parsed = json.loads(raw_content)
    result = ClassificationResult(**parsed)

    usage = response.usage
    return {
        "category": result.category,
        "summary": result.summary,
        "latency_seconds": latency,
        "input_tokens": usage.prompt_tokens if usage else None,
        "output_tokens": usage.completion_tokens if usage else None,
        "raw_output": raw_content,
    }
