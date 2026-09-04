"""One-off migration: converts Phase 1a essay JSONs to the unified EssayRecord schema."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from evaluation import config
from evaluation.schema import EssayRecord

CONDITION_MAP = {
    "baseline_a": "no_plan",
    "baseline_b": "naive_plan",
    "treatment":  "module_plan",
}


def _essay_id(record: dict) -> str:
    writer = record["model"]
    prompt = record["prompt_id"]
    cond   = CONDITION_MAP[record["condition"]]
    trial  = record.get("trial_number", 1)
    return f"ai_{writer}_{prompt}_{cond}_t{trial}"


def migrate_one(src: Path, dst_dir: Path) -> str:
    """Migrate a single Phase 1a JSON. Returns essay_id."""
    raw = json.loads(src.read_text(encoding="utf-8"))

    essay_id = _essay_id(raw)
    dst = dst_dir / f"{essay_id}.json"

    if dst.exists():
        return essay_id  # idempotent

    unified = EssayRecord(
        essay_id=essay_id,
        writer_type="ai",
        writer_id=raw["model"],
        writer_version=raw.get("model_version"),
        condition=CONDITION_MAP[raw["condition"]],
        prompt_id=raw["prompt_id"],
        prompt_text=raw["prompt_text"],
        essay_text=raw["essay_text"],
        essay_word_count=raw["essay_word_count"],
        plan_text=raw.get("plan_text"),
        transcript=raw.get("transcript"),
        source_run="phase1a",
        timestamp=raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
    )
    dst.write_text(unified.model_dump_json(indent=2), encoding="utf-8")
    return essay_id


def migrate_all() -> list[str]:
    src_dir = Path(config.PHASE1A_DIR)
    dst_dir = Path(config.ESSAYS_DIR)
    dst_dir.mkdir(parents=True, exist_ok=True)

    if not src_dir.exists():
        print(f"[ERR] Phase 1a directory not found: {src_dir}", file=sys.stderr)
        return []

    sources = sorted(src_dir.glob("*.json"))
    if not sources:
        print(f"[WARN] No JSON files found in {src_dir}", file=sys.stderr)
        return []

    migrated: list[str] = []
    errors = 0
    for src in sources:
        try:
            eid = migrate_one(src, dst_dir)
            migrated.append(eid)
            print(f"[OK]   {eid}", file=sys.stderr)
        except Exception as exc:
            errors += 1
            print(f"[ERR]  {src.name}: {exc}", file=sys.stderr)

    print(f"\nMigration: {len(migrated)} essays, {errors} errors", file=sys.stderr)
    return migrated


if __name__ == "__main__":
    migrate_all()
