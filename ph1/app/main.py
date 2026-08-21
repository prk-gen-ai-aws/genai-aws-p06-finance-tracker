"""
Project 6 — Personal Finance Tracker Agent
Streamlit UI — Chat interface calling AgentCore Runtime with Memory
"""

import streamlit as st
import boto3
import json
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

# ── Config ──
RUNTIME_ARN = os.getenv(
    'AGENTCORE_RUNTIME_ARN',
    'arn:aws:bedrock-agentcore:us-east-1:759802535955:runtime/p06FinanceTracker_p06FinanceTracker-YPgGfK2bhQ'
)
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="💰",
    layout="wide"
)

# ── Sidebar navigation ──
st.sidebar.title("💰 Finance Tracker")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", ["Finance Tracker", "How it works", "Architecture", "About"])
st.sidebar.markdown("---")
st.sidebar.caption("Built on AWS · Powered by AgentCore")
st.sidebar.caption("Strands Agents · AgentCore Memory")


def invoke_agent(prompt: str, session_id: str) -> str:
    """Invoke AgentCore Runtime and parse SSE response."""
    try:
        client = boto3.client('bedrock-agentcore', region_name=AWS_REGION)
        payload = json.dumps({"prompt": prompt}).encode()

        response = client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier="DEFAULT"
        )

        raw = response['response'].read().decode('utf-8')
        lines = raw.split('\n')

        text_chunks = []
        for line in lines:
            if line.startswith('data: '):
                try:
                    event_data = json.loads(line[6:])
                    event = event_data.get('event', {})
                    delta = event.get('contentBlockDelta', {}).get('delta', {})
                    text = delta.get('text', '')
                    if text:
                        text_chunks.append(text)
                except json.JSONDecodeError:
                    continue

        return ''.join(text_chunks) if text_chunks else "No response received."

    except Exception as e:
        return f"❌ Error: {str(e)}"


# ── Session management ──
if 'session_id' not in st.session_state:
    raw_id = str(uuid.uuid4()).replace('-', '') + str(uuid.uuid4()).replace('-', '')
    st.session_state.session_id = raw_id[:40]

if 'messages' not in st.session_state:
    st.session_state.messages = []


# ============================================================
# PAGE 1: FINANCE TRACKER
# ============================================================
if page == "Finance Tracker":
    st.title("💰 Personal Finance Tracker Agent")
    st.subheader("Track your spending with AI — remembers your budget across sessions")
    st.markdown("---")

    # Example prompts on first load
    if not st.session_state.messages:
        st.markdown("### 💡 Try asking:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎯 Set my monthly budget"):
                st.session_state.pending_prompt = "My monthly budget is $2,000 for food, transport and entertainment"
            if st.button("🍔 Log food expense"):
                st.session_state.pending_prompt = "I spent $150 on food and $45 on transport today"
        with col2:
            if st.button("☕ Add more spending"):
                st.session_state.pending_prompt = "I spent $20 more on coffee today"
            if st.button("📊 Check budget status"):
                st.session_state.pending_prompt = "What is my budget status?"

    # Chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle button clicks
    if 'pending_prompt' in st.session_state:
        prompt = st.session_state.pop('pending_prompt')
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Tracking your finances..."):
                response = invoke_agent(prompt, st.session_state.session_id)
            st.markdown(response.replace("$", "\$"))
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

    # Chat input
    if prompt := st.chat_input("Track your spending or ask about your budget..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Tracking your finances..."):
                response = invoke_agent(prompt, st.session_state.session_id)
            st.markdown(response.replace("$", "\$"))
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Session info + reset
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"Session ID: {st.session_state.session_id[:16]}...")
    with col2:
        if st.button("🔄 New Session"):
            st.session_state.messages = []
            raw_id = str(uuid.uuid4()).replace('-', '') + str(uuid.uuid4()).replace('-', '')
            st.session_state.session_id = raw_id[:40]
            st.rerun()

    st.info("🧠 This agent remembers your budget across sessions — come back tomorrow and it will recall your spending history!")


# ============================================================
# PAGE 2: HOW IT WORKS
# ============================================================
elif page == "How it works":
    st.title("How it works")
    st.markdown("---")
    st.markdown("""
    This finance tracker uses an **AI agent with persistent memory** — it remembers your 
    budget goals and spending history across all conversations, even days later.
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Step 1 — You tell it your budget")
        st.markdown("""
        Say "My monthly budget is $2,000 for food, transport and entertainment."
        The agent stores this in **AgentCore Memory** — a managed AWS memory service
        that persists across sessions.
        """)

        st.markdown("### Step 2 — Log your spending")
        st.markdown("""
        Tell it what you spend:
        - "I spent $150 on food and $45 on transport"
        - "$20 more on coffee today"
        - "I saved $15 by cooking at home"
        
        The agent does running calculations and updates your totals.
        """)

    with col2:
        st.markdown("### Step 3 — Come back anytime")
        st.markdown("""
        Start a **brand new session** tomorrow and ask:
        "What is my budget status?"
        
        The agent recalls your budget and spending history from
        **long-term memory** — no need to repeat yourself.
        """)

        st.markdown("### Step 4 — Get insights")
        st.markdown("""
        The agent gives you:
        - Running totals by category
        - Budget remaining and % used
        - Savings recommendations
        - Alerts when approaching limits
        """)

    st.markdown("---")
    st.markdown("### Memory architecture")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Session Summaries**")
        st.markdown("Summarizes each conversation — primary cross-session recall mechanism")
    with col2:
        st.markdown("**Finance Facts**")
        st.markdown("Extracts structured budget facts — 'Budget status: $2,000 total, $195 spent'")
    with col3:
        st.markdown("**Budget Preferences**")
        st.markdown("Remembers behavioral patterns — categories you track, saving habits")

    st.markdown("---")
    st.markdown("### Incremental updates supported")
    st.markdown("""
    | What you say | What happens |
    |---|---|
    | "I spent $150 on food" | Logs and updates food total |
    | "$20 more on coffee" | ADDS to existing food total |
    | "I saved $15 by cooking" | SUBTRACTS from food total |
    | "Increase my budget to $2,500" | Updates budget goal |
    """)


# ============================================================
# PAGE 3: ARCHITECTURE
# ============================================================
elif page == "Architecture":
    st.title("Architecture")
    st.markdown("---")
    st.markdown("""
    ### Stateful Agent Pipeline on AWS

    P06 introduces **AgentCore Memory** — the agent remembers users across sessions.
    Unlike P05 (stateless tools), P06 maintains a persistent financial profile per user.
    """)

    import os as _os
    diagram_path = _os.path.join(_os.path.dirname(__file__), '..', 'docs', 'architecture-ph1.png')
    if _os.path.exists(diagram_path):
        st.image(diagram_path)
    else:
        st.info("📐 Architecture diagram: ph1/docs/architecture-ph1.png")

    st.markdown("---")
    st.markdown("### Component breakdown")

    components = {
        "Streamlit (local)": "Chat UI. Sends prompt to AgentCore Runtime via boto3 invoke_agent_runtime(). Session ID preserved across turns.",
        "Amazon Bedrock AgentCore Runtime": "Hosts the Strands agent. Manages session isolation and streaming. Deployed via AgentCore CLI + CDK.",
        "Strands Agent (Claude Haiku 4.5)": "Autonomous agent with no Lambda tools. Uses AgentCore Memory for all context. Handles incremental updates, corrections, and calculations.",
        "AgentCore Memory": "Managed memory service with 3 strategies: SpendingSummarizer (session summaries), FinanceFactsCustom (budget facts), BudgetPreferences (habits). Persists across sessions via actor_id.",
        "Memory Strategies": "SpendingSummarizer → /summaries/{actorId}/ (scores 0.51-0.65). FinanceFactsCustom → /finance/{actorId}/ (scores 0.44-0.50). BudgetPreferences → /preferences/{actorId}/ (scores 0.37-0.42).",
        "IAM (Memory Execution Role)": "p06-memory-execution-role allows AgentCore Memory to invoke Bedrock models for custom strategy extraction.",
        "AgentCore CLI + CDK": "agentcore deploy zips ph1/agent/ and deploys Runtime. CDK manages CloudFormation stack."
    }

    for component, description in components.items():
        with st.expander(f"**{component}**"):
            st.markdown(description)

    st.markdown("---")
    st.markdown("### Key difference from P05")
    st.markdown("""
    | | P05 (Cost Analyzer) | P06 (Finance Tracker) |
    |---|---|---|
    | Tools | Lambda (Cost Explorer API) | None — memory only |
    | Memory | NullConversationManager | AgentCoreMemorySessionManager |
    | State | Stateless per session | Persistent across sessions |
    | Recall | Session only | Days/weeks later |
    | IAM | Lambda invoke | Memory execution role |
    """)


# ============================================================
# PAGE 4: ABOUT
# ============================================================
elif page == "About":
    st.title("About this project")
    st.markdown("---")
    st.markdown("### Gen AI on AWS — Portfolio Project 6")
    st.markdown("[View on GitHub](https://github.com/prk-gen-ai-aws/genai-aws-p06-finance-tracker)")
    st.markdown("---")
    st.markdown("""
    P06 introduces **AgentCore Memory** — persistent cross-session memory for AI agents.
    
    Unlike P05 which used Lambda tools for real-time data, P06 demonstrates that
    an agent with good memory can deliver rich, personalized experiences
    with zero external tool calls — just Bedrock reasoning + persistent memory.

    Built with real-world practices:
    - **AgentCore Memory** — 3 strategies: summarization, semantic facts, user preferences
    - **Custom memory strategy** — finance-domain extraction prompt for better retrieval
    - **Cross-session recall** — agent remembers budget and spending history across days
    - **Incremental updates** — handles "$20 more", "I saved $15", corrections
    - **Session continuity** — LRU cache (128 sessions) for within-session context
    - **No Lambda tools** — pure memory + Bedrock reasoning
    """)

    st.markdown("---")
    st.markdown("### Memory improvement journey")
    st.markdown("""
    | Strategy | Format | Score | Result |
    |---|---|---|---|
    | Built-in SEMANTIC | "The user spent $150 on food" | 0.36 | Below threshold |
    | Custom v1 | "Budget category: food $150" | 0.42 | Improved |
    | Custom v2 | "Budget status: food - $150 of $667" | 0.46-0.50 | Above threshold ✅ |
    
    Key insight: Align extraction vocabulary with query vocabulary for better retrieval.
    Used custom strategies instead of built-in for domain-specific optimization.
    """)

    st.markdown("---")
    st.markdown("### Things to consider at scale")
    st.markdown("""
    | Concern | Consideration |
    |---|---|
    | **Multi-user** | Use unique actor_id per user |
    | **Memory TTL** | 90 day default — configure per use case |
    | **Extraction timing** | Async, ~1-30 min — design UX accordingly |
    | **Threshold tuning** | Different namespaces need different thresholds |
    | **Custom vs built-in** | Use custom strategies for domain-specific retrieval |
    """)

    st.markdown("---")
    st.markdown("> Part of an ongoing series exploring Gen AI on AWS.")
    st.markdown("> Browse all projects: https://github.com/prk-gen-ai-aws")
