"""Basic schema validation tests."""
import pytest
from pydantic import ValidationError

from evaluation.schema import BandScore, EssayRecord, JudgeScore, WraftResult


def _base_essay(**overrides):
    data = dict(
        essay_id="test_001",
        writer_type="ai",
        writer_id="claude",
        condition="no_plan",
        prompt_id="p5",
        prompt_text="Some prompt",
        essay_text="Some essay text.",
        essay_word_count=3,
        source_run="test",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    data.update(overrides)
    return data


def test_essay_record_valid():
    EssayRecord(**_base_essay())


def test_essay_record_invalid_condition():
    with pytest.raises(ValidationError):
        EssayRecord(**_base_essay(condition="baseline_a"))


def test_band_score_valid():
    BandScore(band=6.5, justification="good")


def test_band_score_out_of_range():
    with pytest.raises(ValidationError):
        BandScore(band=9.5, justification="bad")


def test_band_score_non_half():
    with pytest.raises(ValidationError):
        BandScore(band=6.3, justification="bad")
