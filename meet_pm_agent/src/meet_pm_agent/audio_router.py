from __future__ import annotations
import asyncio
import logging
import os
import shutil
from pathlib import Path

LOGGER = logging.getLogger(__name__)

VBCABLE_DEVICE_NAME = "VB-Audio Virtual C"  # Matches "Speakers (2- VB-Audio Virtual C, MME)"


class VirtualMicrophone:
    """Routes audio through VB-Audio Virtual Cable on Windows (MME, 0 in / 16 out)."""

    def __init__(self, sink_name: str = VBCABLE_DEVICE_NAME) -> None:
        self.sink_name = sink_name
        self._device_index: int | None = None

    async def ensure_ready(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            raise RuntimeError("sounddevice is required: pip install sounddevice")

        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if VBCABLE_DEVICE_NAME.lower() in dev["name"].lower() and dev["max_output_channels"] > 0:
                self._device_index = i
                LOGGER.info("Found VB-Audio Virtual Cable at device index %d: %s", i, dev["name"])
                break

        if self._device_index is None:
            raise RuntimeError(
                f"VB-Audio Virtual Cable output device not found. "
                f"Ensure '{VBCABLE_DEVICE_NAME}' is installed and visible in Windows audio devices."
            )

    async def play_file(self, path: Path) -> None:
        if self._device_index is None:
            await self.ensure_ready()

        player = self._pick_player()
        LOGGER.info("Playing synthesized response through VB-Audio Virtual Cable (device index %d)", self._device_index)

        if player == "ffplay":
            await self._run_checked(
                "ffplay",
                "-nodisp",
                "-autoexit",
                "-loglevel", "error",
                "-audio_device", str(self._device_index),  # route to VB cable
                str(path),
            )
        elif player == "mpv":
            await self._run_checked(
                "mpv",
                "--really-quiet",
                f"--audio-device=wasapi/{VBCABLE_DEVICE_NAME}",
                str(path),
            )
        else:
            # Fallback: use sounddevice + soundfile directly
            await asyncio.get_event_loop().run_in_executor(
                None, self._play_with_sounddevice, path
            )

    def _play_with_sounddevice(self, path: Path) -> None:
        try:
            import sounddevice as sd
            import soundfile as sf
        except ImportError:
            raise RuntimeError("Install sounddevice and soundfile: pip install sounddevice soundfile")

        data, samplerate = sf.read(str(path), dtype="float32")
        sd.play(data, samplerate=samplerate, device=self._device_index)
        sd.wait()

    def _pick_player(self) -> str:
        for candidate in ("ffplay", "mpv"):
            if shutil.which(candidate):
                return candidate
        return "sounddevice"  # built-in fallback

    async def _run_checked(self, *args: str, env: dict[str, str] | None = None) -> None:
        process = await asyncio.create_subprocess_exec(
            *args,
            env=env or os.environ.copy(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(args)}\n"
                f"stdout: {stdout.decode()}\nstderr: {stderr.decode()}"
            )

    async def _run_capture(self, *args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(args)}\n"
                f"stdout: {stdout.decode()}\nstderr: {stderr.decode()}"
            )
        return stdout.decode()