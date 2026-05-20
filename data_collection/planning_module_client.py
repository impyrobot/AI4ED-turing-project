"""
Thin wrapper around bin/MultiAgentSystem — mirrors the session pattern in app.py.

Session lifecycle:
  sid = start_session(prompt_text)   -> runs graph to first interrupt; returns session_id
  resp = send_user_message(sid, msg) -> resumes; returns next interrupt prompt or None (done)
  plan = get_final_plan(sid)         -> extracts final plan from checkpointed state
  end_session(sid)                   -> drops session from memory
"""
import sys
import uuid
from pathlib import Path
from typing import Any

# Make the planning module importable without installing it as a package
sys.path.insert(0, str(Path(__file__).parents[1]))

from bin.MultiAgentSystem.agents import create_all_agents
from bin.MultiAgentSystem.ochestrator import PlanningModule
from bin.MultiAgentSystem.state_schema import State

# In-memory session store: thread_id -> {mas, state}
_SESSIONS: dict[str, dict[str, Any]] = {}


def _make_initial_state(thread_id: str, essay_topic: str) -> State:
    return {
        "idea_board": "",
        "structures": [],
        "subject": "IELTS Essay Planning",
        "turn_user_messages": [],
        "latest_user_message": essay_topic,
        "facilitator_reply": "",
        "idea_generator_reply": "",
        "subject_specialist_reply": "",
        "critic_reply": "",
        "structuring_coach_reply": "",
        "argument_flow_reply": "",
        "facilitation_done": False,
        "ideation_iteration": 1,
        "critic_iteration": 1,
        "structuring_iteration": 1,
        "thread_id": thread_id,
        "essay_topic": essay_topic,
        "route": "none",
        "criticising_done": False,
        "structuring_done": False,
        "final_message": "",
        "final_file_name": "",
        "final_file_mime_type": "",
    }


def _run_until_interrupt(mas: PlanningModule, state: State, thread_id: str, resume_text: str | None) -> str | None:
    """Drive the graph until the next interrupt. Returns the interrupt prompt, or None if the graph reached END."""
    for node, key, value in mas.stream_updates(state, thread_id=thread_id, resume_text=resume_text):
        if node == "__interrupt__":
            return str(value)
    return None


def start_session(prompt_text: str) -> tuple[str, str | None]:
    """
    Initialise a planning session for the given IELTS prompt.
    Returns (session_id, first_agent_prompt).
    first_agent_prompt is None if the graph completed without interrupting (unusual).
    """
    thread_id = str(uuid.uuid4())
    state = _make_initial_state(thread_id, prompt_text)

    (
        facilitator_ideation, idea_generator, subject_specialist,
        idea_structurer, critic, router, facilitator_critic,
        structuring_coach, argument_flow, facilitator_structuring,
        structuring_router, structuring_idea_structurer,
    ) = create_all_agents(state)

    mas = PlanningModule(
        idea_generator_agent=idea_generator,
        facilitator_agent_ideation=facilitator_ideation,
        idea_structurer_agent=idea_structurer,
        subject_specialist_agent=subject_specialist,
        critic_agent=critic,
        router_agent=router,
        facilitator_agent_critic=facilitator_critic,
        structuring_coach_agent=structuring_coach,
        argument_flow_agent=argument_flow,
        facilitator_agent_structuring=facilitator_structuring,
        structuring_router_agent=structuring_router,
        structuring_idea_structurer_agent=structuring_idea_structurer,
    )

    _SESSIONS[thread_id] = {"mas": mas, "state": state}
    first_prompt = _run_until_interrupt(mas, state, thread_id, resume_text=None)
    return thread_id, first_prompt


def send_user_message(session_id: str, message: str) -> str | None:
    """
    Send a student message and resume the graph.
    Returns the next agent interrupt prompt, or None when the graph has finished.
    """
    sess = _SESSIONS.get(session_id)
    if not sess:
        raise KeyError(f"Unknown session_id: {session_id}")
    mas: PlanningModule = sess["mas"]
    state: State = sess["state"]
    return _run_until_interrupt(mas, state, session_id, resume_text=message)


def _collect_values(snapshot) -> dict:
    """
    Merge values from the parent snapshot and all live subgraph tasks.
    Subgraph state is only visible via task.state while the subgraph is still running
    (it hasn't been committed to the parent checkpoint yet).
    """
    merged = dict(snapshot.values)
    for task in getattr(snapshot, "tasks", []):
        sub = getattr(task, "state", None)
        if sub and hasattr(sub, "values"):
            for k, v in sub.values.items():
                if v and not merged.get(k):
                    merged[k] = v
    return merged


def get_final_plan(session_id: str) -> str:
    """
    Extract the best available plan from the checkpointed graph state.
    Priority: final_message > structures > idea_board > agent reply fields.
    The graph may not have reached END when this is called (student said PLAN COMPLETE
    early), so we harvest content from both the parent and any live subgraph state.
    """
    sess = _SESSIONS.get(session_id)
    if not sess:
        raise KeyError(f"Unknown session_id: {session_id}")
    mas: PlanningModule = sess["mas"]
    snapshot = mas.graph.get_state(
        {"configurable": {"thread_id": session_id}},
        subgraphs=True,
    )
    v = _collect_values(snapshot)

    if v.get("final_message"):
        return v["final_message"]
    structures = v.get("structures", [])
    if structures:
        return "\n\n".join(structures)
    if v.get("idea_board"):
        return v["idea_board"]

    # Fallback: collect non-empty agent reply fields as a partial summary
    reply_fields = [
        "structuring_coach_reply", "argument_flow_reply",
        "critic_reply", "idea_generator_reply",
        "subject_specialist_reply", "facilitator_reply",
    ]
    parts = []
    for field in reply_fields:
        content = v.get(field, "")
        if content and content.strip():
            parts.append(f"[{field}]\n{content.strip()}")
    return "\n\n".join(parts) if parts else ""


def end_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
