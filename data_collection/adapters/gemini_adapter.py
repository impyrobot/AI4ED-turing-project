import os
import google.genai as genai
import google.genai.types as genai_types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from data_collection.adapters.base import ModelAdapter
from data_collection import config

_TRANSIENT = (
    Exception,  # google-genai wraps errors; filter by message in retry check below
)


def _is_transient(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "rate limit", "timeout", "503", "unavailable"))


_retry = retry(
    retry=_is_transient,
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)


class GeminiAdapter(ModelAdapter):
    name = "gemini"
    version = config.MODEL_VERSIONS["gemini"]

    def __init__(self):
        self._client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    def _gen_config(self, temperature: float, max_tokens: int) -> genai_types.GenerateContentConfig:
        # Disable thinking — flash uses thinking tokens by default which exhaust the budget
        return genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )

    @_retry
    def generate(self, prompt: str, temperature: float, max_tokens: int) -> str:
        response = self._client.models.generate_content(
            model=self.version,
            contents=prompt,
            config=self._gen_config(temperature, max_tokens),
        )
        return response.text

    @_retry
    def chat(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        # Map OpenAI-style roles to Gemini's user/model convention
        history = []
        last_user_content = None
        for m in messages:
            role = "model" if m["role"] == "assistant" else m["role"]
            if role == "system":
                # Prepend system message as first user turn
                history.append(genai_types.Content(role="user", parts=[genai_types.Part(text=m["content"])]))
                history.append(genai_types.Content(role="model", parts=[genai_types.Part(text="Understood.")]))
            else:
                history.append(genai_types.Content(role=role, parts=[genai_types.Part(text=m["content"])]))

        # The last user message drives the request; separate it from history
        if history and history[-1].role == "user":
            last_msg = history.pop()
            last_user_content = last_msg.parts[0].text
        else:
            last_user_content = ""

        chat_session = self._client.chats.create(
            model=self.version,
            config=self._gen_config(temperature, max_tokens),
            history=history if history else None,
        )
        response = chat_session.send_message(last_user_content)
        return response.text
