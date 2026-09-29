from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings with safe local defaults."""

    database_path: Path
    request_timeout_seconds: float = 20.0
    user_agent: str = "AI-Model-Watch/0.1 (+local research collector)"
    llm_provider: str = "heuristic"
    llm_endpoint: str = "http://127.0.0.1:11434"
    llm_model: str = ""
    x_bearer_token: str = ""
    x_enabled: bool = False
    x_queries: tuple[str, ...] = (
        '(OpenAI OR Anthropic OR Claude OR GPT OR Gemini OR Llama OR Mistral OR DeepSeek OR "AI model") -is:retweet',
    )
    x_max_results: int = 50
    translation_enabled: bool = False
    translation_limit: int = 100
    translation_model: str = ''
    max_age_weeks: int = 4  # 0 disables the recency filter

    @property
    def since(self) -> str | None:
        if self.max_age_weeks <= 0:
            return None
        return (datetime.now(timezone.utc) - timedelta(weeks=self.max_age_weeks)).isoformat()

    @classmethod
    def from_environment(cls) -> "Settings":
        _load_local_env()
        database_path = Path(
            os.environ.get("AI_MODEL_WATCH_DB", "data/ai_model_watch.db")
        )
        timeout = float(os.environ.get("AI_MODEL_WATCH_TIMEOUT", "20"))
        raw_queries = os.environ.get("AI_MODEL_WATCH_X_QUERIES", "").strip()
        queries = tuple(query.strip() for query in raw_queries.split("||") if query.strip())
        if not queries:
            queries = cls.x_queries
        return cls(
            database_path=database_path,
            request_timeout_seconds=timeout,
            llm_provider=os.environ.get("AI_MODEL_WATCH_LLM", "heuristic"),
            llm_endpoint=os.environ.get("AI_MODEL_WATCH_LLM_ENDPOINT", "http://127.0.0.1:11434"),
            llm_model=os.environ.get("AI_MODEL_WATCH_LLM_MODEL", ""),
            x_bearer_token=os.environ.get(
                "AI_MODEL_WATCH_X_BEARER_TOKEN",
                os.environ.get("X_BEARER_TOKEN", ""),
            ),
            x_enabled=os.environ.get("AI_MODEL_WATCH_ENABLE_X", "false").lower() in {"1", "true", "yes", "on"},
            x_queries=queries,
            x_max_results=max(10, min(int(os.environ.get("AI_MODEL_WATCH_X_MAX_RESULTS", "50")), 100)),
            translation_enabled=os.environ.get("AI_MODEL_WATCH_TRANSLATION", "false").lower() in {"1", "true", "yes", "on"},
            translation_limit=max(1, min(int(os.environ.get("AI_MODEL_WATCH_TRANSLATION_LIMIT", "100")), 500)),
            translation_model=os.environ.get('AI_MODEL_WATCH_TRANSLATION_MODEL', ''),
            max_age_weeks=max(0, int(os.environ.get('AI_MODEL_WATCH_MAX_AGE_WEEKS', '4'))),
        )


def _load_local_env() -> None:
    """Load simple KEY=VALUE entries without adding a dotenv dependency."""
    candidates = (Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env")
    for path in candidates:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        return
