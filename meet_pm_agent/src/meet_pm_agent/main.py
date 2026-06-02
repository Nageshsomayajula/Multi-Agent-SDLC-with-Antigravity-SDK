from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

import orjson
from dotenv import load_dotenv

from .audio_router import VirtualMicrophone
from .caption_watcher import TranscriptBuffer
from .claude_agent import ClaudeProjectManagerAgent
from .config import load_settings
from .meet_bot import GoogleMeetBot
from .models import AgentReply, MeetingQuestion
from .tts import SpeechSynthesizer

LOGGER = logging.getLogger(__name__)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Google Meet project manager agent")
    parser.add_argument("--meet-url", dest="meet_url", help="Google Meet URL", required=False)
    parser.add_argument("--bot-name", dest="bot_name", help="Display name used for trigger detection")
    parser.add_argument("--profile-dir", dest="meet_profile_dir", help="Persistent browser profile directory")
    parser.add_argument("--headless", dest="meet_headless", action="store_true", help="Run browser headless")
    return parser.parse_args()


async def maybe_answer_question(
    *,
    question: MeetingQuestion,
    transcript: TranscriptBuffer,
    llm: ClaudeProjectManagerAgent,
    tts: SpeechSynthesizer,
    mic: VirtualMicrophone,
    bot: GoogleMeetBot,
    output_dir: Path,
    output_mode: str,
) -> AgentReply:
    context = transcript.render_context()
    reply = llm.respond(context=context, question=question)

    audio_path = output_dir / f"reply-{question.created_at.strftime('%Y%m%dT%H%M%S')}.mp3"
    if reply.should_speak and output_mode in {"voice", "voice_then_chat"}:
        await tts.synthesize(reply.text, audio_path)
        await mic.play_file(audio_path)

    if output_mode in {"chat_only", "voice_then_chat"}:
        await bot.post_chat_message(reply.text)

    return reply


async def run() -> None:
    load_dotenv()
    args = parse_args()

    overrides: dict[str, object] = {}
    if args.meet_url:
        overrides["MEET_URL"] = args.meet_url
    if args.bot_name:
        overrides["BOT_NAME"] = args.bot_name
    if args.meet_profile_dir:
        overrides["MEET_PROFILE_DIR"] = args.meet_profile_dir
    if args.meet_headless:
        overrides["MEET_HEADLESS"] = True

    settings = load_settings(**overrides)
    configure_logging(settings.log_level)

    transcript = TranscriptBuffer(
        bot_name=settings.bot_name,
        max_segments=settings.max_history_segments,
        prompt_window_minutes=settings.prompt_window_minutes,
    )
    llm = ClaudeProjectManagerAgent(settings)
    tts = SpeechSynthesizer(voice=settings.tts_voice, rate=settings.tts_rate)
    mic = VirtualMicrophone(settings.virtual_mic_sink)
    await mic.ensure_ready()

    events_file = settings.logs_dir / "events.jsonl"
    cooldown_until = 0.0

    async with GoogleMeetBot(settings) as bot:
        await bot.join(settings.meet_url)
        LOGGER.info("Bot joined the meeting and entered monitoring loop.")

        while True:
            if settings.exit_when_removed and not await bot.is_still_in_meeting():
                LOGGER.info("Bot is no longer in the meeting; exiting.")
                break

            rows = await bot.read_caption_rows()
            new_segments = transcript.ingest_many(rows)
            if new_segments:
                with events_file.open("ab") as handle:
                    for segment in new_segments:
                        handle.write(orjson.dumps({"type": "caption", **segment.to_dict()}))
                        handle.write(b"\n")

            question = transcript.latest_question()
            loop_time = asyncio.get_running_loop().time()
            if (
                question is not None
                and question.addressed_to_bot
                and loop_time >= cooldown_until
            ):
                reply = await maybe_answer_question(
                    question=question,
                    transcript=transcript,
                    llm=llm,
                    tts=tts,
                    mic=mic,
                    bot=bot,
                    output_dir=settings.artifacts_dir,
                    output_mode=settings.output_mode,
                )
                cooldown_until = loop_time + settings.response_cooldown_seconds
                with events_file.open("ab") as handle:
                    handle.write(orjson.dumps({"type": "question", **question.to_dict()}))
                    handle.write(b"\n")
                    handle.write(orjson.dumps({"type": "reply", **reply.to_dict()}))
                    handle.write(b"\n")

            await asyncio.sleep(settings.caption_poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run())
