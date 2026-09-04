"""
One-off ingestion of Sheffield human participant essays into the unified schema.
Participants 1-7 excluding 3 and 8 (those with V2 essay available).

Usage:
    PYTHONPATH=/home/ray/.local/lib/python3.10/site-packages \
        python3 -m evaluation.ingest_sheffield
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from docx import Document

from evaluation.schema import EssayRecord

BASE        = Path(__file__).parents[1]
ESSAY_DIR   = BASE / "data" / "essays"
SHEF_DIR    = BASE / "data" / "essay-shef"
TIMESTAMP   = datetime.now(timezone.utc).isoformat()

PROMPT_TEXTS = {
    "p1": "Technology has changed how people interact. In what ways has technology affected relationships? Is this positive or negative?",
    "p2": "Some think university students should study whatever they like. Others think they should only study useful future subjects such as science and technology. Discuss both views and give your opinion.",
    "p5": "The working week should be shorter and workers should have a longer weekend. Do you agree or disagree?",
}

# (participant_num, prompt_id, original_filename, v2_filename, plan_filename_or_None)
PARTICIPANTS = [
    (1, "p2", "Original_Essay.docx",  "V2_Essay.docx",    "essay_plan_Some think university students should study whatever they like. Others think they should only study useful future subjects such as science and technology. Discuss both views and give your opinion. (1).txt"),
    (2, "p5", "Original_Essay.docx",  "V2_Essay.docx",    "essay_plan_The working week should be shorter and workers should have a longer weekend. Do you agree or disagree_.docx"),
    (4, "p5", "Original_Essay.docx",  "V2_Essay.docx",    "essay_plan_The working week should be shorter and workers should have a longer weekend. Do you agree or disagree_.pdf"),
    (5, "p1", "Original Essay.docx",  "Version 2.docx",   None),
    (6, "p1", "Original Essay.docx",  "Version 2.docx",   None),
    (7, "p5", "Original Essay.docx",  "Version 2.docx",   None),
]


def read_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def read_plan(folder: Path, filename: str) -> str | None:
    if filename is None:
        return None
    path = folder / filename
    if not path.exists():
        print(f"  [warn] plan file not found: {path.name}")
        return None
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return read_txt(path)
    if suffix == ".docx":
        return read_docx(path)
    if suffix == ".pdf":
        print(f"  [info] PDF plan skipped (not extractable without pdfminer): {path.name}")
        return None
    return None


def word_count(text: str) -> int:
    return len(text.split())


def make_record(num: int, prompt_id: str, condition: str,
                essay_text: str, plan_text: str | None) -> EssayRecord:
    pid = f"shef{num:02d}"
    essay_id = f"human_{pid}_{prompt_id}_{condition}"
    return EssayRecord(
        essay_id      = essay_id,
        writer_type   = "human",
        writer_id     = pid,
        writer_version= None,
        condition     = condition,
        prompt_id     = prompt_id,
        prompt_text   = PROMPT_TEXTS[prompt_id],
        essay_text    = essay_text,
        essay_word_count = word_count(essay_text),
        plan_text     = plan_text,
        transcript    = None,
        source_run    = "sheffield_cohort",
        timestamp     = TIMESTAMP,
    )


def main():
    ESSAY_DIR.mkdir(parents=True, exist_ok=True)
    saved, skipped = [], []

    for num, prompt_id, orig_file, v2_file, plan_file in PARTICIPANTS:
        folder = SHEF_DIR / f"participant_{num}" / f"Test_{num}"
        print(f"\nParticipant {num} ({prompt_id})")

        orig_path = folder / orig_file
        v2_path   = folder / v2_file

        if not orig_path.exists():
            print(f"  [skip] missing: {orig_path.name}")
            skipped.append(num)
            continue
        if not v2_path.exists():
            print(f"  [skip] missing V2: {v2_path.name}")
            skipped.append(num)
            continue

        orig_text = read_docx(orig_path)
        v2_text   = read_docx(v2_path)
        plan_text = read_plan(folder, plan_file)

        for condition, text in [("no_plan", orig_text), ("module_plan", v2_text)]:
            record = make_record(num, prompt_id, condition, text, plan_text)
            out = ESSAY_DIR / f"{record.essay_id}.json"
            out.write_text(json.dumps(record.model_dump(), indent=2, ensure_ascii=False))
            print(f"  saved {out.name}  ({record.essay_word_count} words)")
            saved.append(out.name)

    print(f"\nDone: {len(saved)} essays saved, {len(skipped)} participants skipped {skipped}")


if __name__ == "__main__":
    main()
