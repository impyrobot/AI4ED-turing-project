"""Phase 1a data collection runner."""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[1] / ".env")

from data_collection import config, storage
from data_collection.prompts import PROMPTS
from data_collection.adapters.anthropic_adapter import AnthropicAdapter
from data_collection.adapters.openai_adapter import OpenAIAdapter
from data_collection.adapters.gemini_adapter import GeminiAdapter
from data_collection.adapters.local_adapter import LocalAdapter
from data_collection import conditions


def build_matrix(model_filter=None, condition_filter=None, include_local=False):
    models = config.COMMERCIAL_MODELS + (config.LOCAL_MODELS if include_local else [])
    cells = []
    for model in models:
        if model_filter and model != model_filter:
            continue
        for prompt_id in config.ACTIVE_PROMPTS:
            for condition in config.CONDITIONS:
                if condition_filter and condition != condition_filter:
                    continue
                for trial in range(1, config.TRIALS_PER_CELL + 1):
                    cells.append({
                        "model": model,
                        "prompt_id": prompt_id,
                        "condition": condition,
                        "trial": trial,
                        "trial_id": f"{model}_{prompt_id}_{condition}_t{trial}",
                    })
    return cells


def _ollama_running() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False


def _init_adapters():
    adapters = {
        "claude": AnthropicAdapter(),
        "gpt":    OpenAIAdapter(),
        "gemini": GeminiAdapter(),
    }
    if _ollama_running():
        for name in config.LOCAL_MODELS:
            adapters[name] = LocalAdapter(name, config.MODEL_VERSIONS[name])
        names = ", ".join(config.LOCAL_MODELS)
        print(f"[OK]   ollama running — {names} adapters initialised", file=sys.stderr)
    else:
        for name in config.LOCAL_MODELS:
            print(f"[SKIP] {name}: ollama not running (start with: ollama serve)", file=sys.stderr)
    return adapters


def _dispatch(cell, adapter, dry_run=False):
    condition = cell["condition"]
    prompt_text = PROMPTS[cell["prompt_id"]]
    if condition == "baseline_a":
        return conditions.baseline_a.run(adapter, cell["prompt_id"], prompt_text)
    elif condition == "baseline_b":
        return conditions.baseline_b.run(adapter, cell["prompt_id"], prompt_text)
    elif condition == "treatment":
        return conditions.treatment.run(adapter, cell["prompt_id"], prompt_text)
    raise ValueError(f"Unknown condition: {condition}")


def main():
    parser = argparse.ArgumentParser(description="Phase 1a data collection")
    parser.add_argument("--model",     help="Run only this model")
    parser.add_argument("--condition", help="Run only this condition")
    parser.add_argument("--dry-run",   action="store_true", help="Print matrix and exit")
    parser.add_argument("--force",     action="store_true", help="Re-run completed cells")
    args = parser.parse_args()

    include_local = _ollama_running() or (args.model in config.LOCAL_MODELS if args.model else False)
    matrix = build_matrix(model_filter=args.model, condition_filter=args.condition, include_local=include_local)

    if args.dry_run:
        print(f"{'trial_id':<40} {'model':<8} {'condition':<12} {'prompt':<6} {'trial'}")
        print("-" * 80)
        for cell in matrix:
            print(f"{cell['trial_id']:<40} {cell['model']:<8} {cell['condition']:<12} {cell['prompt_id']:<6} {cell['trial']}")
        print(f"\n{len(matrix)} cells total (commercial models only; local models skipped)")
        for name in config.LOCAL_MODELS:
            print(f"  [SKIP] {name}: hosting pending")
        return

    adapters = _init_adapters()
    index = storage.load_index(config.OUTPUT_DIR)
    completed = errored = 0
    start_time = time.time()

    for cell in matrix:
        tid = cell["trial_id"]
        if not args.force and index.get(tid) == "completed":
            print(f"[SKIP] {tid} already completed", file=sys.stderr)
            continue

        index[tid] = "pending"
        storage.save_index(config.OUTPUT_DIR, index)

        adapter = adapters[cell["model"]]
        t0 = time.time()
        try:
            record = _dispatch(cell, adapter)
            record.setdefault("trial_id", tid)
            record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            record.setdefault("config_snapshot", config.CONFIG_SNAPSHOT)
            storage.save_trial(config.OUTPUT_DIR, tid, record)
            index[tid] = "completed"
            completed += 1
            print(f"[OK]   {tid}  ({time.time()-t0:.1f}s)", file=sys.stderr)
        except Exception as exc:
            index[tid] = "errored"
            errored += 1
            print(f"[ERR]  {tid}: {exc}", file=sys.stderr)
        finally:
            storage.save_index(config.OUTPUT_DIR, index)

    elapsed = time.time() - start_time
    print(
        f"\nDone: {completed} completed, {errored} errored, {elapsed:.1f}s total",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
