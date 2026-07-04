from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Any

Category = Literal["billing", "technical", "account", "general"]


class ClassificationResult(BaseModel):
    """The structured output we expect back from the LLM feature under test."""
    category: Category
    summary: str = Field(..., description="One-sentence summary of the email")


class PromptConfig(BaseModel):
    """A versioned prompt definition, loaded from /prompts/*.yaml.

    This is the 'code' the eval pipeline runs CI against — every time this
    file changes, the eval suite should run.
    """
    version: str
    model: str
    system_prompt: str
    few_shot_examples: List[Dict[str, Any]] = []
    temperature: float = 0.0
    max_tokens: int = 300
