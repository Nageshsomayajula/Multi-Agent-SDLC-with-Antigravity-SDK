from __future__ import annotations

import logging
from textwrap import dedent

from anthropic import Anthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import Settings
from .models import AgentReply, MeetingQuestion

LOGGER = logging.getLogger(__name__)


class ClaudeProjectManagerAgent:
    """Wraps Claude with a focused prompt for concise live-meeting responses."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Anthropic(api_key=settings.anthropic_api_key)

    def _system_prompt(self) -> str:
        return dedent(
            f"""
            {self.settings.bot_role}

            You are participating in a live Google Meet as **{self.settings.bot_name}**.
            Your speaking style must sound like an experienced project manager.

            Follow these rules:
            1. Keep answers short enough to speak in roughly 20 to 45 seconds.
            2. If the question is ambiguous, state the assumption briefly and answer anyway.
            3. Mention owners, risks, deadlines, or dependencies when relevant.
            4. Do not claim actions that have not actually been completed.
            5. If the meeting context does not support a confident answer, say what should be confirmed next.
            6. Use plain spoken English that works well with text-to-speech.
            7. Do not use bullet points or markdown in the final answer.
            8. End with a concrete next-step sentence whenever possible.
            """
        ).strip()

    def _user_prompt(self, context: str, question: MeetingQuestion) -> str:
        return dedent(
            f"""
            Recent meeting context:
            {context or 'No prior context available.'}

            Latest question from {question.speaker}:
            {question.text}

            Write the exact answer the bot should say aloud.
            Also provide one short internal rationale sentence for logging.

            Return JSON with this shape:
            {{
              "answer": "...",
              "rationale": "...",
              "should_speak": true
            }}
            """
        ).strip()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
    )
    def respond(self, context: str, question: MeetingQuestion) -> AgentReply:
        LOGGER.info("Sending prompt to Claude for question from %s", question.speaker)
        message = self.client.messages.create(
            model=self.settings.claude_model,
            max_tokens=self.settings.max_response_tokens,
            system=self._system_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": self._user_prompt(context=context, question=question),
                }
            ],
        )

        text_blocks = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        raw = "\n".join(text_blocks).strip()

        try:
            import json

            payload = json.loads(raw)
            return AgentReply(
                text=str(payload["answer"]).strip(),
                rationale=str(payload.get("rationale", "")).strip() or None,
                should_speak=bool(payload.get("should_speak", True)),
            )
        except Exception:
            LOGGER.warning("Claude returned non-JSON output; falling back to raw text parsing.")
            cleaned = raw.replace("```json", "").replace("```", "").strip()
            return AgentReply(text=cleaned, rationale="Fallback parse", should_speak=True)
