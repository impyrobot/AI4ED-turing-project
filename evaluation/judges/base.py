import json
import math
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from evaluation.schema import BandScore, EssayRecord, JudgeScore

JUDGE_PROMPT = """\
You are an experienced IELTS examiner. Score the following essay against the official IELTS Task 2 rubric. Output strictly JSON with band scores (0.0–9.0, half-bands allowed) and a one-sentence justification for each dimension.

Prompt: {prompt}

Essay:
{essay}

Required JSON shape (no extra fields, no preamble):
{{
  "task_response":      {{"band": 0.0, "justification": "..."}},
  "coherence_cohesion": {{"band": 0.0, "justification": "..."}},
  "lexical_resource":   {{"band": 0.0, "justification": "..."}},
  "grammatical_range":  {{"band": 0.0, "justification": "..."}},
  "overall_band": 0.0
}}"""

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)


def _parse_response(raw: str, essay_id: str, judge_model: str, judge_version: str) -> JudgeScore:
    """Parse judge JSON response; returns NaN score on failure instead of raising."""
    text = raw.strip()
    m = _FENCE_RE.search(text)
    if m:
        text = m.group(1)
    try:
        data = json.loads(text)
        return JudgeScore(
            essay_id=essay_id,
            judge_model=judge_model,
            judge_version=judge_version,
            task_response=BandScore(**data["task_response"]),
            coherence_cohesion=BandScore(**data["coherence_cohesion"]),
            lexical_resource=BandScore(**data["lexical_resource"]),
            grammatical_range=BandScore(**data["grammatical_range"]),
            overall_band=float(data["overall_band"]),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        return JudgeScore(
            essay_id=essay_id,
            judge_model=judge_model,
            judge_version=judge_version,
            task_response=BandScore(band=0.0, justification="parse error"),
            coherence_cohesion=BandScore(band=0.0, justification="parse error"),
            lexical_resource=BandScore(band=0.0, justification="parse error"),
            grammatical_range=BandScore(band=0.0, justification="parse error"),
            overall_band=float("nan"),
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={"parse_error": str(exc), "raw_response": raw},
        )


class JudgeAdapter(ABC):
    name: str
    version: str

    @abstractmethod
    def score(self, essay: EssayRecord) -> JudgeScore:
        """Score one essay against IELTS Task 2 rubric."""
