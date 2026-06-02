from __future__ import annotations

import re
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Iterable

from .models import CaptionSegment, MeetingQuestion

QUESTION_WORDS = ("what", "why", "when", "who", "how", "can", "could", "should", "would", "do")


class TranscriptBuffer:
    """Maintains a rolling, de-duplicated caption history."""

    def __init__(self, bot_name: str, max_segments: int = 18, prompt_window_minutes: int = 8) -> None:
        self.bot_name = bot_name.strip().lower()
        self._segments: deque[CaptionSegment] = deque(maxlen=max_segments)
        self._prompt_window = timedelta(minutes=prompt_window_minutes)
        self._last_observed_fingerprint: str | None = None

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def ingest_many(self, rows: Iterable[tuple[str, str]]) -> list[CaptionSegment]:
        added: list[CaptionSegment] = []
        for speaker, text in rows:
            speaker_norm = self._normalize(speaker)
            text_norm = self._normalize(text)
            if not speaker_norm or not text_norm:
                continue
            fingerprint = f"{speaker_norm.lower()}::{text_norm.lower()}"
            if fingerprint == self._last_observed_fingerprint:
                continue

            if self._segments and self._segments[-1].speaker.lower() == speaker_norm.lower():
                previous = self._segments[-1].text
                if text_norm.startswith(previous) or previous.startswith(text_norm):
                    self._segments[-1].merge_text(text_norm)
                    self._last_observed_fingerprint = fingerprint
                    added.append(self._segments[-1])
                    continue

            segment = CaptionSegment(speaker=speaker_norm, text=text_norm)
            self._segments.append(segment)
            self._last_observed_fingerprint = fingerprint
            added.append(segment)
        return added

    def recent_segments(self) -> list[CaptionSegment]:
        cutoff = datetime.now(timezone.utc) - self._prompt_window
        return [segment for segment in self._segments if segment.updated_at >= cutoff]

    def render_context(self) -> str:
        lines = []
        for segment in self.recent_segments():
            lines.append(f"{segment.speaker}: {segment.text}")
        return "\n".join(lines)

    def latest_question(self) -> MeetingQuestion | None:
        if not self._segments:
            return None

        latest = self._segments[-1]
        text_lc = latest.text.lower()
        addressed = self.bot_name in text_lc or any(
            token in text_lc for token in ("agent", "bot", "project manager")
        )
        is_question = "?" in latest.text or text_lc.startswith(QUESTION_WORDS)

        if not is_question:
            return None

        return MeetingQuestion(
            speaker=latest.speaker,
            text=latest.text,
            addressed_to_bot=addressed,
        )
