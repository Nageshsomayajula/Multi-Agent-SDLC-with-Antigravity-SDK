from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Error, Page, TimeoutError, async_playwright

from .config import Settings

LOGGER = logging.getLogger(__name__)


class GoogleMeetBot:
    """Controls a persistent Chromium session to join and operate a Google Meet."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.playwright = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> "GoogleMeetBot":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.settings.meet_profile_dir),
            headless=self.settings.meet_headless,
            channel=self.settings.browser_channel,
            slow_mo=self.settings.browser_slow_mo_ms,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--use-fake-ui-for-media-stream",
                "--disable-infobars",
                "--start-maximized",
            ],
            viewport={"width": 1440, "height": 960},
        )

        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()

        await self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """
        )

    async def close(self) -> None:
        if self.context is not None:
            await self.context.close()
        if self.playwright is not None:
            await self.playwright.stop()

    async def join(self, meet_url: str) -> None:
        if self.page is None:
            raise RuntimeError("Browser page is not initialized.")

        LOGGER.info("Opening Meet URL: %s", meet_url)
        await self.page.goto(meet_url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(5000)

        await self._dismiss_popups()
        await self._prepare_prejoin_state()
        await self._join_call()
        await self.page.wait_for_timeout(5000)
        await self.enable_captions()

    async def _dismiss_popups(self) -> None:
        assert self.page is not None
        labels = [
            "Got it",
            "Dismiss",
            "Close",
            "Not now",
        ]
        for label in labels:
            locator = self.page.get_by_role("button", name=label)
            try:
                if await locator.count() > 0:
                    await locator.first.click(timeout=1000)
                    await self.page.wait_for_timeout(400)
            except Error:
                continue

    async def _prepare_prejoin_state(self) -> None:
        assert self.page is not None
        await self._ensure_button_state(off_label="Turn off microphone", on_label="Turn on microphone", want_on=False)
        await self._ensure_button_state(off_label="Turn off camera", on_label="Turn on camera", want_on=False)

    async def _ensure_button_state(self, off_label: str, on_label: str, want_on: bool) -> None:
        assert self.page is not None
        on_locator = self.page.get_by_role("button", name=on_label)
        off_locator = self.page.get_by_role("button", name=off_label)

        try:
            if want_on:
                if await on_locator.count() > 0:
                    await on_locator.first.click(timeout=2000)
            else:
                if await off_locator.count() > 0:
                    await off_locator.first.click(timeout=2000)
            await self.page.wait_for_timeout(500)
        except Error:
            LOGGER.warning("Could not set device state for labels '%s'/'%s'", off_label, on_label)

    async def _join_call(self) -> None:
        assert self.page is not None
        join_buttons = [
            self.page.get_by_role("button", name="Join now"),
            self.page.get_by_role("button", name="Ask to join"),
        ]

        for locator in join_buttons:
            try:
                if await locator.count() > 0:
                    await locator.first.click(timeout=self.settings.join_timeout_seconds * 1000)
                    LOGGER.info("Join button clicked.")
                    return
            except Error:
                continue

        raise TimeoutError("Could not find a Join now or Ask to join button.")

    async def enable_captions(self) -> None:
        assert self.page is not None
        candidate_labels = [
            "Turn on captions",
            "Captions",
            "Turn on captions (c)",
        ]
        for label in candidate_labels:
            locator = self.page.get_by_role("button", name=label)
            try:
                if await locator.count() > 0:
                    await locator.first.click(timeout=3000)
                    LOGGER.info("Captions enabled via button: %s", label)
                    return
            except Error:
                continue

        try:
            await self.page.keyboard.press("c")
            LOGGER.info("Attempted to enable captions via keyboard shortcut.")
        except Error:
            LOGGER.warning("Could not toggle captions.")

    async def post_chat_message(self, text: str) -> bool:
        assert self.page is not None
        try:
            chat_button = self.page.get_by_role("button", name="Chat with everyone")
            if await chat_button.count() == 0:
                chat_button = self.page.get_by_role("button", name="Open in-call messages")
            await chat_button.first.click(timeout=3000)
            await self.page.wait_for_timeout(500)
            input_box = self.page.locator("textarea, div[contenteditable='true']").last
            await input_box.fill(text)
            await self.page.keyboard.press("Enter")
            return True
        except Error:
            LOGGER.exception("Failed to post chat message.")
            return False

    async def is_still_in_meeting(self) -> bool:
        assert self.page is not None
        try:
            leave_button = self.page.get_by_role("button", name="Leave call")
            if await leave_button.count() > 0:
                return True
            end_button = self.page.get_by_role("button", name="End call")
            return await end_button.count() > 0
        except Error:
            return False

    async def read_caption_rows(self) -> list[tuple[str, str]]:
        assert self.page is not None
        payload = await self.page.evaluate(
            """
            () => {
              const textOf = (el) => (el && el.textContent ? el.textContent.replace(/\s+/g, ' ').trim() : '');
              const candidates = [];
              const regions = Array.from(document.querySelectorAll('[aria-live="polite"], [aria-live="assertive"]'));
              for (const region of regions) {
                const blocks = Array.from(region.querySelectorAll('div, span'));
                for (const block of blocks) {
                  const speakerEl = block.querySelector('[data-self-name], [data-participant-name], [class*="speaker"], [class*="name"]');
                  const textEl = block.querySelector('[class*="caption"], [class*="text"], span, div');
                  const speaker = textOf(speakerEl);
                  const text = textOf(textEl || block);
                  if (speaker && text && text !== speaker) {
                    candidates.push({ speaker, text });
                  }
                }
              }

              if (candidates.length === 0) {
                const lines = [];
                for (const node of Array.from(document.querySelectorAll('div, span'))) {
                  const raw = textOf(node);
                  if (!raw || raw.length < 8 || raw.length > 240) continue;
                  const parts = raw.split(':');
                  if (parts.length >= 2) {
                    const speaker = parts[0].trim();
                    const text = parts.slice(1).join(':').trim();
                    if (speaker && text) {
                      lines.push({ speaker, text });
                    }
                  }
                }
                return lines.slice(-8);
              }

              const compact = [];
              const seen = new Set();
              for (const item of candidates.slice(-20)) {
                const key = `${item.speaker}::${item.text}`;
                if (!seen.has(key)) {
                  seen.add(key);
                  compact.push(item);
                }
              }
              return compact.slice(-8);
            }
            """
        )
        if not payload:
            return []
        return [(item.get("speaker", ""), item.get("text", "")) for item in payload]

    async def save_debug_snapshot(self, name: str) -> Path:
        assert self.page is not None
        target = self.settings.artifacts_dir / f"{name}.png"
        await self.page.screenshot(path=str(target), full_page=True)
        return target

    async def dump_page_text(self, name: str) -> Path:
        assert self.page is not None
        target = self.settings.artifacts_dir / f"{name}.json"
        content = {
            "url": self.page.url,
            "title": await self.page.title(),
            "caption_rows": await self.read_caption_rows(),
        }
        target.write_text(json.dumps(content, indent=2), encoding="utf-8")
        return target

    async def wait(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
