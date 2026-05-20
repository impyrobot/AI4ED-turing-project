import json
from pathlib import Path


def load_index(output_dir: str) -> dict:
    path = Path(output_dir) / "index.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_index(output_dir: str, index: dict) -> None:
    path = Path(output_dir) / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2))


def save_trial(output_dir: str, trial_id: str, record: dict) -> Path:
    essays_dir = Path(output_dir) / "essays"
    essays_dir.mkdir(parents=True, exist_ok=True)
    path = essays_dir / f"{trial_id}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return path


def word_count(text: str) -> int:
    return len(text.split())
