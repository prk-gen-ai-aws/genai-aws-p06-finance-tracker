# Personal Finance Tracker Agent
Stateful personal finance tracker agent on AWS — powered by Amazon Bedrock AgentCore Runtime and AgentCore Memory. Track your spending in natural language and the agent remembers your budget across sessions.

Ask anything about your finances: log expenses, track categories, get budget status, handle corrections like "I spent $20 more" or "I saved $15 by cooking at home" — the agent remembers everything across conversations.

Real-world use case: A personal finance companion that builds a persistent financial profile over time — no app to install, no spreadsheet to update, just natural conversation.

[View on GitHub](https://github.com/prk-gen-ai-aws/genai-aws-p06-finance-tracker)

---

## How It Works

1. You tell the agent your budget: "My monthly budget is $2,000 for food, transport and entertainment"
2. You log expenses as they happen: "I spent $150 on food and $45 on transport today"
3. The agent stores everything in AgentCore Memory — persisted across sessions
4. Come back tomorrow in a new session and ask: "What is my budget status?"
5. The agent recalls your budget, spending history, and preferences automatically

Note: Cross-session recall is available after long-term memory extraction completes. This is an asynchronous process — AWS does not specify an exact SLA. In our testing, extraction completed within approximately 1-30 minutes after a session ends.

---

## What Makes This Different from P05

P05 (AWS Cost Analyzer) used Lambda tools to fetch real-time data. P06 uses no Lambda tools at all — the agent relies entirely on AgentCore Memory and Bedrock reasoning.

```
P05: Streamlit → AgentCore Runtime → Agent → Lambda tools → Cost Explorer API
P06: Streamlit → AgentCore Runtime → Agent ↔ AgentCore Memory (no tools)
```

This demonstrates that an agent with good persistent memory can deliver rich, personalized experiences without any external data sources.

---

## Supported Interactions

The agent handles natural language for all of these:

- Set budget: "My monthly budget is $2,000 for food, transport and entertainment"
- Log expense: "I spent $150 on food and $45 on transport today"
- Incremental update: "I spent $20 more on coffee" (adds to existing total)
- Savings correction: "I saved $15 by cooking at home" (subtracts from total)
- Status check: "What is my budget status?"
- Adjustment: "Increase my budget to $2,500"
- Category check: "How much have I spent on food?"
- Reset: "Start fresh for next month"

---

## Architecture

Architecture diagram: ph1/docs/architecture-ph1.png

Components:
- Streamlit (local) sends prompt to AgentCore Runtime via boto3 invoke_agent_runtime()
- AgentCore Runtime hosts the Strands agent — managed, auto-scaling, session-isolated
- Strands Agent (Claude Haiku 4.5) reasons about spending and maintains financial context
- AgentCore Memory provides persistent cross-session memory via 3 strategies
- No Lambda tools, no DynamoDB, no API Gateway

---

## Memory Architecture

AgentCore Memory uses three complementary strategies:

SpendingSummarizer (SUMMARIZATION):
  Creates session summaries after each conversation
  Namespace: /summaries/{actorId}/{sessionId}/
  Retrieved via: /summaries/{actorId}/ (prefix search across all sessions)
  Cosine similarity scores: 0.51-0.65 (primary recall mechanism)

FinanceFactsCustom (CUSTOM SEMANTIC):
  Extracts structured financial facts using finance-domain extraction prompt
  Format: "Budget status: food - $150 spent of $667 budget, $517 remaining"
  Namespace: /finance/{actorId}/
  Cosine similarity scores: 0.44-0.50

BudgetPreferences (USER PREFERENCE):
  Extracts behavioral patterns and spending habits
  Namespace: /preferences/{actorId}/
  Cosine similarity scores: 0.37-0.42

Note: SpendingSummarizer is the most reliable strategy for cross-session recall because
session summaries mirror user query vocabulary (scoring 0.51-0.65 vs threshold 0.45-0.5).

---

## Memory Improvement Journey

Built-in SEMANTIC strategy:
  Extracted: "The user has a monthly budget of $2,000 covering food, transport..."
  Score against "budget status" query: 0.36 (below threshold)

Custom strategy v1 (explicit formats):
  Extracted: "Budget category: food budget $X, spent $X"
  Score: 0.42 (improved, still below 0.45)

Custom strategy v2 (budget-status aligned):
  Extracted: "Budget status: food - $150 spent of $667 budget, $517 remaining"
  Score: 0.44-0.50 (above 0.45 threshold)

Key insight: Align extraction vocabulary with query vocabulary for better retrieval.
Used custom strategies instead of built-in for domain-specific optimization.

---

## Project Structure

    genai-aws-p06-finance-tracker/
    ph1/                         <- phase 1
      agent/                     <- Strands agent code
        main.py                  <- agent entry point with AgentCoreMemorySessionManager
        pyproject.toml           <- uv project file (required by AgentCore CLI)
      app/                       <- Streamlit UI (runs locally)
        main.py                  <- chat interface
        requirements.txt         <- app dependencies
      docs/                      <- architecture diagrams
      sample-queries/            <- example questions for the agent
    agentcore/                   <- AgentCore CLI scaffold
      agentcore.json             <- agent config (name, codeLocation, runtimeVersion, env vars)
      cdk/                       <- CDK deployment code (TypeScript)
    README.md
    VERSIONS.md
    .gitignore
    .env.example

---

## Tech Stack

- Frontend: Streamlit (Python) — runs locally
- Agent Framework: Strands Agents v1.0
- Agent Runtime: Amazon Bedrock AgentCore Runtime (managed, CDK deployed)
- Memory: Amazon Bedrock AgentCore Memory (3 strategies)
- AI Model: Amazon Bedrock — Claude Haiku 4.5
- IaC: CDK via AgentCore CLI (Runtime) + IAM via AWS CLI (memory execution role)
- Language: Python 3.12

---

## Prerequisites

- AWS account with CLI configured (aws configure)
- Python 3.12+
- Node.js 18+ (required for AgentCore CLI and CDK)
- Bedrock model access: Go to AWS Console → Amazon Bedrock → Model access → Request access → Enable "Claude Haiku 4.5 20251001"

One-time installations:
    sudo npm install -g @aws/agentcore
    sudo npm install -g aws-cdk
    pip install strands-agents strands-agents-tools bedrock-agentcore
    curl -LsSf https://astral.sh/uv/install.sh | sh

Note: Throughout this guide, replace YOUR_ACCOUNT_ID with your 12-digit AWS account ID.
You can find it by running: aws sts get-caller-identity --query Account --output text

One-time CDK bootstrap (per AWS account/region):
    cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1

---

## Fork and Deploy — Complete Guide

### Step 0 — Clone the repository

    git clone https://github.com/prk-gen-ai-aws/genai-aws-p06-finance-tracker.git
    cd genai-aws-p06-finance-tracker

### Step 1 — Create Python virtual environment

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r ph1/app/requirements.txt
    pip install strands-agents strands-agents-tools bedrock-agentcore

Copy .env.example to .env — you will fill in values as you complete each step:

    cp .env.example .env

The .env file contains only configuration values (no credentials or secrets).
It is gitignored and never committed to the repository.

Expected .env content after all steps:
    AWS_REGION=us-east-1
    AGENTCORE_MEMORY_ID=p06FinanceTrackerMemory-xxxxxxxxxx
    AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT_ID:runtime/...

### Step 2 — Create AgentCore Memory (one-time setup)

    python3 << 'EOF'
    from bedrock_agentcore.memory import MemoryClient
    client = MemoryClient(region_name="us-east-1")
    memory = client.create_memory_and_wait(
        name="p06FinanceTrackerMemory",
        description="Personal finance tracker memory",
        strategies=[
            {
                "summaryMemoryStrategy": {     # SUMMARIZATION strategy
                    "name": "SpendingSummarizer",
                    "namespaceTemplates": ["/summaries/{actorId}/{sessionId}/"]
                }
            },
            {
                "userPreferenceMemoryStrategy": {
                    "name": "BudgetPreferences",
                    "namespaceTemplates": ["/preferences/{actorId}/"]
                }
            }
        ]
    )
    print(f"Memory ID: {memory['id']}")
    EOF

Open .env and replace the AGENTCORE_MEMORY_ID placeholder with the Memory ID from above:
    AGENTCORE_MEMORY_ID=p06FinanceTrackerMemory-xxxxxxxxxx

Note: .env is gitignored — no credentials or sensitive values are committed to the repository.

Verify memory was created successfully:

    python3 -c "
    from bedrock_agentcore.memory import MemoryClient
    status = MemoryClient(region_name='us-east-1').get_memory_status(memory_id='YOUR_MEMORY_ID')
    print(f'Memory status: {status}')
    "
    # Expected output: Memory status: ACTIVE

### Step 3 — Create IAM role for custom memory strategy

    aws iam create-policy --policy-name p06-memory-execution-policy --policy-document '{
      "Version": "2012-10-17",
      "Statement": [{"Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"], "Resource": ["arn:aws:bedrock:*::foundation-model/*", "arn:aws:bedrock:*:*:inference-profile/*"]}]
    }'

    aws iam create-role --role-name p06-memory-execution-role --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }'

    aws iam attach-role-policy --role-name p06-memory-execution-role --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/p06-memory-execution-policy

### Step 4 — Add custom semantic strategy

    python3 << 'EOF'
    import boto3
    client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
    client.update_memory(
        memoryId="YOUR_MEMORY_ID",
        memoryExecutionRoleArn="arn:aws:iam::YOUR_ACCOUNT_ID:role/p06-memory-execution-role",
        memoryStrategies={
            "addMemoryStrategies": [{
                "customMemoryStrategy": {
                    "name": "FinanceFactsCustom",
                    "description": "Finance-domain semantic extraction with query-aligned fact format",
                    "configuration": {
                        "semanticOverride": {
                            "extraction": {
                                "appendToPrompt": "For personal finance conversations, extract facts starting with: Budget status: [description] - $X spent of $X budget, $X remaining. Every fact MUST contain the word budget.",
                                "modelId": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
                            },
                            "consolidation": {
                                "appendToPrompt": "Keep facts concise using exact terms: budget, spent, remaining. Preserve dollar amounts exactly.",
                                "modelId": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
                            }
                        }
                    },
                    "namespaceTemplates": ["/finance/{actorId}/"]
                }
            }]
        }
    )
    print("Custom strategy added successfully")
    EOF

### Step 5 — Update agentcore.json

Edit agentcore/agentcore.json — update the runtimes section only. Keep all other existing keys (managedBy, tags, memories, etc.) unchanged:

    {
      "name": "p06FinanceTracker",
      "runtimes": [{
        "name": "p06FinanceTracker",
        "build": "CodeZip",
        "entrypoint": "main.py",
        "codeLocation": "ph1/agent/",
        "runtimeVersion": "PYTHON_3_12",
        "networkMode": "PUBLIC",
        "protocol": "HTTP",
        "environmentVariables": {
          "AGENTCORE_MEMORY_ID": "your-memory-id",
          "AWS_REGION": "us-east-1"
        }
      }]
    }

### Step 6 — Deploy AgentCore Runtime

    cd agentcore/cdk
    npm install        # if permission error: sudo npm install
    npx tsc            # compile TypeScript — required before deploy
    cd ../..
    agentcore deploy

### Step 7 — Add memory permissions to AgentCore role

Step 7a — Get the AgentCore IAM role name (copy the full role name from output):

    aws cloudformation describe-stack-resources \
      --stack-name AgentCore-p06FinanceTracker-default \
      --query "StackResources[?ResourceType=='AWS::IAM::Role'].PhysicalResourceId" \
      --output text

Step 7b — Add permissions (replace AGENTCORE_ROLE_NAME with output from Step 7a,
YOUR_ACCOUNT_ID with your 12-digit account ID, and YOUR_MEMORY_ID with your memory ID):

    aws iam put-role-policy \
      --role-name AGENTCORE_ROLE_NAME \
      --policy-name AllowAgentCoreMemory \
      --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["bedrock-agentcore:*"],"Resource":"arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT_ID:memory/YOUR_MEMORY_ID"}]}'

### Step 8 — Run the app

Get Runtime ARN and add to .env:

    agentcore status
    # Copy the Runtime ARN from output, then:
    echo "AGENTCORE_RUNTIME_ARN=your-runtime-arn" >> .env

Run the app:

    streamlit run ph1/app/main.py

---

## Cost Estimate

- Amazon Bedrock (Claude Haiku 4.5): approx USD 0.001-0.003 per conversation turn
- AgentCore Runtime: pay per invocation (negligible for dev usage)
- AgentCore Memory: pay per memory operation (negligible for dev usage)
- Total (development): less than USD 3.00 per month with daily testing

---

## Things to Consider at Scale

- Multi-user: use unique actor_id per user (currently "default-user" for ph1)
- Memory TTL: 90 day default — configure eventExpiryDuration per use case
- Extraction timing: async, ~1-30 min — design UX with this in mind
- Threshold tuning: different namespaces need different relevance thresholds
- Custom vs built-in strategies: use custom for domain-specific retrieval improvement
- Deletion discipline: never delete working memory strategies without a verified replacement

---

## AWS Documentation References

- Amazon Bedrock AgentCore Memory: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
- AgentCore Memory Blog: https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-memory-building-context-aware-agents/
- Strands Agents: https://strandsagents.com/latest/
- AgentCore Runtime invoke: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-invoke-agent.html

---

## Version History

See VERSIONS.md for details.

---

> Part of an ongoing series exploring Gen AI on AWS — applying real-world architecture patterns from serverless foundations to multi-agent agentic systems.
>
> Browse all projects: https://github.com/prk-gen-ai-aws
