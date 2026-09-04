from pathlib import Path

# WRAFT scoring model (fine-tuned GPT-4o via OpenAI)
WRAFT_SCORE_MODEL    = "ft:gpt-4o-2024-08-06:waseda-university:eassy-eval:AVLSHV8x"
WRAFT_SCORE_FALLBACK = "gpt-4.1"
WRAFT_PROMPT_PATH    = Path(__file__).parents[1] / "wraft/backend/myapp/templates/prompts/score_prompt.txt"

# LLM judge settings
JUDGE_TEMPERATURE = 0.2
JUDGE_MAX_TOKENS  = 600

# Judge model versions
JUDGE_CLAUDE_MODEL = "claude-sonnet-4-6"
JUDGE_GPT_MODEL    = "gpt-4.1"

# Data directories (relative to project root; runner resolves absolute paths)
ESSAYS_DIR      = Path("data/essays")
EVALUATIONS_DIR = Path("data/evaluations")
RATINGS_DIR     = Path("data/ratings")
SUMMARY_CSV     = Path("data/summary.csv")
PHASE1A_DIR     = Path("data/phase1a/essays")
