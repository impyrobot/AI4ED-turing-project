import re
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from data_collection.adapters.base import ModelAdapter

OLLAMA_BASE_URL = "http://localhost:11434/v1"

_TRANSIENT = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
)

_retry = retry(
    retry=retry_if_exception_type(_TRANSIENT),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)

_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.S)


def _strip_thinking(text: str) -> str:
    """Remove DeepSeek-R1 <think>...</think> blocks from output."""
    return _THINK_RE.sub("", text).strip()


class LocalAdapter(ModelAdapter):
    """
    Adapter for locally-hosted models via Ollama's OpenAI-compatible API.
    Handles DeepSeek-R1 thinking-token stripping automatically.
    """

    def __init__(self, short_name: str, ollama_model: str):
        self.name = short_name
        self.version = ollama_model
        self._strip = short_name == "deepseek"
        self._client = openai.OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",  # Ollama ignores the key but the SDK requires one
        )

    def _clean(self, text: str) -> str:
        return _strip_thinking(text) if self._strip else text

    @_retry
    def generate(self, prompt: str, temperature: float, max_tokens: int) -> str:
        response = self._client.chat.completions.create(
            model=self.version,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._clean(response.choices[0].message.content)

    @_retry
    def chat(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        response = self._client.chat.completions.create(
            model=self.version,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        return self._clean(response.choices[0].message.content)
