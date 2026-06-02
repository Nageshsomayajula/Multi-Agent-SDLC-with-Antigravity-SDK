import os
import httpx
from typing import Optional

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_STT_URL = os.getenv('GEMINI_STT_URL')
GEMINI_TEXT_URL = os.getenv('GEMINI_TEXT_URL')


async def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """Send audio bytes to Gemini STT endpoint. Returns transcription string.

    If GEMINI_STT_URL or key not configured, returns a placeholder transcription.
    """
    if not GEMINI_STT_URL or not GEMINI_API_KEY:
        return "[simulated transcription] audio received"

    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
    # This is a generic POST; actual API may differ — adapt as needed.
    async with httpx.AsyncClient(timeout=60.0) as client:
        files = {"file": ("audio.webm", audio_bytes, "audio/webm")}
        resp = await client.post(GEMINI_STT_URL, headers=headers, files=files)
        resp.raise_for_status()
        data = resp.json()
        # Expecting {'transcript': '...'} or similar
        return data.get('transcript') or data.get('text') or ""


async def summarize_text(text: str, max_tokens: Optional[int] = 512) -> str:
    """Send text to Gemini text-generation endpoint for summarization.

    If GEMINI_TEXT_URL or key not configured, returns a short simulated summary.
    """
    if not GEMINI_TEXT_URL or not GEMINI_API_KEY:
        # simple heuristic summary
        return (text[:300] + '...') if len(text) > 300 else text

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": f"Summarize the following meeting transcript into concise bullet points:\n\n{text}",
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(GEMINI_TEXT_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        # Adapt to expected response shape (may differ)
        # look for 'summary' or 'output_text' or a generative 'choices' array
        if 'summary' in data:
            return data['summary']
        if 'output_text' in data:
            return data['output_text']
        if 'choices' in data and isinstance(data['choices'], list) and data['choices']:
            return data['choices'][0].get('text') or data['choices'][0].get('message') or ''
        return data.get('text') or ''
