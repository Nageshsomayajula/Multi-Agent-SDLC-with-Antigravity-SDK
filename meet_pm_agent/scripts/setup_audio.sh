#!/usr/bin/env bash
set -euo pipefail

SINK_NAME="${1:-MeetAgentSink}"

if ! command -v pactl >/dev/null 2>&1; then
  echo "pactl is required but was not found in PATH." >&2
  exit 1
fi

if ! pactl list short sinks | grep -q "${SINK_NAME}"; then
  pactl load-module module-null-sink "sink_name=${SINK_NAME}" "sink_properties=device.description=${SINK_NAME}"
fi

pactl set-default-sink "${SINK_NAME}"
pactl set-default-source "${SINK_NAME}.monitor"

echo "Virtual microphone ready."
echo "Sink: ${SINK_NAME}"
echo "Source: ${SINK_NAME}.monitor"
