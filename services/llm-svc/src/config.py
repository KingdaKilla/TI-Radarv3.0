"""Konfiguration fuer den LLM Analysis Service.

Pydantic Settings laedt Werte aus Umgebungsvariablen und .env-Dateien.
Alle Konfigurationsparameter sind zentral hier definiert.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service-Konfiguration — geladen aus Umgebungsvariablen."""

    # --- LLM Provider ---
    llm_provider: str = "gemini"  # "anthropic", "openai", "gemini" oder "ollama"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    model_name: str = "gemini-2.0-flash"
    max_tokens: int = 4096
    temperature: float = 0.3

    # --- gRPC Server ---
    service_port: int = 50070
    service_host: str = "0.0.0.0"

    # --- Observability ---
    log_level: str = "INFO"
    metrics_port: int = 9099

    # --- Lokales LLM (Ollama) ---
    ollama_base_url: str = "http://ollama:11434/v1"
    ollama_timeout_s: float = 120.0

    # --- Timeouts ---
    llm_timeout_s: float = 60.0

    # --- Sprache ---
    default_language: str = "de"

    # --- Faithfulness Guards (Task 16) ---
    faithfulness_enabled: bool = False
    sufficiency_threshold: str = "PARTIAL"  # SUFFICIENT, PARTIAL, INSUFFICIENT
    faithfulness_model: str = "claude-haiku"  # Lightweight model for checks

    model_config = {
        "env_prefix": "LLM_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
