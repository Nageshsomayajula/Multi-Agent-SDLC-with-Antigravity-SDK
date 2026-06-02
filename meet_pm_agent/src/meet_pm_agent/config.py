from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and CLI overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-sonnet-4-20250514", alias="CLAUDE_MODEL")
    bot_name: str = Field("Atlas PM", alias="BOT_NAME")
    bot_role: str = Field(
        "You are a concise, tactful project manager in a live meeting. "
        "Answer clearly, state risks, clarify owners, and propose next steps.",
        alias="BOT_ROLE",
    )
    meet_url: str = Field(..., alias="MEET_URL")
    meet_headless: bool = Field(False, alias="MEET_HEADLESS")
    meet_profile_dir: Path = Field(
        Path.home() / ".config" / "meet-agent-profile",
        alias="MEET_PROFILE_DIR",
    )
    browser_channel: str | None = Field("chrome", alias="BROWSER_CHANNEL")
    browser_slow_mo_ms: int = Field(0, alias="BROWSER_SLOW_MO_MS")
    join_timeout_seconds: int = Field(120, alias="JOIN_TIMEOUT_SECONDS")
    caption_poll_interval_seconds: float = Field(1.5, alias="CAPTION_POLL_INTERVAL_SECONDS")
    max_history_segments: int = Field(18, alias="MAX_HISTORY_SEGMENTS")
    response_cooldown_seconds: int = Field(20, alias="RESPONSE_COOLDOWN_SECONDS")
    max_response_tokens: int = Field(350, alias="MAX_RESPONSE_TOKENS")
    virtual_mic_sink: str = Field("MeetAgentSink", alias="VIRTUAL_MIC_SINK")
    tts_voice: str = Field("en-US-AriaNeural", alias="TTS_VOICE")
    tts_rate: str = Field("+0%", alias="TTS_RATE")
    logs_dir: Path = Field(Path("./runtime/logs"), alias="LOGS_DIR")
    artifacts_dir: Path = Field(Path("./runtime/artifacts"), alias="ARTIFACTS_DIR")
    prompt_window_minutes: int = Field(8, alias="PROMPT_WINDOW_MINUTES")
    exit_when_removed: bool = Field(True, alias="EXIT_WHEN_REMOVED")
    output_mode: Literal["voice", "chat_only", "voice_then_chat"] = Field(
        "voice", alias="OUTPUT_MODE"
    )
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    def prepare_directories(self) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.meet_profile_dir.mkdir(parents=True, exist_ok=True)


def load_settings(**overrides: object) -> Settings:
    settings = Settings(**overrides)
    settings.prepare_directories()
    return settings
