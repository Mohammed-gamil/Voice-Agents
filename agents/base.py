from __future__ import annotations

from typing import Any

from livekit.agents.pipeline import VoicePipelineAgent
from livekit.agents import llm

from config.schema import TenantConfig
from tools.custom_actions.registry import load_custom_tools


class TenantAgent(VoicePipelineAgent):
    def __init__(
        self,
        config: TenantConfig,
        prompt_key: str,
        vad: Any | None,
        stt: Any | None,
        llm_plugin: Any | None,
        tts: Any | None,
        turn_handling: Any | None = None,
        *,
        chat_ctx: llm.ChatContext | None = None,
        include_custom_tools: bool = True,
    ) -> None:
        self.config = config
        self.prompt_key = prompt_key
        self.agent_name = self.__class__.__name__
        
        # Tools initialization (normally fnc_ctx)
        tools = load_custom_tools(config.tools.custom_actions) if include_custom_tools else None
        
        if chat_ctx is None:
            chat_ctx = llm.ChatContext()
            
        instructions = self._instructions()
        if instructions:
            chat_ctx.append(role="system", text=instructions)
            
        super().__init__(
            vad=vad,
            stt=stt,
            llm=llm_plugin,
            tts=tts,
            chat_ctx=chat_ctx,
            turn_detector=turn_handling,
            # fnc_ctx=tools if tools else None,
        )

    def _instructions(self) -> str:
        instructions = [self.config.prompt(self.prompt_key)]
        if self.config.conversation.scenarios:
            scenario_lines = [
                f"- {name}: {scenario.description}\n{scenario.instructions}"
                for name, scenario in self.config.conversation.scenarios.items()
            ]
            instructions.append(
                "Scenario handling rules. Use these when the conversation matches the scenario:\n"
                + "\n".join(scenario_lines)
            )
        return "\n\n".join(instructions)
