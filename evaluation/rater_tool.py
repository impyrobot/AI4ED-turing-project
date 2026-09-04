"""Generate blank rater CSVs and ingest filled ones."""
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from evaluation import config
from evaluation.schema import EssayRecord

SCORE_COLS = ["task_response", "coherence_cohesion", "lexical_resource", "grammatical_range", "overall_band"]


def _load_essays() -> list[EssayRecord]:
    essays_dir = Path(config.ESSAYS_DIR)
    records = []
    for p in sorted(essays_dir.glob("*.json")):
        records.append(EssayRecord.model_validate_json(p.read_text(encoding="utf-8")))
    return records


def _stratified_sample(essays: list[EssayRecord], n: int, seed: int) -> list[EssayRecord]:
    import random
    rng = random.Random(seed)
    groups: dict[tuple, list] = {}
    for e in essays:
        key = (e.condition, e.writer_type)
        groups.setdefault(key, []).append(e)
    sample: list[EssayRecord] = []
    keys = sorted(groups.keys())
    # round-robin across groups until we have n
    while len(sample) < n:
        added = False
        for k in keys:
            if groups[k] and len(sample) < n:
                item = rng.choice(groups[k])
                groups[k].remove(item)
                sample.append(item)
                added = True
        if not added:
            break
    return sample


def cmd_generate(args):
    essays = _load_essays()
    if not essays:
        print("[ERR] No essays found in data/essays/", file=sys.stderr)
        sys.exit(1)

    if args.sample:
        essays = _stratified_sample(essays, args.sample, args.seed)

    rows = []
    for e in essays:
        row = {
            "essay_id":   e.essay_id,
            "prompt_id":  e.prompt_id,
            "prompt_text": e.prompt_text,
            "essay_text": e.essay_text,
        }
        for col in SCORE_COLS:
            row[col] = ""
        row["notes"] = ""
        rows.append(row)

    df = pd.DataFrame(rows)
    ratings_dir = Path(config.RATINGS_DIR)
    ratings_dir.mkdir(parents=True, exist_ok=True)
    out = ratings_dir / f"{args.rater}_sheet.csv"
    df.to_csv(out, index=False)
    print(f"Generated: {out}  ({len(df)} essays)")


def _validate_band(val) -> float | None:
    if val == "" or (isinstance(val, float) and math.isnan(val)):
        return None
    v = float(val)
    if not (0 <= v <= 9):
        raise ValueError(f"Band score {v} out of range 0–9")
    if (v * 2) != int(v * 2):
        raise ValueError(f"Band score {v} not a half-band increment")
    return v


def cmd_ingest(args):
    df = pd.read_csv(args.file)
    ratings_dir = Path(config.RATINGS_DIR)
    ratings_dir.mkdir(parents=True, exist_ok=True)

    ok = errors = 0
    for _, row in df.iterrows():
        essay_id = row["essay_id"]
        scores = {}
        valid = True
        for col in SCORE_COLS:
            try:
                scores[col] = _validate_band(row.get(col, ""))
            except ValueError as exc:
                print(f"[WARN] {essay_id} / {col}: {exc}", file=sys.stderr)
                valid = False

        record = {
            "essay_id": essay_id,
            "rater":    args.rater,
            "scores":   scores,
            "notes":    str(row.get("notes", "") or ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        out = ratings_dir / f"{args.rater}_{essay_id}.json"
        out.write_text(json.dumps(record, indent=2), encoding="utf-8")
        if valid:
            ok += 1
        else:
            errors += 1

    print(f"Ingested: {ok} ok, {errors} with warnings — files in {ratings_dir}")


def main():
    parser = argparse.ArgumentParser(description="Rater CSV tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="Produce blank rater CSV")
    gen.add_argument("--rater",  required=True)
    gen.add_argument("--all",    action="store_true", help="Include all essays")
    gen.add_argument("--sample", type=int, help="Stratified sample of N essays")
    gen.add_argument("--seed",   type=int, default=42)

    ing = sub.add_parser("ingest", help="Read filled CSV and write rating files")
    ing.add_argument("--rater", required=True)
    ing.add_argument("--file",  required=True)

    args = parser.parse_args()
    if args.cmd == "generate":
        cmd_generate(args)
    elif args.cmd == "ingest":
        cmd_ingest(args)


if __name__ == "__main__":
    main()
