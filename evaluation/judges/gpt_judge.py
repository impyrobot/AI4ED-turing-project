import sys
from datetime import datetime, timezone

import openai
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from evaluation.config import JUDGE_GPT_MODEL, JUDGE_MAX_TOKENS, JUDGE_TEMPERATURE
from evaluation.judges.base import JUDGE_PROMPT, JudgeAdapter, _parse_response
from evaluation.schema import EssayRecord, JudgeScore

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

_client = openai.OpenAI()


class GPTJudge(JudgeAdapter):
    name = "gpt"
    version = JUDGE_GPT_MODEL

    @_retry
    def score(self, essay: EssayRecord) -> JudgeScore:
        prompt = JUDGE_PROMPT.format(prompt=essay.prompt_text, essay=essay.essay_text)
        response = _client.chat.completions.create(
            model=self.version,
            messages=[{"role": "user", "content": prompt}],
            temperature=JUDGE_TEMPERATURE,
            max_tokens=JUDGE_MAX_TOKENS,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = _parse_response(raw, essay.essay_id, self.name, self.version)
        if result.metadata and "parse_error" in result.metadata:
            print(f"[WARN] GPT judge parse error for {essay.essay_id}: {result.metadata['parse_error']}", file=sys.stderr)
        return result
