"""Per-essay orchestrator: runs WRAFT + selected LLM judges."""
import json
import sys
from pathlib import Path

from evaluation import config
from evaluation.judges.base import JudgeAdapter
from evaluation.schema import EssayRecord
from evaluation import wraft_client

# A judge never scores essays from its own model family.
JUDGE_MAP: dict[str, list[str]] = {
    "claude":   ["gpt"],
    "gpt":      ["claude"],
    "_default": ["claude", "gpt"],
}


def _selected_judges(essay: EssayRecord, all_judges: dict[str, JudgeAdapter]) -> list[JudgeAdapter]:
    key = essay.writer_id if essay.writer_id in JUDGE_MAP else "_default"
    names = JUDGE_MAP[key]
    return [all_judges[n] for n in names if n in all_judges]


def evaluate(essay: EssayRecord, all_judges: dict[str, JudgeAdapter], force: bool = False) -> dict:
    """Run WRAFT + selected judges for one essay. Returns a status dict."""
    evals_dir = Path(config.EVALUATIONS_DIR)
    evals_dir.mkdir(parents=True, exist_ok=True)

    results: dict = {"essay_id": essay.essay_id, "wraft": None, "judges": {}}

    # --- WRAFT ---
    wraft_path = evals_dir / f"wraft_{essay.essay_id}.json"
    if force or not wraft_path.exists():
        try:
            result = wraft_client.assess(essay)
            wraft_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            results["wraft"] = "ok"
            print(f"[OK]   WRAFT  {essay.essay_id}  score={result.score}", file=sys.stderr)
        except Exception as exc:
            results["wraft"] = f"error: {exc}"
            print(f"[ERR]  WRAFT  {essay.essay_id}: {exc}", file=sys.stderr)
    else:
        results["wraft"] = "skipped"

    # --- LLM judges ---
    judges = _selected_judges(essay, all_judges)
    for judge in judges:
        judge_path = evals_dir / f"judge_{judge.name}_{essay.essay_id}.json"
        if force or not judge_path.exists():
            try:
                score = judge.score(essay)
                judge_path.write_text(score.model_dump_json(indent=2), encoding="utf-8")
                results["judges"][judge.name] = "ok"
                print(f"[OK]   judge/{judge.name}  {essay.essay_id}  overall={score.overall_band}", file=sys.stderr)
            except Exception as exc:
                results["judges"][judge.name] = f"error: {exc}"
                print(f"[ERR]  judge/{judge.name}  {essay.essay_id}: {exc}", file=sys.stderr)
        else:
            results["judges"][judge.name] = "skipped"

    return results
