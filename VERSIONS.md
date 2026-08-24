# Version History

## ph1 (Current)
- Personal Finance Tracker Agent using Amazon Bedrock AgentCore Runtime + Memory
- Strands Agents framework (v1.0) for autonomous reasoning
- No Lambda tools — AgentCore Memory + Bedrock reasoning only
- Three memory strategies: SpendingSummarizer, FinanceFactsCustom, BudgetPreferences
- Custom semantic strategy with finance-domain extraction prompt
- Cross-session recall via session summaries (scores 0.51-0.65)
- Incremental updates: "$20 more", "I saved $15", corrections
- Session continuity: LRU agent cache (128 sessions)
- CodeZip deployment via AgentCore CLI + CDK

## Key Design Decisions
- No Lambda tools: AgentCore Memory sufficient for finance tracking use case
- Custom strategy over built-in: domain-specific extraction prompt improves retrieval scores
- SpendingSummarizer as primary recall: session summaries mirror query vocabulary
- actor_id="default-user": single user for ph1, multi-user ready for ph2
- Namespace prefix search: /summaries/{actorId}/ not /summaries/{actorId}/{sessionId}/
- session_manager= not conversation_manager=: correct parameter for AgentCoreMemorySessionManager
- close() in finally block: flushes events to trigger long-term extraction

## Key Learnings
- session_manager= (not conversation_manager=) for AgentCoreMemorySessionManager
- strands-agents 1.52.0 + bedrock-agentcore 1.21.0: compatible versions
- Namespace prefix scope: /summaries/{actorId}/ retrieves across ALL sessions
- SpendingSummarizer scores highest (0.51-0.65) for budget queries
- Custom strategy requires memoryExecutionRoleArn IAM role
- Built-in SEMANTIC strategy cannot be modified after creation
- boto3 update_memory() directly (not SDK modify_strategy()) for reliable custom strategy modification
- Long-term extraction is async: ~1-30 min, AWS does not document exact SLA
- Relevance threshold tuning: 0.5 for summaries, 0.45 for facts/preferences
- Deletion discipline: never delete working strategies without verified replacement

## ph2 Roadmap (internal)
- Multi-user support (unique actor_id per user)
- Month-over-month spending comparison
- Budget alerts via email/SNS
- Category budget limits with warnings
- Export spending report as PDF
