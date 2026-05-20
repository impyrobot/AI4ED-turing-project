"""
Re-generate module_plan essays from existing saved plans using the updated
essay writing template and lower temperature. Does NOT re-run the planning module.
Overwrites the essay_text and essay_word_count fields only.
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[1] / ".env")

from data_collection import config, storage
from data_collection.adapters.anthropic_adapter import AnthropicAdapter
from data_collection.adapters.openai_adapter import OpenAIAdapter
from data_collection.adapters.gemini_adapter import GeminiAdapter
from data_collection.adapters.local_adapter import LocalAdapter
from data_collection.conditions.treatment import ESSAY_WRITING_TEMPLATE

ADAPTERS = {
    "claude": lambda: AnthropicAdapter(),
    "gpt":    lambda: OpenAIAdapter(),
    "gemini": lambda: GeminiAdapter(),
    "llama":  lambda: LocalAdapter("llama", config.MODEL_VERSIONS["llama"]),
    "qwen":   lambda: LocalAdapter("qwen",  config.MODEL_VERSIONS["qwen"]),
}

ESSAYS_DIR = Path("data/phase1a/essays")


def regen_one(path: Path) -> None:
    record = json.loads(path.read_text(encoding="utf-8"))

    if record.get("condition") != "treatment":
        return
    plan_text = record.get("plan_text", "").strip()
    if not plan_text:
        print(f"[SKIP] {path.name} — no plan saved", file=sys.stderr)
        return

    model = record["model"]
    if model not in ADAPTERS:
        print(f"[SKIP] {path.name} — no adapter for {model}", file=sys.stderr)
        return

    prompt_text = record["prompt_text"]
    writing_prompt = ESSAY_WRITING_TEMPLATE.format(prompt=prompt_text, plan=plan_text)

    try:
        adapter = ADAPTERS[model]()
        essay_text = adapter.generate(writing_prompt, config.ESSAY_TEMPERATURE, config.MAX_TOKENS_ESSAY)
    except Exception as exc:
        print(f"[ERR]  {path.name}: {exc}", file=sys.stderr)
        return

    old_wc = record["essay_word_count"]
    new_wc = storage.word_count(essay_text)
    record["essay_text"] = essay_text
    record["essay_word_count"] = new_wc
    record["metadata"]["regen_note"] = "essay re-generated with prescriptive prompt, temp=0.2"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK]   {path.name}  words: {old_wc} → {new_wc}", file=sys.stderr)


def main():
    paths = sorted(ESSAYS_DIR.glob("*_treatment_*.json"))
    if not paths:
        print(f"[ERR] No treatment JSONs found in {ESSAYS_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Re-generating essays for {len(paths)} treatment files...", file=sys.stderr)
    for p in paths:
        regen_one(p)


if __name__ == "__main__":
    main()
