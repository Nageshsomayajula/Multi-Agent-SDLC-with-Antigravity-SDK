from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class CaptionSegment:
    speaker: str
    text: str
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def merge_text(self, text: str) -> None:
        if text.strip() and text.strip() != self.text.strip():
            self.text = text.strip()
            self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data


@dataclass(slots=True)
class MeetingQuestion:
    speaker: str
    text: str
    addressed_to_bot: bool
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker": self.speaker,
            "text": self.text,
            "addressed_to_bot": self.addressed_to_bot,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class AgentReply:
    text: str
    rationale: str | None = None
    should_speak: bool = True
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "rationale": self.rationale,
            "should_speak": self.should_speak,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class MeetSelectors:
    mic_button: str
    camera_button: str
    join_button: str
    ask_to_join_button: str
    captions_button: str
    chat_button: str
    leave_button: str
    caption_container: str
    caption_speaker: str
    caption_text: str
