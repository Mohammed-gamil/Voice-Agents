from __future__ import annotations

from livekit.agents import JobProcess
from livekit.plugins import silero


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()
