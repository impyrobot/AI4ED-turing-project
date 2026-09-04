"""CLI for ingesting human-written essays into the unified dataset."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from evaluation import config
from evaluation.schema import EssayRecord
from data_collection.prompts import PROMPTS


def _word_count(text: str) -> int:
    return len(text.split())


def main():
    parser = argparse.ArgumentParser(description="Ingest a human essay into data/essays/")
    parser.add_argument("--participant",      required=True, help="Participant ID, e.g. human_001")
    parser.add_argument("--prompt",           required=True, help="Prompt ID, e.g. p5")
    parser.add_argument("--essay-file",       required=True, help="Path to essay text file")
    parser.add_argument("--condition",        required=True,
                        choices=["no_plan", "naive_plan", "module_plan"])
    parser.add_argument("--plan-file",        help="Path to plan text file (mode 2)")
    parser.add_argument("--transcript-file",  help="Path to transcript JSON file (mode 2)")
    args = parser.parse_args()

    essay_path = Path(args.essay_file)
    if not essay_path.exists():
        print(f"[ERR] Essay file not found: {essay_path}", file=sys.stderr)
        sys.exit(1)

    essay_text = essay_path.read_text(encoding="utf-8").strip()
    if not essay_text:
        print("[ERR] Essay file is empty", file=sys.stderr)
        sys.exit(1)

    if args.prompt not in PROMPTS:
        print(f"[ERR] Unknown prompt ID: {args.prompt}", file=sys.stderr)
        sys.exit(1)
    prompt_text = PROMPTS[args.prompt]

    plan_text = None
    if args.plan_file:
        plan_text = Path(args.plan_file).read_text(encoding="utf-8").strip()

    transcript = None
    if args.transcript_file:
        transcript = json.loads(Path(args.transcript_file).read_text(encoding="utf-8"))

    essay_id = f"human_{args.participant}_{args.prompt}_{args.condition}"
    source_run = f"human_intake_{datetime.now(timezone.utc).strftime('%Y_%m')}"

    record = EssayRecord(
        essay_id=essay_id,
        writer_type="human",
        writer_id=args.participant,
        writer_version=None,
        condition=args.condition,
        prompt_id=args.prompt,
        prompt_text=prompt_text,
        essay_text=essay_text,
        essay_word_count=_word_count(essay_text),
        plan_text=plan_text,
        transcript=transcript,
        source_run=source_run,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    dst_dir = Path(config.ESSAYS_DIR)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{essay_id}.json"
    dst.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    print(f"Ingested: {essay_id}")
    print(f"  Word count: {record.essay_word_count}")
    print(f"  File: {dst}")


if __name__ == "__main__":
    main()
