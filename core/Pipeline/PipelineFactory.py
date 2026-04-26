from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.schema import LLMConfig, PipelineConfig, RealtimeModelConfig, STTConfig, TTSConfig, VADConfig


@dataclass(frozen=True)
class PipelineComponents:
    mode: str
    vad: Any | None = None
    stt: Any | None = None
    llm: Any | None = None
    tts: Any | None = None
    realtime: Any | None = None


def build_pipeline(
    pipeline: PipelineConfig,
    vad_config: VADConfig,
    prewarmed_vad: Any | None = None,
) -> PipelineComponents:
    vad = prewarmed_vad if prewarmed_vad is not None else build_vad(vad_config)

    if pipeline.mode == "s2s":
        return PipelineComponents(
            mode=pipeline.mode,
            llm=build_realtime(pipeline.s2s_model),
            realtime=build_realtime(pipeline.s2s_model),
        )

    return PipelineComponents(
        mode=pipeline.mode,
        vad=vad,
        stt=build_stt(pipeline.stt),
        llm=build_llm(pipeline.llm),
        tts=build_tts(pipeline.tts),
        realtime=None,
    )


def build_vad(config: VADConfig) -> Any | None:
    if config.provider == "none":
        return None
    if config.provider == "silero":
        from livekit.plugins import silero

        return silero.VAD.load()
    if config.provider == "webrtc":
        return None
    raise ValueError(f"unsupported VAD provider: {config.provider}")


def build_stt(config: STTConfig) -> Any:
    if config.provider == "livekit_inference":
        return _descriptor(config.model, config.language)
    if config.provider == "deepgram":
        from livekit.plugins import deepgram

        return deepgram.STT(model=_provider_model(config.model), language=config.language)
    if config.provider == "assemblyai":
        from livekit.plugins import assemblyai

        return assemblyai.STT(model=_provider_model(config.model), language=config.language)
    raise ValueError(f"unsupported STT provider: {config.provider}")


def build_llm(config: LLMConfig) -> Any:
    if config.provider == "livekit_inference":
        return config.model
    if config.provider == "openai":
        from livekit.plugins import openai

        if hasattr(openai, "responses"):
            return openai.responses.LLM(model=_provider_model(config.model), temperature=config.temperature)
        return openai.LLM(model=_provider_model(config.model), temperature=config.temperature)
    if config.provider == "anthropic":
        from livekit.plugins import anthropic

        return anthropic.LLM(model=_provider_model(config.model), temperature=config.temperature)
    raise ValueError(f"unsupported LLM provider: {config.provider}")


def build_tts(config: TTSConfig) -> Any:
    if config.provider == "livekit_inference":
        return _descriptor(config.model, config.voice_id)
    if config.provider == "cartesia":
        from livekit.plugins import cartesia

        return cartesia.TTS(model=_provider_model(config.model), voice=config.voice_id)
    if config.provider == "elevenlabs":
        from livekit.plugins import elevenlabs

        return elevenlabs.TTS(model=_provider_model(config.model), voice_id=config.voice_id)
    if config.provider == "openai":
        from livekit.plugins import openai

        return openai.TTS(model=_provider_model(config.model), voice=config.voice_id)
    raise ValueError(f"unsupported TTS provider: {config.provider}")


def build_realtime(config: RealtimeModelConfig | None) -> Any | None:
    if config is None:
        return None
    if config.provider == "openai_realtime":
        from livekit.plugins import openai

        return openai.realtime.RealtimeModel(
            model=config.model,
            voice=config.voice,
            modalities=config.modalities,
        )
    if config.provider == "google_realtime":
        from livekit.plugins import google

        return google.beta.realtime.RealtimeModel(model=config.model)
    if config.provider == "xai_realtime":
        from livekit.plugins import xai

        return xai.realtime.RealtimeModel(model=config.model, voice=config.voice)
    raise ValueError(f"unsupported realtime provider: {config.provider}")


def _descriptor(model: str, suffix: str | None) -> str:
    return f"{model}:{suffix}" if suffix else model


def _provider_model(model: str) -> str:
    return model.split("/", 1)[1] if "/" in model else model
