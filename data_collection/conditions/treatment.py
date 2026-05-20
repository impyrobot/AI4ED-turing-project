import sys
import time
from pathlib import Path

from data_collection.adapters.base import ModelAdapter
from data_collection import config, storage
from data_collection import planning_module_client as pmc

STUDENT_PERSONA_TEMPLATE = (
    "You are a university student preparing an IELTS Task 2 essay on the following prompt:\n\n"
    "{prompt}\n\n"
    "You will discuss it with several AI agents who will help you plan. "
    "Engage genuinely — ask questions, respond thoughtfully to challenges, and refine your ideas "
    "based on what they say. When you feel you have a complete plan covering your thesis, main "
    "arguments, and structure, end your message with the exact phrase: PLAN COMPLETE"
)

ESSAY_WRITING_TEMPLATE = (
    "You are writing an IELTS Task 2 academic essay. Follow the plan below precisely.\n\n"
    "Rules:\n"
    "- Your introduction must use the thesis stance stated in the plan, paraphrased from the prompt.\n"
    "- Each body paragraph must develop the specific argument and use the specific evidence listed in the plan. "
    "Do not invent new arguments or examples not mentioned in the plan.\n"
    "- Your conclusion must restate your position and address any nuances noted in the plan.\n"
    "- Target 250 words (240–260 acceptable).\n"
    "- Output only the essay text, no preamble, no commentary.\n\n"
    "Prompt: {prompt}\n\nPlan:\n{plan}"
)


def run(adapter: ModelAdapter, prompt_id: str, prompt_text: str) -> dict:
    t0 = time.time()
    transcript = []
    errors = []

    # --- Phase 1: planning conversation ---
    system_prompt = STUDENT_PERSONA_TEMPLATE.format(prompt=prompt_text)

    try:
        session_id, agent_prompt = pmc.start_session(prompt_text)
    except Exception as e:
        return _error_record(adapter, prompt_id, prompt_text, str(e), t0)

    # Seed the model's message history with the student persona
    history = [{"role": "system", "content": system_prompt}]

    stop_reason = "MAX_TURNS"
    turns_used = 0

    for turn in range(config.MAX_PLANNING_TURNS):
        if agent_prompt is None:
            # Graph reached END on its own
            stop_reason = "GRAPH_END"
            break

        # Log agent turn
        transcript.append({"turn": len(transcript), "role": "agent", "content": agent_prompt})

        # Ask the model (as student) to respond
        history.append({"role": "user", "content": agent_prompt})
        try:
            student_reply = adapter.chat(history, config.TEMPERATURE, config.MAX_TOKENS_PLAN)
        except Exception as e:
            errors.append(f"turn {turn} adapter error: {e}")
            stop_reason = "ERROR"
            break

        history.append({"role": "assistant", "content": student_reply})
        transcript.append({"turn": len(transcript), "role": "student", "content": student_reply})
        turns_used = turn + 1

        # Check soft stop
        if config.STOP_TOKEN in student_reply:
            stop_reason = "PLAN_COMPLETE"
            # Still send the message so the planning module logs it
            try:
                agent_prompt = pmc.send_user_message(session_id, student_reply)
            except Exception:
                pass
            break

        # Send to planning module and get next prompt
        try:
            agent_prompt = pmc.send_user_message(session_id, student_reply)
        except Exception as e:
            errors.append(f"turn {turn} planning module error: {e}")
            stop_reason = "ERROR"
            break

    # --- Retrieve plan ---
    plan_text = ""
    try:
        plan_text = pmc.get_final_plan(session_id)
    except Exception as e:
        errors.append(f"get_final_plan error: {e}")
    finally:
        pmc.end_session(session_id)

    # --- Phase 2: essay writing (fresh context) ---
    essay_text = ""
    if plan_text:
        writing_prompt = ESSAY_WRITING_TEMPLATE.format(prompt=prompt_text, plan=plan_text)
    else:
        # Fallback: use transcript summary as plan
        writing_prompt = ESSAY_WRITING_TEMPLATE.format(
            prompt=prompt_text,
            plan="[plan unavailable — write from the IELTS prompt directly]",
        )
        errors.append("plan_text empty; essay written without plan")

    try:
        essay_text = adapter.generate(writing_prompt, config.ESSAY_TEMPERATURE, config.MAX_TOKENS_ESSAY)
    except Exception as e:
        errors.append(f"essay generation error: {e}")

    duration = time.time() - t0

    return {
        "model":            adapter.name,
        "model_version":    adapter.version,
        "condition":        "treatment",
        "prompt_id":        prompt_id,
        "prompt_text":      prompt_text,
        "trial_number":     1,
        "essay_text":       essay_text,
        "essay_word_count": storage.word_count(essay_text),
        "plan_text":        plan_text,
        "transcript":       transcript,
        "stop_reason":      stop_reason,
        "turns_used":       turns_used,
        "metadata": {
            "duration_seconds": round(duration, 2),
            "errors":           errors,
        },
    }


def _error_record(adapter, prompt_id, prompt_text, error_msg, t0):
    return {
        "model":            adapter.name,
        "model_version":    adapter.version,
        "condition":        "treatment",
        "prompt_id":        prompt_id,
        "prompt_text":      prompt_text,
        "trial_number":     1,
        "essay_text":       "",
        "essay_word_count": 0,
        "plan_text":        "",
        "transcript":       [],
        "stop_reason":      "ERROR",
        "turns_used":       0,
        "metadata": {
            "duration_seconds": round(time.time() - t0, 2),
            "errors":           [error_msg],
        },
    }
