from __future__ import annotations

import logging
from pathlib import Path

import edge_tts

LOGGER = logging.getLogger(__name__)


class SpeechSynthesizer:
    """Renders spoken audio with Edge TTS into an MP3 file."""

    def __init__(self, voice: str, rate: str = "+0%") -> None:
        self.voice = voice
        self.rate = rate

    async def synthesize(self, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Synthesizing reply audio to %s", output_path)
        communicate = edge_tts.Communicate(text=text, voice=self.voice, rate=self.rate)
        await communicate.save(str(output_path))
        return output_path
