import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()

_client = None


def get_client() -> Groq:
    """Lazily construct a singleton Groq client.

    Kept as its own module so swapping providers later (OpenAI, Anthropic)
    only means editing this one file and classifier.py's call signature.
    """
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Copy .env.example to .env and fill it in, "
                "or export it in your shell / CI secrets."
            )
        _client = Groq(api_key=api_key)
    return _client
