import re
import time

from data_collection.adapters.base import ModelAdapter
from data_collection import config, storage


INSTRUCTION_TEMPLATE = (
    "You will write an IELTS Task 2 essay responding to the following prompt. "
    "First produce a brief plan (thesis, 2–3 main points, conclusion direction). "
    "Then write the full essay of approximately 250 words (240–260 acceptable).\n\n"
    "Format your response exactly as:\n"
    "PLAN:\n[plan]\n\nESSAY:\n[essay]\n\n"
    "Prompt: {prompt}"
)


def _parse(raw: str) -> tuple[str | None, str | None]:
    """Return (plan_text, essay_text). None for a section if not found."""
    plan = essay = None

    # Case-insensitive split on PLAN: and ESSAY: markers
    plan_match  = re.search(r"(?i)^PLAN:\s*\n(.*?)(?=\n\s*ESSAY:)", raw, re.S | re.M)
    essay_match = re.search(r"(?i)^ESSAY:\s*\n(.*)", raw, re.S | re.M)

    if plan_match:
        plan = plan_match.group(1).strip()
    if essay_match:
        essay = essay_match.group(1).strip()

    return plan, essay


def run(adapter: ModelAdapter, prompt_id: str, prompt_text: str) -> dict:
    instruction = INSTRUCTION_TEMPLATE.format(prompt=prompt_text)
    t0 = time.time()
    raw = adapter.generate(instruction, config.TEMPERATURE, config.MAX_TOKENS_ESSAY + config.MAX_TOKENS_PLAN)
    duration = time.time() - t0

    plan, essay = _parse(raw)
    parse_failed = plan is None or essay is None

    return {
        "model":            adapter.name,
        "model_version":    adapter.version,
        "condition":        "baseline_b",
        "prompt_id":        prompt_id,
        "prompt_text":      prompt_text,
        "trial_number":     1,
        "essay_text":       essay or "",
        "essay_word_count": storage.word_count(essay or ""),
        "plan_text":        plan,
        "transcript":       None,
        "stop_reason":      None,
        "turns_used":       None,
        "metadata": {
            "duration_seconds": round(duration, 2),
            "errors":           ["parse_failed: sections not found in response"] if parse_failed else [],
            "raw_response":     raw if parse_failed else None,
        },
    }
