import time

from data_collection.adapters.base import ModelAdapter
from data_collection import config, storage


INSTRUCTION_TEMPLATE = (
    "Write an IELTS Task 2 essay responding to the following prompt. "
    "Target approximately 250 words (240–260 acceptable). "
    "Output only the essay text, with no preamble or commentary.\n\n"
    "Prompt: {prompt}"
)


def run(adapter: ModelAdapter, prompt_id: str, prompt_text: str) -> dict:
    instruction = INSTRUCTION_TEMPLATE.format(prompt=prompt_text)
    t0 = time.time()
    essay = adapter.generate(instruction, config.TEMPERATURE, config.MAX_TOKENS_ESSAY)
    duration = time.time() - t0

    return {
        "model":           adapter.name,
        "model_version":   adapter.version,
        "condition":       "baseline_a",
        "prompt_id":       prompt_id,
        "prompt_text":     prompt_text,
        "trial_number":    1,
        "essay_text":      essay,
        "essay_word_count": storage.word_count(essay),
        "plan_text":       None,
        "transcript":      None,
        "stop_reason":     None,
        "turns_used":      None,
        "metadata": {
            "duration_seconds": round(duration, 2),
            "errors": [],
        },
    }
