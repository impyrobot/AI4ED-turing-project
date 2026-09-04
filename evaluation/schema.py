from typing import Literal, Optional
from pydantic import BaseModel, field_validator


class EssayRecord(BaseModel):
    essay_id: str
    writer_type: Literal["ai", "human"]
    writer_id: str
    writer_version: Optional[str] = None
    condition: Literal["no_plan", "naive_plan", "module_plan"]
    prompt_id: str
    prompt_text: str
    essay_text: str
    essay_word_count: int
    plan_text: Optional[str] = None
    transcript: Optional[list[dict]] = None
    source_run: str
    timestamp: str


class BandScore(BaseModel):
    band: float
    justification: str

    @field_validator("band")
    @classmethod
    def valid_band(cls, v: float) -> float:
        if not (0.0 <= v <= 9.0):
            raise ValueError(f"Band score {v} out of range 0–9")
        if (v * 2) != int(v * 2):
            raise ValueError(f"Band score {v} must be in half-band increments")
        return v


class JudgeScore(BaseModel):
    essay_id: str
    judge_model: str
    judge_version: str
    task_response: BandScore
    coherence_cohesion: BandScore
    lexical_resource: BandScore
    grammatical_range: BandScore
    overall_band: float
    timestamp: str
    metadata: Optional[dict] = None


class WraftResult(BaseModel):
    essay_id: str
    score: float          # 0.0–5.0
    model_used: str
    fallback_used: bool
    raw_response: str
    timestamp: str
