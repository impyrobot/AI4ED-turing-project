import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from data_collection.adapters.base import ModelAdapter
from data_collection import config

_TRANSIENT = (
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
)

_retry = retry(
    retry=retry_if_exception_type(_TRANSIENT),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)


class AnthropicAdapter(ModelAdapter):
    name = "claude"
    version = config.MODEL_VERSIONS["claude"]

    def __init__(self):
        self._client = anthropic.Anthropic()

    def _base_kwargs(self, temperature: float, max_tokens: int) -> dict:
        # temperature is deprecated for Claude 4+ models
        kwargs = {"model": self.version, "max_tokens": max_tokens}
        if not self.version.startswith("claude-opus-4") and not self.version.startswith("claude-sonnet-4"):
            kwargs["temperature"] = temperature
        return kwargs

    @_retry
    def generate(self, prompt: str, temperature: float, max_tokens: int) -> str:
        response = self._client.messages.create(
            **self._base_kwargs(temperature, max_tokens),
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    @_retry
    def chat(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        turns = [m for m in messages if m["role"] != "system"]
        kwargs = self._base_kwargs(temperature, max_tokens)
        kwargs["messages"] = turns
        if system:
            kwargs["system"] = system
        response = self._client.messages.create(**kwargs)
        return response.content[0].text
