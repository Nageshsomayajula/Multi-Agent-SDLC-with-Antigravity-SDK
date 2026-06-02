# Google Meet Project Manager Agent

This repository provides a **browser-based Google Meet agent** that joins a meeting, monitors live captions, detects when the bot is being addressed, generates project-manager-style answers with **Claude**, and responds through a **virtual microphone** with synthesized speech.

## What this implementation does

This codebase is designed as a practical MVP rather than a production-grade meeting platform. It focuses on the parts that can be built and controlled directly:

| Capability | Included in this repository | Notes |
| --- | --- | --- |
| Join Google Meet in Chromium | Yes | Uses Playwright with a persistent browser profile |
| Automate camera/microphone state | Yes | Disables camera, keeps mic controlled by the agent |
| Read live meeting conversation | Yes | Uses Google Meet captions as the main input channel |
| Detect questions for the bot | Yes | Keyword and name-based trigger detection |
| Generate answers with Claude | Yes | Uses the Anthropic Messages API |
| Speak answers back into the meeting | Yes | Uses a virtual microphone pipeline |
| Persist transcripts and logs | Yes | Saves JSONL events and transcript segments locally |
| Production hardening | Partial | Google Meet DOM changes and account auth still require maintenance |

## Recommended architecture

The bot uses **caption-driven understanding** because it is substantially more stable for an initial build than trying to decode raw WebRTC audio inside the browser.

```text
Google Meet page in Chromium
    -> captions observer collects speaker + text segments
    -> transcript buffer merges recent context
    -> trigger detector decides whether the bot was asked to respond
    -> Claude response engine generates a PM-style answer
    -> text-to-speech renderer creates WAV output
    -> virtual microphone player feeds audio into Meet
```

## Why this design is the right MVP

A browser bot for Google Meet has two difficult surfaces: **browser automation** and **live audio routing**. The most fragile part of the browser layer is usually the Meet DOM, while the most fragile part of the audio layer is microphone injection. This repository therefore isolates responsibilities into small modules so that selectors, prompt policy, and audio transport can be updated independently.

## Important constraints

| Constraint | Impact |
| --- | --- |
| Google Meet has no official public bot-join API for this workflow | The solution relies on browser automation and may need maintenance |
| Google UI changes can break selectors | Selector configuration is centralized for easier updates |
| Google login can require CAPTCHA or manual intervention | Use a persistent profile and pre-authenticate once |
| Caption scraping is not equivalent to perfect transcription | Accuracy depends on Meet captions |
| Real-time answer injection needs a virtual microphone | Linux audio setup is required before first run |

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/meet_pm_agent/main.py` | Main entry point that orchestrates the bot |
| `src/meet_pm_agent/config.py` | Environment-based configuration |
| `src/meet_pm_agent/meet_bot.py` | Playwright automation for joining and controlling Google Meet |
| `src/meet_pm_agent/caption_watcher.py` | Caption scraping and transcript buffering |
| `src/meet_pm_agent/claude_agent.py` | Claude prompt construction and response generation |
| `src/meet_pm_agent/tts.py` | Speech synthesis abstraction |
| `src/meet_pm_agent/audio_router.py` | Virtual microphone setup and playback |
| `src/meet_pm_agent/models.py` | Shared dataclasses for captions and events |
| `scripts/run_bot.py` | Convenient launch wrapper |
| `docs/linux_audio_setup.md` | Virtual microphone setup instructions |

## Prerequisites

You will need the following before using the bot:

1. A Google account that can join the target Meet room.
2. A Meet URL.
3. An Anthropic API key stored as `ANTHROPIC_API_KEY`.
4. Linux audio tools such as PulseAudio or PipeWire compatibility utilities.
5. Chromium dependencies required by Playwright.

## Basic setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## Typical runtime flow

```bash
python scripts/run_bot.py \
  --meet-url "https://meet.google.com/abc-defg-hij" \
  --bot-name "Atlas PM" \
  --profile-dir "$HOME/.config/meet-agent-profile"
```

## Environment variables

| Variable | Description |
| --- | --- |
| `ANTHROPIC_API_KEY` | API key for Claude |
| `CLAUDE_MODEL` | Claude model name, for example `claude-sonnet-4-20250514` |
| `BOT_NAME` | Name the bot listens for in questions |
| `BOT_ROLE` | Persona instruction, such as project manager |
| `MEET_PROFILE_DIR` | Persistent Chromium profile path |
| `MEET_HEADLESS` | Usually `false` for Google Meet |
| `MEET_CAPTIONS_LANGUAGE` | Optional language hint for caption monitoring |
| `VIRTUAL_MIC_SINK` | Name of the PulseAudio sink/source used for speech playback |
| `LOG_LEVEL` | Logging verbosity |

## Safety and compliance note

This repository is provided for **authorized internal automation only**. Before joining or responding in a meeting, make sure the meeting host and participants permit the bot's presence and any automated speaking behavior.

## Next improvements

| Improvement | Benefit |
| --- | --- |
| Replace DOM scraping with a Chrome extension observer | More reliable caption capture |
| Add meeting chat fallback | Useful when voice playback is unavailable |
| Add retrieval over project docs | Better PM-quality answers |
| Add speaker diarization from raw audio | Better context attribution |
| Add backend queue and dashboard | Easier multi-meeting management |
