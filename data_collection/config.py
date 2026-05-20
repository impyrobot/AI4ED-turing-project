TEMPERATURE        = 0.7
ESSAY_TEMPERATURE  = 0.2   # lower temp for essay writing to improve plan adherence
MAX_TOKENS_ESSAY   = 800
MAX_TOKENS_PLAN    = 600
WORD_COUNT_TARGET  = (240, 260)
WORD_COUNT_TEXT    = "approximately 250 words (240–260 acceptable)"
MAX_PLANNING_TURNS = 15
STOP_TOKEN         = "PLAN COMPLETE"
OUTPUT_DIR         = "data/phase1a"

# Verify gpt/gemini strings against live API before running — these change.
MODEL_VERSIONS = {
    "claude":   "claude-opus-4-7",
    "gpt":      "gpt-4.1",           # verified 2026-05-11
    "gemini":   "gemini-2.5-flash",  # 2.5-pro requires billing; flash available on free tier
    "llama":    "llama3.1:8b",           # Ollama — pull before running
    "deepseek": "deepseek-r1:7b",       # Ollama — pull before running; thinking tokens stripped
    "qwen":     "qwen2.5:7b",           # Ollama — replacement for deepseek-r1; no thinking tokens
}

COMMERCIAL_MODELS = ["claude", "gpt", "gemini"]
LOCAL_MODELS      = ["llama", "deepseek", "qwen"]
CONDITIONS        = ["baseline_a", "baseline_b", "treatment"]
ACTIVE_PROMPTS    = ["p1", "p2", "p5"]
TRIALS_PER_CELL   = 1

CONFIG_SNAPSHOT = {
    "temperature":        TEMPERATURE,
    "max_tokens_essay":   MAX_TOKENS_ESSAY,
    "max_tokens_plan":    MAX_TOKENS_PLAN,
    "word_count_target":  WORD_COUNT_TARGET,
    "max_planning_turns": MAX_PLANNING_TURNS,
    "stop_token":         STOP_TOKEN,
    "model_versions":     MODEL_VERSIONS,
}
