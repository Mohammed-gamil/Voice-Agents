from __future__ import annotations

from livekit.agents import Agent, ChatContext

from config.schema import TenantConfig
from tools.custom_actions.registry import load_custom_tools


class TenantAgent(Agent):
    def __init__(
        self,
        config: TenantConfig,
        prompt_key: str,
        *,
        chat_ctx: ChatContext | None = None,
        include_custom_tools: bool = True,
    ) -> None:
        self.config = config
        self.prompt_key = prompt_key
        self.agent_name = self.__class__.__name__
        tools = load_custom_tools(config.tools.custom_actions) if include_custom_tools else []
        super().__init__(
            instructions=self._instructions(),
            chat_ctx=chat_ctx,
            tools=tools,
        )

    async def on_enter(self) -> None:
        greeting = self.config.conversation.greetings.get(self.agent_name)
        if greeting:
            await self.session.generate_reply(
                instructions=f"Say exactly this greeting, naturally: {greeting}",
                allow_interruptions=True,
            )
            return
        await self.session.generate_reply()

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
