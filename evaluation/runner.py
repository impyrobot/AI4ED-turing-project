"""Batch orchestrator for the Phase 2 evaluation pipeline."""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[1] / ".env")

from evaluation import config


def cmd_migrate():
    from evaluation.migrate_phase1a import migrate_all
    migrate_all()


def cmd_evaluate(essay_id_filter=None, writer_filter=None, force=False):
    from evaluation.schema import EssayRecord
    from evaluation.judges.claude_judge import ClaudeJudge
    from evaluation.judges.gpt_judge import GPTJudge
    from evaluation.evaluator import evaluate

    all_judges = {"claude": ClaudeJudge(), "gpt": GPTJudge()}
    essays_dir = Path(config.ESSAYS_DIR)

    if not essays_dir.exists():
        print("[ERR] data/essays/ not found — run --migrate first", file=sys.stderr)
        sys.exit(1)

    paths = sorted(essays_dir.glob("*.json"))
    if not paths:
        print("[WARN] No essays found in data/essays/", file=sys.stderr)
        return

    ok = errors = 0
    for p in paths:
        essay = EssayRecord.model_validate_json(p.read_text(encoding="utf-8"))
        if essay_id_filter and essay.essay_id != essay_id_filter:
            continue
        if writer_filter and essay.writer_id != writer_filter:
            continue
        result = evaluate(essay, all_judges, force=force)
        if any(str(v).startswith("error") for v in [result["wraft"], *result["judges"].values()]):
            errors += 1
        else:
            ok += 1

    print(f"\nEvaluation: {ok} ok, {errors} with errors", file=sys.stderr)


def cmd_aggregate():
    from evaluation.aggregate import build_summary
    df = build_summary()
    print(df[["essay_id", "wraft_overall", "judge_mean_overall"]].to_string())


def main():
    parser = argparse.ArgumentParser(description="Phase 2 evaluation pipeline")
    parser.add_argument("--migrate",   action="store_true", help="Migrate Phase 1a essays")
    parser.add_argument("--evaluate",  action="store_true", help="Run WRAFT + judge scoring")
    parser.add_argument("--aggregate", action="store_true", help="Rebuild summary.csv")
    parser.add_argument("--all",       action="store_true", help="migrate + evaluate + aggregate")
    parser.add_argument("--essay-id",  help="Limit to one essay ID")
    parser.add_argument("--writer",    help="Limit to one writer ID")
    parser.add_argument("--force",     action="store_true", help="Re-run even if output exists")
    args = parser.parse_args()

    if not any([args.migrate, args.evaluate, args.aggregate, args.all]):
        parser.print_help()
        return

    if args.migrate or args.all:
        cmd_migrate()
    if args.evaluate or args.all:
        cmd_evaluate(essay_id_filter=args.essay_id, writer_filter=args.writer, force=args.force)
    if args.aggregate or args.all:
        cmd_aggregate()


if __name__ == "__main__":
    main()
