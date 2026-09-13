"""
Central runtime configuration. Single source of truth for constants that
would otherwise be hardcoded/duplicated across modules (model names,
service URLs).
"""

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:1.5b-instruct"
