import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from data_collection.adapters.base import ModelAdapter
from data_collection import config

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


class OpenAIAdapter(ModelAdapter):
    name = "gpt"
    version = config.MODEL_VERSIONS["gpt"]

    def __init__(self):
        self._client = openai.OpenAI()

    @_retry
    def generate(self, prompt: str, temperature: float, max_tokens: int) -> str:
        response = self._client.chat.completions.create(
            model=self.version,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    @_retry
    def chat(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        response = self._client.chat.completions.create(
            model=self.version,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        return response.choices[0].message.content
