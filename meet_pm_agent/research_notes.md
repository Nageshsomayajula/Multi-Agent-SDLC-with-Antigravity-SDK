# Research Notes

## Google Meet bot implementation patterns

Source: Recall.ai article, "How to Build a Google Meet Bot from Scratch" (accessed 2026-04-21).

Key findings:

- A practical browser-based Meet bot can be built with **Playwright** controlling Chromium.
- A common low-friction approach is to **enable captions and scrape live captions from the DOM** instead of attempting low-level meeting audio extraction first.
- Captions can be buffered in memory as transcript segments with fields such as `speaker`, `text`, `start`, and `end`.
- Reliability risks include **DOM fragility**, expired authentication state, CAPTCHA prompts, and rate/session issues.
- Containerized deployment is a common next step after a local prototype.

## Claude Python SDK usage

Source: Claude API docs, Python SDK page (accessed 2026-04-21).

Key findings:

- Install with `pip install anthropic`.
- Basic client pattern:

```python
from anthropic import Anthropic
client = Anthropic()
message = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}],
)
```

- Responses are read from `message.content`.
- Streaming is also supported, but non-streaming is sufficient for an MVP response loop.

## Design implication for this project

For the initial codebase, prefer a **caption-driven project manager agent** with optional text-to-speech output and browser join automation. This is more realistic and maintainable than trying to build full duplex browser audio understanding in the first version.
