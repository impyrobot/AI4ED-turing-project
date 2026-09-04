"""Aggregate all evaluation + rating files into data/summary.csv."""
import json
import math
import sys
from pathlib import Path

import pandas as pd
import numpy as np

from evaluation import config
from evaluation.schema import EssayRecord

DIMS = ["tr", "cc", "lr", "gra"]
DIM_KEYS = {
    "tr":  "task_response",
    "cc":  "coherence_cohesion",
    "lr":  "lexical_resource",
    "gra": "grammatical_range",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_summary() -> pd.DataFrame:
    essays_dir = Path(config.ESSAYS_DIR)
    evals_dir  = Path(config.EVALUATIONS_DIR)
    ratings_dir = Path(config.RATINGS_DIR)

    rows = []
    for ep in sorted(essays_dir.glob("*.json")):
        e = EssayRecord.model_validate_json(ep.read_text(encoding="utf-8"))
        row: dict = {
            "essay_id":   e.essay_id,
            "writer_type": e.writer_type,
            "writer_id":  e.writer_id,
            "condition":  e.condition,
            "prompt_id":  e.prompt_id,
            "word_count": e.essay_word_count,
        }

        # WRAFT
        wp = evals_dir / f"wraft_{e.essay_id}.json"
        row["wraft_overall"] = _load_json(wp)["score"] if wp.exists() else float("nan")

        # Judges
        for judge in ["claude", "gpt"]:
            jp = evals_dir / f"judge_{judge}_{e.essay_id}.json"
            if jp.exists():
                jd = _load_json(jp)
                row[f"judge_{judge}_overall"] = jd["overall_band"]
                for short, key in DIM_KEYS.items():
                    row[f"judge_{judge}_{short}"] = jd[key]["band"]
            else:
                row[f"judge_{judge}_overall"] = float("nan")
                for short in DIM_KEYS:
                    row[f"judge_{judge}_{short}"] = float("nan")

        # Judge means (nanmean handles 1-judge vs 2-judge asymmetry)
        row["judge_mean_overall"] = np.nanmean([row["judge_claude_overall"], row["judge_gpt_overall"]])
        for short in DIMS:
            row[f"judge_mean_{short}"] = np.nanmean([row[f"judge_claude_{short}"], row[f"judge_gpt_{short}"]])

        # Raters (dynamic — any rater_XXX_<essay_id>.json)
        for rp in sorted(ratings_dir.glob(f"*_{e.essay_id}.json")):
            rd = _load_json(rp)
            rater = rd["rater"]
            scores = rd.get("scores", {})
            row[f"{rater}_overall"] = scores.get("overall_band")

        rows.append(row)

    df = pd.DataFrame(rows)
    out = Path(config.SUMMARY_CSV)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Summary: {len(df)} rows → {out}", file=sys.stderr)
    return df


if __name__ == "__main__":
    build_summary()
