import asyncio
from livekit.agents import llm
from livekit.plugins import openai
import logging

logger = logging.getLogger("observer-agent")

class ObserverAgent:
    def __init__(self, chat_ctx: llm.ChatContext):
        self.chat_ctx = chat_ctx
        self.llm = openai.LLM(model="gpt-4o-mini")

    async def start(self):
        """
        Background task to monitor conversation asynchronously.
        Evaluates the context and can inject corrective prompts without
        blocking the primary VoicePipelineAgent loop.
        """
        logger.info("Observer LLM started to monitor conversation.")
        while True:
            await asyncio.sleep(10)
            
            # Evaluates the conversation length or safety rules here
            if len(self.chat_ctx.messages) > 15:
                logger.info("Observer: Conversation is getting long, might need summarization.")
                # We could inject context here if required for safety:
                # self.chat_ctx.append(role="system", text="User has been speaking for a while. Be concise.")
