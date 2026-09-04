"""
WRAFT scoring wrapper.

Bypasses the Django ORM entirely. Loads score_prompt.txt directly,
calls the fine-tuned GPT-4o model via OpenAI SDK, and falls back to
gpt-4.1 if the fine-tuned model is unavailable (wrong org key).

WRAFT scale: 0.0–5.0 (not IELTS 0–9).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_JSON_RE = re.compile(r'\{[^{}]*"score"\s*:\s*[\d.]+[^{}]*\}', re.S)

import openai
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from evaluation.config import WRAFT_PROMPT_PATH, WRAFT_SCORE_FALLBACK, WRAFT_SCORE_MODEL
from evaluation.schema import EssayRecord, WraftResult

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

_FALLBACK_CALIBRATION = """

Calibration note: Use the FULL 0–5 scale. Score 5 is exceptional and rare — reserve it only for essays that flawlessly meet every criterion above. Most competent essays that address the topic adequately but have minor weaknesses in organisation, development, or language should score 3–4. Score 4 requires clear organisation AND sufficient development AND mostly accurate language. Score 3 is appropriate when any one of those areas is noticeably weak. Be strict: if an essay is merely adequate, score it 3, not 5."""

_client = openai.OpenAI()
_prompt_template: str | None = None


def _load_prompt() -> str:
    global _prompt_template
    if _prompt_template is None:
        path = Path(WRAFT_PROMPT_PATH)
        if not path.exists():
            raise FileNotFoundError(f"WRAFT prompt not found at {path}")
        _prompt_template = path.read_text(encoding="utf-8")
    return _prompt_template


@_retry
def _call_model(model: str, prompt: str) -> str:
    response = _client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content


def assess(essay: EssayRecord) -> WraftResult:
    template = _load_prompt()
    prompt = template.replace("{essay_prompt}", essay.prompt_text).replace("{essay_text}", essay.essay_text)

    fallback_used = False
    model_used = WRAFT_SCORE_MODEL
    raw = ""

    try:
        raw = _call_model(WRAFT_SCORE_MODEL, prompt)
    except (openai.NotFoundError, openai.AuthenticationError) as exc:
        print(f"[WARN] WRAFT fine-tuned model unavailable ({exc}), falling back to {WRAFT_SCORE_FALLBACK}", file=sys.stderr)
        fallback_used = True
        model_used = WRAFT_SCORE_FALLBACK
        raw = _call_model(WRAFT_SCORE_FALLBACK, prompt + _FALLBACK_CALIBRATION)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_RE.search(raw)
        if m:
            data = json.loads(m.group())
        else:
            raise ValueError(f"WRAFT returned non-JSON for {essay.essay_id}: {raw[:200]}")

    score = float(data["score"])
    if not (0.0 <= score <= 5.0):
        raise ValueError(f"WRAFT score {score} out of range 0–5 for essay {essay.essay_id}")

    return WraftResult(
        essay_id=essay.essay_id,
        score=score,
        model_used=model_used,
        fallback_used=fallback_used,
        raw_response=raw,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
