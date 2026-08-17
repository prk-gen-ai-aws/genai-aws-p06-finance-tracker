"""
Project 6 — Personal Finance Tracker Agent
Strands Agent with AgentCore Memory — no Lambda tools needed
Memory stores budget goals, spending history, category preferences
ph1/agent/main.py
"""

import os
import uuid
from collections import OrderedDict
from strands import Agent
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from dotenv import load_dotenv

load_dotenv()

# ── AgentCore Runtime app ──
app = BedrockAgentCoreApp()
log = app.logger

# ── Config ──
region = os.getenv('AWS_REGION', 'us-east-1')
MEMORY_ID = os.getenv('AGENTCORE_MEMORY_ID', 'p06FinanceTrackerMemory-WfrQzfDyWb')
ACTOR_ID = "default-user"  # single user for ph1
MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def load_model():
    return BedrockModel(
        model_id=MODEL_ID,
        region_name=region
    )


# ── System prompt ──
SYSTEM_PROMPT = """You are a Personal Finance Tracker Agent — a helpful, 
friendly financial companion that helps users track their spending and stay 
within budget.

YOUR CAPABILITIES:
- Remember the user's budget goals across ALL sessions (powered by AgentCore Memory)
- Track spending by category (food, transport, entertainment, etc.)
- Do running calculations — handle incremental updates like "$20 more" or "another $50"
- Handle corrections like "I saved $15" or "actually it was $80 not $100"
- Recall previous conversations and build on them

HOW TO HANDLE SPENDING UPDATES:
- When user says "I spent $X on Y" → log it and update running total
- When user says "I spent $X more" → ADD to the existing category total
- When user says "I saved $X" → SUBTRACT from the relevant category
- Always show: category totals, overall total spent, budget remaining, % used

OUTPUT FORMAT:
- Always confirm what you've recorded
- Show a brief spending summary after each update:
  📊 Budget: $X,XXX | Spent: $XXX | Remaining: $XXX (XX% left)
- Break down by category when tracking multiple categories
- Use emojis sparingly for clarity (📊 💰 ✅ ⚠️)

BUDGET ALERTS:
- Warn (⚠️) when user has used more than 75% of budget
- Celebrate (🎉) when user mentions saving money
- Give encouragement when user is on track

DONTS:
- Do NOT make up spending figures — only use what the user tells you
- Do NOT provide investment advice
- Do NOT be preachy about spending habits
- Do NOT forget previous context — always build on what was shared before
- Do NOT reset spending unless user explicitly asks to start fresh

REMEMBER: Your memory persists across browser sessions.
Even if the user starts a new conversation, you remember their budget,
categories, and spending history."""


# ── Session cache ──
def agent_factory():
    cache = OrderedDict()

    def get_or_create_agent(session_id: str) -> Agent:
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)

        # Create AgentCore Memory session manager
        memory_config = AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=ACTOR_ID,
            retrieval_config={
                f"/preferences/{ACTOR_ID}/": RetrievalConfig(
                    top_k=5,
                    relevance_score=0.5
                ),
                f"/summaries/{ACTOR_ID}/{session_id}/": RetrievalConfig(
                    top_k=5,
                    relevance_score=0.5
                )
            }
        )
        session_manager = AgentCoreMemorySessionManager(
            agentcore_memory_config=memory_config,
            region_name=region
        )

        cache[session_id] = Agent(
            model=load_model(),
            system_prompt=SYSTEM_PROMPT,
            tools=[],  # No Lambda tools — Memory + Bedrock reasoning only
            session_manager=session_manager
        )
        return cache[session_id]

    return get_or_create_agent


get_or_create_agent = agent_factory()


def _extract_prompt(payload: dict):
    """Extract prompt from AgentCore payload."""
    if "messages" in payload:
        return payload["messages"]
    return payload.get("prompt", "")


# ── AgentCore Runtime entry point ──
@app.entrypoint
async def invoke(payload, context):
    log.info("Finance Tracker Agent invoked")

    session_id = getattr(context, 'session_id', str(uuid.uuid4()))
    agent = get_or_create_agent(session_id)
    prompt = _extract_prompt(payload)

    try:
        async for event in agent.stream_async(prompt):
            if not isinstance(event, dict) or "event" not in event:
                continue
            cbs = event["event"].get("contentBlockStart")
            if cbs is not None and not cbs.get("start"):
                continue
            yield event
    finally:
        # Flush memory events to trigger long-term strategy extraction
        try:
            session_manager = agent.conversation_manager
            if hasattr(session_manager, 'close'):
                await session_manager.close()
        except Exception as e:
            log.warning(f"Memory flush warning: {e}")


# ── Local development entry point ──
if __name__ == "__main__":
    app.run()
