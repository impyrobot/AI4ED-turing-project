"""
One-off ingestion of Japan cohort essays into the unified schema.

Design: between-subjects
  control/   → condition: no_plan   (wrote without planning module)
  experiment/ → condition: module_plan (used planning module)
  Exception: participant 538 was in experiment folder but system failed;
             treated as no_plan per researcher decision.

Prompt p3: "It is more important to study subjects you are interested in
than to choose subjects to prepare for a job or career.
Do you agree or disagree?"

Usage:
    source .venv/bin/activate
    python3 -m evaluation.ingest_japan
"""

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from docx import Document

from evaluation.schema import EssayRecord

BASE       = Path(__file__).parents[1]
ESSAY_DIR  = BASE / "data" / "essays"
JP_BASE    = BASE / "data" / "essay-jp" / "writing experiment data" / "writing samples-anonymized"
TIMESTAMP  = datetime.now(timezone.utc).isoformat()

PROMPT_ID   = "p3"
PROMPT_TEXT = (
    "It is more important to study subjects you are interested in than to "
    "choose subjects to prepare for a job or career. Do you agree or disagree?"
)


# ── text extractors ──────────────────────────────────────────────────────────

class _StripHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return re.sub(r'\s+', ' ', ' '.join(self._parts)).strip()


def read_html(path: Path) -> str:
    parser = _StripHTML()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.get_text()


def read_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def extract(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".html":
        return read_html(path)
    if suffix == ".docx":
        return read_docx(path)
    if suffix == ".txt":
        return read_txt(path)
    raise ValueError(f"Unsupported format: {path}")


def word_count(text: str) -> int:
    return len(text.split())


# ── find the essay file inside a Moodle submission folder ───────────────────

def find_essay_file(folder: Path) -> Path | None:
    for suffix in [".html", ".docx", ".txt"]:
        matches = list(folder.glob(f"*{suffix}"))
        if matches:
            return matches[0]
    return None


# ── build EssayRecord ────────────────────────────────────────────────────────

def make_record(participant_id: str, condition: str, text: str,
                metadata: dict | None = None) -> EssayRecord:
    essay_id = f"human_jp{participant_id}_{PROMPT_ID}_{condition}"
    return EssayRecord(
        essay_id         = essay_id,
        writer_type      = "human",
        writer_id        = f"jp{participant_id}",
        writer_version   = None,
        condition        = condition,
        prompt_id        = PROMPT_ID,
        prompt_text      = PROMPT_TEXT,
        essay_text       = text,
        essay_word_count = word_count(text),
        plan_text        = None,
        transcript       = None,
        source_run       = "japan_cohort",
        timestamp        = TIMESTAMP,
    )


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ESSAY_DIR.mkdir(parents=True, exist_ok=True)
    saved, errors = [], []

    # ── numbered Moodle folders (control + experiment) ───────────────────────
    tasks = []

    # control → no_plan
    for folder in sorted((JP_BASE / "control").iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        pid = re.match(r"^(\d+)", folder.name)
        if not pid:
            continue
        tasks.append((pid.group(1), "no_plan", folder))

    # experiment → module_plan, except 538 → no_plan
    for folder in sorted((JP_BASE / "experiment").iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        pid = re.match(r"^(\d+)", folder.name)
        if not pid:
            continue
        num = pid.group(1)
        if num == "538":
            # system failure — use docx, treat as no_plan
            docx_path = folder / "Writing Submission.docx"
            if docx_path.exists():
                tasks.append((num, "no_plan", folder, docx_path))
            continue
        # skip the 538 onlinetext folder (just a note)
        if "onlinetext" in folder.name and folder.name.startswith("538"):
            continue
        tasks.append((num, "module_plan", folder))

    for task in tasks:
        pid, condition, folder = task[0], task[1], task[2]
        explicit_file = task[3] if len(task) > 3 else None

        path = explicit_file or find_essay_file(folder)
        if path is None:
            print(f"  [skip] no readable file in {folder.name}")
            errors.append(folder.name)
            continue

        try:
            text = extract(path)
            if not text.strip():
                print(f"  [skip] empty text: {folder.name}")
                errors.append(folder.name)
                continue
            record = make_record(pid, condition, text)
            out = ESSAY_DIR / f"{record.essay_id}.json"
            out.write_text(json.dumps(record.model_dump(), indent=2, ensure_ascii=False))
            print(f"  [{condition[:2].upper()}] {record.essay_id}  ({record.essay_word_count} words)")
            saved.append(record.essay_id)
        except Exception as e:
            print(f"  [error] {folder.name}: {e}")
            errors.append(folder.name)

    # ── loose experiment files ───────────────────────────────────────────────
    exp_dir = JP_BASE / "experiment"
    loose = [
        ("25c1103", "module_plan", exp_dir / "25c1103_homework_Moa.Abe.txt"),
        ("25c1127", "module_plan", exp_dir / "Interest Is The Best Teacher.docx"),
        ("C4",      "module_plan", exp_dir / "class 4.docx"),
    ]

    for pid, condition, path in loose:
        if not path.exists():
            print(f"  [skip] missing loose file: {path.name}")
            errors.append(path.name)
            continue
        try:
            text = extract(path)
            record = make_record(pid, condition, text)
            out = ESSAY_DIR / f"{record.essay_id}.json"
            out.write_text(json.dumps(record.model_dump(), indent=2, ensure_ascii=False))
            print(f"  [MP] {record.essay_id}  ({record.essay_word_count} words)")
            saved.append(record.essay_id)
        except Exception as e:
            print(f"  [error] {path.name}: {e}")
            errors.append(path.name)

    print(f"\nDone: {len(saved)} essays saved, {len(errors)} errors/skips")
    no_plan_n    = sum(1 for x in saved if "no_plan" in x)
    module_n     = sum(1 for x in saved if "module_plan" in x)
    print(f"  no_plan: {no_plan_n}  |  module_plan: {module_n}")


if __name__ == "__main__":
    main()
