import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from evaluation.config import JUDGE_CLAUDE_MODEL, JUDGE_MAX_TOKENS, JUDGE_TEMPERATURE
from evaluation.judges.base import JUDGE_PROMPT, JudgeAdapter, _parse_response
from evaluation.schema import EssayRecord, JudgeScore

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

_client = anthropic.Anthropic()


def _base_kwargs(version: str) -> dict:
    """Claude 4+ models don't accept temperature."""
    kwargs = {"max_tokens": JUDGE_MAX_TOKENS}
    if not (version.startswith("claude-opus-4") or version.startswith("claude-sonnet-4")):
        kwargs["temperature"] = JUDGE_TEMPERATURE
    return kwargs


class ClaudeJudge(JudgeAdapter):
    name = "claude"
    version = JUDGE_CLAUDE_MODEL

    @_retry
    def score(self, essay: EssayRecord) -> JudgeScore:
        prompt = JUDGE_PROMPT.format(prompt=essay.prompt_text, essay=essay.essay_text)
        kwargs = _base_kwargs(self.version)
        response = _client.messages.create(
            model=self.version,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        raw = response.content[0].text
        result = _parse_response(raw, essay.essay_id, self.name, self.version)
        if result.metadata and "parse_error" in result.metadata:
            print(f"[WARN] Claude judge parse error for {essay.essay_id}: {result.metadata['parse_error']}", file=sys.stderr)
        return result
