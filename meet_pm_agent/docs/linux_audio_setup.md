# Linux Audio Setup for the Google Meet Agent

The bot speaks back into Google Meet by generating speech audio locally and routing that audio into a **virtual microphone**. The implementation in this repository assumes a Linux desktop with **PulseAudio** or **PipeWire compatibility tools** available through `pactl`.

## Conceptual model

| Audio object | Purpose |
| --- | --- |
| Null sink | Receives the bot's synthesized speech playback |
| Monitor source | Exposes the sink's output as an input device |
| Google Meet microphone | Uses the monitor source as the active microphone |

In practical terms, the bot plays its response into a virtual speaker, and Google Meet listens to the monitor stream of that speaker as if it were a microphone.

## One-time dependency installation

On Ubuntu, install the common utilities below:

```bash
sudo apt-get update
sudo apt-get install -y pulseaudio-utils ffmpeg
```

If your system uses PipeWire, `pactl` usually remains compatible. If `ffplay` is not available, you may alternatively install `mpv`.

## Manual test setup

Create a virtual sink:

```bash
pactl load-module module-null-sink sink_name=MeetAgentSink sink_properties=device.description=MeetAgentSink
```

Set it as the default sink and source:

```bash
pactl set-default-sink MeetAgentSink
pactl set-default-source MeetAgentSink.monitor
```

Verify that the source exists:

```bash
pactl list short sources | grep MeetAgentSink
```

## Browser-side requirement

When Chromium opens Google Meet, confirm that the selected microphone is the monitor source associated with the sink. In many Linux desktop environments, setting the default source before the browser joins is sufficient. If Google Meet has already cached another input device, open Meet settings and switch the microphone to the virtual source manually once; the persistent browser profile will usually retain it.

## Operational notes

| Issue | Likely cause | Recommended action |
| --- | --- | --- |
| Bot joins but nobody hears it | Meet is using a different microphone | Re-select the virtual source in Meet settings |
| Playback command fails | No supported audio player installed | Install `ffmpeg`, `mpv`, or another supported player |
| `pactl` errors | Audio service not running | Restart user audio service or verify PipeWire compatibility |
| Echo or feedback | Physical microphone still active elsewhere | Keep the real microphone muted or disconnected |

## Suggested first-run procedure

1. Log into Google in the persistent profile.
2. Join a test Meet manually with the same profile.
3. Set the microphone to `MeetAgentSink.monitor`.
4. Turn on captions manually once to confirm the UI language and selectors.
5. Run the bot against a private test meeting.

This staged setup reduces the amount of first-run troubleshooting when you move from local development to a real meeting workflow.
