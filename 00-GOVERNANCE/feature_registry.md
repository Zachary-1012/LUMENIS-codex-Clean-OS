# 序境 / ZBC Feature Registry

> Generated: 2026-09-06 | Shard D / Team 1 | Source: real code scan
> Total Features: 334 | Total Functions: 2653

## Status Distribution

| Status | Count |
|---|---|
| PLANNED | 0 |
| IMPLEMENTED | 88 |
| INTEGRATED | 206 |
| TESTED | 40 |
| VERIFIED | 0 |
| RELEASED | 0 |
| OPERATING | 0 |

## Domain Distribution

| Domain | Count |
|---|---|
| 01 Product/Domain/Subject | 74 |
| 02 Repository/Runtime/Environment | 3 |
| 03 Data Collection | 9 |
| 04 Source Library | 6 |
| 06 Subject Filter/Dedup | 5 |
| 07 Data Quality | 1 |
| 10 Event | 4 |
| 12 Case/Public Opinion | 7 |
| 13 Risk Engine | 1 |
| 14 Alert | 1 |
| 15 Metric/Statistics | 3 |
| 17 Search/Filter | 7 |
| 18 KOS | 11 |
| 19 KOL | 1 |
| 21 Campaign/Topic | 5 |
| 22 Report | 6 |
| 23 Import/Export | 3 |
| 25 AI Provider/Gateway | 134 |
| 26 AI Analyzer/Filter | 2 |
| 27 AI Learning/Feedback | 4 |
| 31 Orchestrator | 1 |
| 34 Permission | 3 |
| 39 Evidence | 5 |
| 40 Evaluation | 1 |
| 42 Checkpoint/Resume/Recovery | 1 |
| 43 Memory/Learning Asset | 1 |
| 44 Browser/CDP/Login | 13 |
| 45 Frontend/UI/UX | 1 |
| 46 API | 4 |
| 47 DB/Migration | 5 |
| 48 Security/Audit | 5 |
| 49 CI/CD/Release | 1 |
| 50 Production Runtime | 6 |

## Feature Registry (Full)

| ID | Domain | Feature | File | Funcs | Status | Test | Evidence |
|---|---|---|---|---|---|---|---|
| F-0001 | 17 Search/Filter | Search/Filter - ddc_research_adapter.py | components\AI-Development-Research-Hub\src\adapter | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0002 | 17 Search/Filter | Search/Filter - research_record.py | components\AI-Development-Research-Hub\src\contrac | 10 | IMPLEMENTED | No | Source scan: 11 functions, 11 real, 0 stubs |
| F-0003 | 17 Search/Filter | Search/Filter - CollectionHygienePolicy | components\AI-Development-Research-Hub\src\contrac | 3 | TESTED | Yes | Source scan: 3 functions, 3 real, 0 stubs |
| F-0004 | 17 Search/Filter | Search/Filter - RateGovernor | components\AI-Development-Research-Hub\src\contrac | 4 | TESTED | Yes | Source scan: 4 functions, 4 real, 0 stubs |
| F-0005 | 17 Search/Filter | Search/Filter - Module Functions | components\AI-Development-Research-Hub\src\contrac | 4 | IMPLEMENTED | Yes | Source scan: 4 functions, 4 real, 0 stubs |
| F-0006 | 17 Search/Filter | Search/Filter - capability_registry.py | components\AI-Development-Research-Hub\src\shared\ | 10 | INTEGRATED | No | Source scan: 12 functions, 12 real, 0 stubs |
| F-0007 | 17 Search/Filter | Search/Filter - shadow_lifecycle.py | components\AI-Development-Research-Hub\src\shared\ | 4 | IMPLEMENTED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0008 | 01 Product/Domain/Subject | Product/Subject - test_pyresilience.py | components\SICI-Core\shadow_run\test_pyresilience. | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0009 | 01 Product/Domain/Subject | Product/Subject - test_yyds_logger.py | components\SICI-Core\shadow_run\test_yyds_logger.p | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0010 | 04 Source Library | Source/Adapter - AdapterMetrics | components\SICI-Core\upgrade_modules\base_adapter_ | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0011 | 04 Source Library | Source/Adapter - AdapterRegistry | components\SICI-Core\upgrade_modules\base_adapter_ | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0012 | 04 Source Library | Source/Adapter - BaseAdapter | components\SICI-Core\upgrade_modules\base_adapter_ | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0013 | 04 Source Library | Source/Adapter - SimpleCache | components\SICI-Core\upgrade_modules\base_adapter_ | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0014 | 01 Product/Domain/Subject | Product/Subject - CookieItem | components\SICI-Core\upgrade_modules\dual_pool.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0015 | 01 Product/Domain/Subject | Product/Subject - CookiePool | components\SICI-Core\upgrade_modules\dual_pool.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0016 | 01 Product/Domain/Subject | Product/Subject - DualPoolManager | components\SICI-Core\upgrade_modules\dual_pool.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0017 | 01 Product/Domain/Subject | Product/Subject - ProxyItem | components\SICI-Core\upgrade_modules\dual_pool.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0018 | 01 Product/Domain/Subject | Product/Subject - ProxyPool | components\SICI-Core\upgrade_modules\dual_pool.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0019 | 01 Product/Domain/Subject | Product/Subject - Module Functions | components\SICI-Core\upgrade_modules\dual_pool.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0020 | 01 Product/Domain/Subject | Product/Subject - unified_logger.py | components\SICI-Core\upgrade_modules\unified_logge | 10 | INTEGRATED | No | Source scan: 15 functions, 15 real, 0 stubs |
| F-0021 | 02 Repository/Runtime/Environment | Config/Environment - skills_registry_cli.py | config\skills_registry_cli.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0022 | 25 AI Provider/Gateway | AI Engine - action_firewall.py | osai_engine\action_firewall.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0023 | 25 AI Provider/Gateway | AI Engine - agent.py | osai_engine\agent.py | 3 | TESTED | Yes | Source scan: 3 functions, 3 real, 0 stubs |
| F-0024 | 25 AI Provider/Gateway | AI Engine - AuditRecord | osai_engine\agent_identity.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0025 | 25 AI Provider/Gateway | AI Engine - Identity | osai_engine\agent_identity.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0026 | 25 AI Provider/Gateway | AI Engine - IdentityChain | osai_engine\agent_identity.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0027 | 25 AI Provider/Gateway | AI Engine - IdentityNode | osai_engine\agent_identity.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0028 | 25 AI Provider/Gateway | AI Engine - IdentityRegistry | osai_engine\agent_identity.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0029 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\agent_identity.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0030 | 25 AI Provider/Gateway | AI Engine - AgentIdentityContext | osai_engine\agent_integration.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0031 | 25 AI Provider/Gateway | AI Engine - IdentityAwareAgentWrapper | osai_engine\agent_integration.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0032 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\agent_integration.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0033 | 25 AI Provider/Gateway | AI Gateway - ai_gateway.py | osai_engine\ai_gateway.py | 5 | TESTED | Yes | Source scan: 5 functions, 5 real, 0 stubs |
| F-0034 | 25 AI Provider/Gateway | AI Engine - BrowserCapability | osai_engine\browser_capability.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0035 | 25 AI Provider/Gateway | AI Engine - BrowserCapabilityRegistry | osai_engine\browser_capability.py | 10 | INTEGRATED | No | Source scan: 11 functions, 11 real, 0 stubs |
| F-0036 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\browser_capability.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0037 | 25 AI Provider/Gateway | AI Engine - browser_executor.py | osai_engine\browser_executor.py | 10 | IMPLEMENTED | No | Source scan: 12 functions, 12 real, 0 stubs |
| F-0038 | 25 AI Provider/Gateway | AI Engine - Action | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0039 | 25 AI Provider/Gateway | AI Engine - CanonicalBase | osai_engine\canonical_data.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0040 | 25 AI Provider/Gateway | AI Engine - Case | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0041 | 25 AI Provider/Gateway | AI Engine - Decision | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0042 | 25 AI Provider/Gateway | AI Engine - Evaluation | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0043 | 25 AI Provider/Gateway | AI Engine - Event | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0044 | 25 AI Provider/Gateway | AI Engine - Evidence | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0045 | 25 AI Provider/Gateway | AI Engine - Finding | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0046 | 25 AI Provider/Gateway | AI Engine - LearningAsset | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0047 | 25 AI Provider/Gateway | AI Engine - Outcome | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0048 | 25 AI Provider/Gateway | AI Engine - Source | osai_engine\canonical_data.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0049 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\canonical_data.py | 4 | IMPLEMENTED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0050 | 25 AI Provider/Gateway | AI Engine - canonical_skill_registry.py | osai_engine\canonical_skill_registry.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0051 | 25 AI Provider/Gateway | AI Engine - Capability | osai_engine\capability_registry.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0052 | 25 AI Provider/Gateway | AI Engine - CapabilityRegistry | osai_engine\capability_registry.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0053 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\capability_registry.py | 3 | IMPLEMENTED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0054 | 25 AI Provider/Gateway | AI Engine - Checkpoint | osai_engine\checkpoint_resume.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0055 | 25 AI Provider/Gateway | AI Engine - CheckpointManager | osai_engine\checkpoint_resume.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0056 | 25 AI Provider/Gateway | AI Engine - context_runtime.py | osai_engine\context_runtime.py | 9 | INTEGRATED | No | Source scan: 9 functions, 9 real, 0 stubs |
| F-0057 | 25 AI Provider/Gateway | AI Engine - contract_persistence.py | osai_engine\contract_persistence.py | 10 | IMPLEMENTED | No | Source scan: 13 functions, 13 real, 0 stubs |
| F-0058 | 25 AI Provider/Gateway | AI Engine - DAOResult | osai_engine\decision_action_outcome.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0059 | 25 AI Provider/Gateway | AI Engine - DecisionActionOutcomeEngine | osai_engine\decision_action_outcome.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0060 | 25 AI Provider/Gateway | AI Engine - DelegationContext | osai_engine\delegation.py | 9 | TESTED | Yes | Source scan: 9 functions, 9 real, 0 stubs |
| F-0061 | 25 AI Provider/Gateway | AI Engine - DelegationManager | osai_engine\delegation.py | 5 | TESTED | Yes | Source scan: 5 functions, 5 real, 0 stubs |
| F-0062 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\delegation.py | 1 | IMPLEMENTED | Yes | Source scan: 1 functions, 1 real, 0 stubs |
| F-0063 | 25 AI Provider/Gateway | AI Engine - EffectFence | osai_engine\effect_fence.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0064 | 25 AI Provider/Gateway | AI Engine - EffectRecord | osai_engine\effect_fence.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0065 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\effect_fence.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0066 | 25 AI Provider/Gateway | AI Engine - BaseEngine | osai_engine\engine_layer.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0067 | 25 AI Provider/Gateway | AI Engine - CodingEngine | osai_engine\engine_layer.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0068 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\engine_layer.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0069 | 25 AI Provider/Gateway | AI Engine - engine_runtime.py | osai_engine\engine_runtime.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0070 | 25 AI Provider/Gateway | AI Engine - engineering_loop.py | osai_engine\engineering_loop.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0071 | 25 AI Provider/Gateway | AI Engine - Evaluation | osai_engine\evaluation_contract.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0072 | 25 AI Provider/Gateway | AI Engine - EvaluationRegistry | osai_engine\evaluation_contract.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0073 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\evaluation_contract.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0074 | 25 AI Provider/Gateway | AI Engine - evidence.py | osai_engine\evidence.py | 1 | TESTED | Yes | Source scan: 1 functions, 1 real, 0 stubs |
| F-0075 | 25 AI Provider/Gateway | AI Engine - BusinessEvidenceChain | osai_engine\evidence_chain.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0076 | 25 AI Provider/Gateway | AI Engine - EvidenceChain | osai_engine\evidence_chain.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0077 | 25 AI Provider/Gateway | AI Engine - EvidenceChainRegistry | osai_engine\evidence_chain.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0078 | 25 AI Provider/Gateway | AI Engine - EvidenceNode | osai_engine\evidence_chain.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0079 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\evidence_chain.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0080 | 25 AI Provider/Gateway | AI Engine - EvidenceEdge | osai_engine\evidence_graph.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0081 | 25 AI Provider/Gateway | AI Engine - EvidenceGraph | osai_engine\evidence_graph.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0082 | 25 AI Provider/Gateway | AI Engine - EvidenceNode | osai_engine\evidence_graph.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0083 | 25 AI Provider/Gateway | AI Engine - harness_runtime.py | osai_engine\harness_runtime.py | 10 | INTEGRATED | No | Source scan: 15 functions, 15 real, 0 stubs |
| F-0084 | 25 AI Provider/Gateway | AI Engine - impact_analysis.py | osai_engine\impact_analysis.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0085 | 25 AI Provider/Gateway | AI Engine - LearningRecord | osai_engine\learning_record_contract.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0086 | 25 AI Provider/Gateway | AI Engine - LearningRegistry | osai_engine\learning_record_contract.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0087 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\learning_record_contract.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0088 | 25 AI Provider/Gateway | AI Engine - lifecycle_contract.py | osai_engine\lifecycle_contract.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0089 | 25 AI Provider/Gateway | AI Engine - llm.py | osai_engine\llm.py | 2 | IMPLEMENTED | Yes | Source scan: 2 functions, 2 real, 0 stubs |
| F-0090 | 25 AI Provider/Gateway | AI Engine - MemoryEntry | osai_engine\memory_lifecycle.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0091 | 25 AI Provider/Gateway | AI Engine - MemoryLifecycle | osai_engine\memory_lifecycle.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0092 | 25 AI Provider/Gateway | AI Engine - DelegationContext | osai_engine\obo_jit.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0093 | 25 AI Provider/Gateway | AI Engine - DelegationManager | osai_engine\obo_jit.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0094 | 25 AI Provider/Gateway | AI Engine - ExecutionAttribution | osai_engine\obo_jit.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0095 | 25 AI Provider/Gateway | AI Engine - Metric | osai_engine\observability.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0096 | 25 AI Provider/Gateway | AI Engine - Observability | osai_engine\observability.py | 10 | INTEGRATED | No | Source scan: 12 functions, 12 real, 0 stubs |
| F-0097 | 25 AI Provider/Gateway | AI Engine - TraceSpan | osai_engine\observability.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0098 | 25 AI Provider/Gateway | AI Engine - _TraceContext | osai_engine\observability.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0099 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\observability.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0100 | 25 AI Provider/Gateway | AI Engine - orchestrator.py | osai_engine\orchestrator.py | 3 | IMPLEMENTED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0101 | 25 AI Provider/Gateway | AI Engine - PermissionContractRegistry | osai_engine\permission_contract.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0102 | 25 AI Provider/Gateway | AI Engine - PermissionRequest | osai_engine\permission_contract.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0103 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\permission_contract.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0104 | 25 AI Provider/Gateway | AI Engine - permission_gate.py | osai_engine\permission_gate.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0105 | 25 AI Provider/Gateway | AI Engine - ReleaseCandidate | osai_engine\release_safety.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0106 | 25 AI Provider/Gateway | AI Engine - ReleaseSafetyManager | osai_engine\release_safety.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0107 | 25 AI Provider/Gateway | AI Engine - RepoRecord | osai_engine\repository_contract.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0108 | 25 AI Provider/Gateway | AI Engine - RepositoryContractRegistry | osai_engine\repository_contract.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0109 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\repository_contract.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0110 | 25 AI Provider/Gateway | AI Engine - repository_registry.py | osai_engine\repository_registry.py | 10 | IMPLEMENTED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0111 | 25 AI Provider/Gateway | AI Engine - research.py | osai_engine\research.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0112 | 25 AI Provider/Gateway | AI Engine - ResearchPipeline | osai_engine\research_pipeline.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0113 | 25 AI Provider/Gateway | AI Engine - ResearchRecord | osai_engine\research_pipeline.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0114 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\research_pipeline.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0115 | 25 AI Provider/Gateway | AI Engine - rules.py | osai_engine\rules.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0116 | 25 AI Provider/Gateway | AI Engine - RuntimeRegistry | osai_engine\runtime_contract.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0117 | 25 AI Provider/Gateway | AI Engine - RuntimeState | osai_engine\runtime_contract.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0118 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\runtime_contract.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0119 | 25 AI Provider/Gateway | AI Engine - Lease | osai_engine\runtime_guardian.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0120 | 25 AI Provider/Gateway | AI Engine - RuntimeGuardian | osai_engine\runtime_guardian.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0121 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\runtime_guardian.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0122 | 25 AI Provider/Gateway | AI Engine - InvocationRecord | osai_engine\skill_execution_contract.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0123 | 25 AI Provider/Gateway | AI Engine - SkillExecutionContract | osai_engine\skill_execution_contract.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0124 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\skill_execution_contract.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0125 | 25 AI Provider/Gateway | AI Engine - SkillInvocation | osai_engine\skill_invocation.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0126 | 25 AI Provider/Gateway | AI Engine - SkillInvoker | osai_engine\skill_invocation.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0127 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\skill_invocation.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0128 | 25 AI Provider/Gateway | AI Engine - skill_manifest.py | osai_engine\skill_manifest.py | 6 | IMPLEMENTED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0129 | 25 AI Provider/Gateway | AI Engine - skill_registry.py | osai_engine\skill_registry.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0130 | 25 AI Provider/Gateway | AI Engine - skill_selector.py | osai_engine\skill_selector.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0131 | 25 AI Provider/Gateway | AI Engine - skill_sync.py | osai_engine\skill_sync.py | 10 | IMPLEMENTED | No | Source scan: 13 functions, 13 real, 0 stubs |
| F-0132 | 25 AI Provider/Gateway | AI Engine - source_skills.py | osai_engine\skills\source_skills.py | 10 | INTEGRATED | No | Source scan: 18 functions, 18 real, 0 stubs |
| F-0133 | 25 AI Provider/Gateway | AI Engine - Task | osai_engine\task_contract.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0134 | 25 AI Provider/Gateway | AI Engine - TaskRegistry | osai_engine\task_contract.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0135 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\task_contract.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0136 | 25 AI Provider/Gateway | AI Engine - tools.py | osai_engine\tools.py | 10 | INTEGRATED | No | Source scan: 11 functions, 11 real, 0 stubs |
| F-0137 | 25 AI Provider/Gateway | AI Engine - Span | osai_engine\trace_contract.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0138 | 25 AI Provider/Gateway | AI Engine - Trace | osai_engine\trace_contract.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0139 | 25 AI Provider/Gateway | AI Engine - TraceRegistry | osai_engine\trace_contract.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0140 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\trace_contract.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0141 | 25 AI Provider/Gateway | AI Engine - TraceEvaluation | osai_engine\trace_evaluation.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0142 | 25 AI Provider/Gateway | AI Engine - TraceEvaluator | osai_engine\trace_evaluation.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0143 | 25 AI Provider/Gateway | AI Engine - TraceMetrics | osai_engine\trace_evaluation.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0144 | 25 AI Provider/Gateway | AI Engine - UIState | osai_engine\ui_state_contract.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0145 | 25 AI Provider/Gateway | AI Engine - UIStateRegistry | osai_engine\ui_state_contract.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0146 | 25 AI Provider/Gateway | AI Engine - Module Functions | osai_engine\ui_state_contract.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0147 | 01 Product/Domain/Subject | Product/Subject - _douyin_detail_debug.py | _douyin_detail_debug.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0148 | 01 Product/Domain/Subject | Product/Subject - _douyin_render_walk.py | _douyin_render_walk.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0149 | 01 Product/Domain/Subject | Product/Subject - _douyin_ssr_debug.py | _douyin_ssr_debug.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0150 | 01 Product/Domain/Subject | Product/Subject - _douyin_struct.py | _douyin_struct.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0151 | 44 Browser/CDP/Login | Browser/CDP - _parse_x_cookie_v2.py | _parse_x_cookie_v2.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0152 | 22 Report | Report Generation - _split_report_api.py | _split_report_api.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0153 | 01 Product/Domain/Subject | Product/Subject - adaptive_engine.py | adaptive_engine.py | 10 | TESTED | Yes | Source scan: 13 functions, 13 real, 0 stubs |
| F-0154 | 48 Security/Audit | Security - agent_security.py | agent_security.py | 5 | IMPLEMENTED | Yes | Source scan: 5 functions, 5 real, 0 stubs |
| F-0155 | 26 AI Analyzer/Filter | AI Analyzer - ai_analyzer.py | ai_analyzer.py | 10 | INTEGRATED | No | Source scan: 14 functions, 14 real, 0 stubs |
| F-0156 | 01 Product/Domain/Subject | Product/Subject - ai_api.py | ai_api.py | 10 | IMPLEMENTED | No | Source scan: 21 functions, 21 real, 0 stubs |
| F-0157 | 25 AI Provider/Gateway | AI Gateway - CircuitBreaker | ai_channel.py | 6 | TESTED | Yes | Source scan: 6 functions, 6 real, 0 stubs |
| F-0158 | 25 AI Provider/Gateway | AI Gateway - ProviderBreaker | ai_channel.py | 7 | TESTED | Yes | Source scan: 7 functions, 7 real, 0 stubs |
| F-0159 | 25 AI Provider/Gateway | AI Gateway - Module Functions | ai_channel.py | 10 | TESTED | Yes | Source scan: 12 functions, 12 real, 0 stubs |
| F-0160 | 26 AI Analyzer/Filter | AI Analyzer - ai_filter.py | ai_filter.py | 7 | IMPLEMENTED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0161 | 01 Product/Domain/Subject | Product/Subject - AIDesensitizer | ai_governance.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0162 | 01 Product/Domain/Subject | Product/Subject - AIUsageTracker | ai_governance.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0163 | 01 Product/Domain/Subject | Product/Subject - Module Functions | ai_governance.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0164 | 27 AI Learning/Feedback | AI Learning - AILearningEngine | ai_learning_engine.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0165 | 27 AI Learning/Feedback | AI Learning - WebSentimentSearch | ai_learning_engine.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0166 | 27 AI Learning/Feedback | AI Learning - Module Functions | ai_learning_engine.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0167 | 04 Source Library | Source/Adapter - ai_resource_packs.py | ai_resource_packs.py | 10 | IMPLEMENTED | No | Source scan: 13 functions, 13 real, 0 stubs |
| F-0168 | 14 Alert | Alert/Notification - alert_engine.py | alert_engine.py | 9 | INTEGRATED | No | Source scan: 9 functions, 9 real, 0 stubs |
| F-0169 | 12 Case/Public Opinion | Main Application - app.py | app.py | 10 | TESTED | Yes | Source scan: 253 functions, 253 real, 0 stubs |
| F-0170 | 39 Evidence | Evidence Management - app_evidence.py | app_evidence.py | 10 | INTEGRATED | No | Source scan: 19 functions, 19 real, 0 stubs |
| F-0171 | 46 API | API/Routes - app_refactor_blueprint.py | app_refactor_blueprint.py | 10 | INTEGRATED | No | Source scan: 17 functions, 17 real, 0 stubs |
| F-0172 | 01 Product/Domain/Subject | Product/Subject - architecture_api.py | architecture_api.py | 10 | IMPLEMENTED | No | Source scan: 22 functions, 22 real, 0 stubs |
| F-0173 | 01 Product/Domain/Subject | Product/Subject - ark_llm.py | ark_llm.py | 10 | IMPLEMENTED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0174 | 34 Permission | Permission/Auth - auth_recovery_api.py | auth_recovery_api.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0175 | 34 Permission | Permission/Auth - AuthRecoveryCenter | auth_recovery_center.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0176 | 34 Permission | Permission/Auth - RecoveryTask | auth_recovery_center.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0177 | 42 Checkpoint/Resume/Recovery | Recovery - auto_recovery.py | auto_recovery.py | 10 | TESTED | Yes | Source scan: 19 functions, 19 real, 0 stubs |
| F-0178 | 44 Browser/CDP/Login | Browser/CDP - bilibili_login_manager.py | bilibili_login_manager.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0179 | 01 Product/Domain/Subject | Product/Subject - brand_knowledge_base.py | brand_knowledge_base.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0180 | 22 Report | Report Generation - brand_report_generator.py | brand_report_generator.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0181 | 15 Metric/Statistics | Metrics/Stats - brand_stats_recompute.py | brand_stats_recompute.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0182 | 44 Browser/CDP/Login | Browser/CDP - browser_discovery.py | browser_discovery.py | 9 | INTEGRATED | No | Source scan: 9 functions, 9 real, 0 stubs |
| F-0183 | 44 Browser/CDP/Login | Browser/CDP - browser_runtime_api.py | browser_runtime_api.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0184 | 44 Browser/CDP/Login | Browser/CDP - browser_surface.py | browser_surface.py | 10 | IMPLEMENTED | Yes | Source scan: 48 functions, 48 real, 0 stubs |
| F-0185 | 44 Browser/CDP/Login | Browser/CDP - browser_surface_api.py | browser_surface_api.py | 10 | INTEGRATED | No | Source scan: 31 functions, 31 real, 0 stubs |
| F-0186 | 01 Product/Domain/Subject | Product/Subject - cache_manager.py | cache_manager.py | 10 | INTEGRATED | No | Source scan: 11 functions, 11 real, 0 stubs |
| F-0187 | 15 Metric/Statistics | Metrics/Stats - canonical_metrics.py | canonical_metrics.py | 10 | TESTED | Yes | Source scan: 12 functions, 12 real, 0 stubs |
| F-0188 | 12 Case/Public Opinion | Case Management - case_ai_evaluate.py | case_ai_evaluate.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0189 | 12 Case/Public Opinion | Case Management - case_deep_analysis.py | case_deep_analysis.py | 10 | INTEGRATED | No | Source scan: 12 functions, 12 real, 0 stubs |
| F-0190 | 12 Case/Public Opinion | Case Management - case_templates.py | case_templates.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0191 | 44 Browser/CDP/Login | Browser/CDP - cdp_helper.py | cdp_helper.py | 10 | IMPLEMENTED | No | Source scan: 15 functions, 15 real, 0 stubs |
| F-0192 | 49 CI/CD/Release | CI/CD/Release - ci_cd.py | ci_cd.py | 9 | IMPLEMENTED | No | Source scan: 9 functions, 9 real, 0 stubs |
| F-0193 | 01 Product/Domain/Subject | Product/Subject - collection_api.py | collection_api.py | 10 | INTEGRATED | No | Source scan: 13 functions, 13 real, 0 stubs |
| F-0194 | 25 AI Provider/Gateway | AI Engine - collection_intelligence.py | collection_intelligence.py | 5 | IMPLEMENTED | Yes | Source scan: 5 functions, 5 real, 0 stubs |
| F-0195 | 03 Data Collection | Collector - collector.py | collector.py | 10 | IMPLEMENTED | Yes | Source scan: 18 functions, 18 real, 0 stubs |
| F-0196 | 03 Data Collection | Collector - collector_auto_start.py | collector_auto_start.py | 9 | INTEGRATED | No | Source scan: 9 functions, 9 real, 0 stubs |
| F-0197 | 03 Data Collection | Collector - collector_automation.py | collector_automation.py | 10 | INTEGRATED | No | Source scan: 19 functions, 19 real, 0 stubs |
| F-0198 | 03 Data Collection | Collector - collector_guard_integration.py | collector_guard_integration.py | 5 | TESTED | Yes | Source scan: 5 functions, 5 real, 0 stubs |
| F-0199 | 03 Data Collection | Collector - collector_v2_integration.py | collector_v2_integration.py | 8 | IMPLEMENTED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0200 | 48 Security/Audit | Security - compliance_gate.py | compliance_gate.py | 7 | TESTED | Yes | Source scan: 7 functions, 7 real, 0 stubs |
| F-0201 | 02 Repository/Runtime/Environment | Config/Environment - config.py | config.py | 10 | INTEGRATED | No | Source scan: 16 functions, 16 real, 0 stubs |
| F-0202 | 25 AI Provider/Gateway | AI Engine - context_intelligence.py | context_intelligence.py | 5 | TESTED | Yes | Source scan: 5 functions, 5 real, 0 stubs |
| F-0203 | 01 Product/Domain/Subject | Product/Subject - lumenis_adapter.py | contracts\lumenis_adapter.py | 8 | IMPLEMENTED | Yes | Source scan: 8 functions, 8 real, 0 stubs |
| F-0204 | 22 Report | Report Generation - daily_report.py | daily_report.py | 10 | TESTED | Yes | Source scan: 14 functions, 14 real, 0 stubs |
| F-0205 | 01 Product/Domain/Subject | Product/Subject - data_boundary.py | data_boundary.py | 7 | IMPLEMENTED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0206 | 27 AI Learning/Feedback | AI Learning - data_feedback_loop.py | data_feedback_loop.py | 10 | INTEGRATED | No | Source scan: 12 functions, 12 real, 0 stubs |
| F-0207 | 07 Data Quality | Data Quality - data_quality_gate.py | data_quality_gate.py | 10 | IMPLEMENTED | Yes | Source scan: 15 functions, 15 real, 0 stubs |
| F-0208 | 01 Product/Domain/Subject | Product/Subject - data_query_api.py | data_query_api.py | 10 | INTEGRATED | No | Source scan: 12 functions, 12 real, 0 stubs |
| F-0209 | 01 Product/Domain/Subject | Product/Subject - database.py | database.py | 10 | TESTED | Yes | Source scan: 59 functions, 59 real, 0 stubs |
| F-0210 | 47 DB/Migration | DB/Migration - database_migrations.py | database_migrations.py | 10 | INTEGRATED | No | Source scan: 18 functions, 18 real, 0 stubs |
| F-0211 | 01 Product/Domain/Subject | Product/Subject - dev_exec_core.py | dev_exec_core.py | 4 | IMPLEMENTED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0212 | 01 Product/Domain/Subject | Product/Subject - domain_isolation.py | domain_isolation.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0213 | 01 Product/Domain/Subject | Product/Subject - emv.py | emv.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0214 | 15 Metric/Statistics | Metrics/Stats - engineering_metrics.py | engineering_metrics.py | 9 | IMPLEMENTED | Yes | Source scan: 9 functions, 9 real, 0 stubs |
| F-0215 | 01 Product/Domain/Subject | Product/Subject - evaluate_system_timing.py | evaluate_system_timing.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0216 | 40 Evaluation | Evaluation - evaluation_system.py | evaluation_system.py | 10 | INTEGRATED | No | Source scan: 15 functions, 15 real, 0 stubs |
| F-0217 | 10 Event | Event Management - BrandEvent | event_graph.py | 2 | TESTED | Yes | Source scan: 2 functions, 2 real, 0 stubs |
| F-0218 | 10 Event | Event Management - EventGraph | event_graph.py | 10 | TESTED | Yes | Source scan: 12 functions, 12 real, 0 stubs |
| F-0219 | 10 Event | Event Management - EventRelation | event_graph.py | 2 | TESTED | Yes | Source scan: 2 functions, 2 real, 0 stubs |
| F-0220 | 10 Event | Event Management - Module Functions | event_graph.py | 7 | TESTED | Yes | Source scan: 7 functions, 7 real, 0 stubs |
| F-0221 | 39 Evidence | Evidence Management - evidence_api.py | evidence_api.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0222 | 39 Evidence | Evidence Management - evidence_store.py | evidence_store.py | 4 | TESTED | Yes | Source scan: 4 functions, 4 real, 0 stubs |
| F-0223 | 23 Import/Export | Import/Export - export_report.py | export_report.py | 10 | INTEGRATED | No | Source scan: 19 functions, 19 real, 0 stubs |
| F-0224 | 01 Product/Domain/Subject | Product/Subject - function_registry.py | function_registry.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0225 | 46 API | API/Routes - ic_routes.py | ic_routes.py | 10 | IMPLEMENTED | No | Source scan: 13 functions, 13 real, 0 stubs |
| F-0226 | 23 Import/Export | Import/Export - import_cookies.py | import_cookies.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0227 | 23 Import/Export | Import/Export - import_xhs_cookies.py | import_xhs_cookies.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0228 | 25 AI Provider/Gateway | AI Engine - intelligence.py | intelligence.py | 10 | TESTED | Yes | Source scan: 31 functions, 31 real, 0 stubs |
| F-0229 | 44 Browser/CDP/Login | Browser/CDP - internal_browser.py | internal_browser.py | 10 | TESTED | Yes | Source scan: 32 functions, 32 real, 0 stubs |
| F-0230 | 44 Browser/CDP/Login | Browser/CDP - ScreencastManager | internal_browser_stream.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0231 | 44 Browser/CDP/Login | Browser/CDP - ScreencastSession | internal_browser_stream.py | 10 | INTEGRATED | No | Source scan: 12 functions, 12 real, 0 stubs |
| F-0232 | 44 Browser/CDP/Login | Browser/CDP - Module Functions | internal_browser_stream.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0233 | 01 Product/Domain/Subject | Product/Subject - juguang_api.py | juguang_api.py | 5 | IMPLEMENTED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0234 | 19 KOL | KOL Management - kol_analysis.py | kol_analysis.py | 5 | TESTED | Yes | Source scan: 5 functions, 5 real, 0 stubs |
| F-0235 | 18 KOS | KOS Management - kos_attribution.py | kos_attribution.py | 3 | TESTED | Yes | Source scan: 3 functions, 3 real, 0 stubs |
| F-0236 | 18 KOS | KOS Management - kos_engine.py | kos_engine.py | 10 | INTEGRATED | No | Source scan: 27 functions, 27 real, 0 stubs |
| F-0237 | 18 KOS | KOS Management - kos_execution.py | kos_execution.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0238 | 18 KOS | KOS Management - kos_intel.py | kos_intel.py | 10 | IMPLEMENTED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0239 | 18 KOS | KOS Management - kos_metrics.py | kos_metrics.py | 8 | IMPLEMENTED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0240 | 18 KOS | KOS Management - kos_ops.py | kos_ops.py | 10 | TESTED | Yes | Source scan: 10 functions, 10 real, 0 stubs |
| F-0241 | 18 KOS | KOS Management - kos_paid.py | kos_paid.py | 5 | TESTED | Yes | Source scan: 5 functions, 5 real, 0 stubs |
| F-0242 | 18 KOS | KOS Management - kos_professional.py | kos_professional.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0243 | 18 KOS | KOS Management - kos_report.py | kos_report.py | 4 | IMPLEMENTED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0244 | 18 KOS | KOS Management - kos_routes.py | kos_routes.py | 10 | INTEGRATED | No | Source scan: 62 functions, 62 real, 0 stubs |
| F-0245 | 18 KOS | KOS Management - kos_scenarios.py | kos_scenarios.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0246 | 03 Data Collection | Collector - CodebaseScanner | learning_collector.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0247 | 03 Data Collection | Collector - LearningAnalyzer | learning_collector.py | 9 | INTEGRATED | No | Source scan: 9 functions, 9 real, 0 stubs |
| F-0248 | 03 Data Collection | Collector - Module Functions | learning_collector.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0249 | 01 Product/Domain/Subject | Product/Subject - learning_persistence.py | learning_persistence.py | 10 | TESTED | Yes | Source scan: 26 functions, 26 real, 0 stubs |
| F-0250 | 01 Product/Domain/Subject | Product/Subject - local_ai_client.py | local_ai_client.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0251 | 01 Product/Domain/Subject | Product/Subject - logger.py | logger.py | 10 | IMPLEMENTED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0252 | 01 Product/Domain/Subject | Product/Subject - lumenis_agg_api.py | lumenis_agg_api.py | 10 | IMPLEMENTED | No | Source scan: 23 functions, 23 real, 0 stubs |
| F-0253 | 45 Frontend/UI/UX | Frontend/UI - lumenis_frontend.py | lumenis_frontend.py | 10 | TESTED | Yes | Source scan: 25 functions, 25 real, 0 stubs |
| F-0254 | 01 Product/Domain/Subject | Product/Subject - lumenis_skill_adapter.py | lumenis_skill_adapter.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0255 | 43 Memory/Learning Asset | Memory - memory_optimizer.py | memory_optimizer.py | 10 | IMPLEMENTED | No | Source scan: 14 functions, 14 real, 0 stubs |
| F-0256 | 47 DB/Migration | DB/Migration - BaseModel | models.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0257 | 47 DB/Migration | DB/Migration - Note | models.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0258 | 47 DB/Migration | DB/Migration - Module Functions | models.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0259 | 01 Product/Domain/Subject | Product/Subject - monitor_pipeline.py | monitor_pipeline.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0260 | 01 Product/Domain/Subject | Product/Subject - Alert | monitoring.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0261 | 01 Product/Domain/Subject | Product/Subject - HealthStatus | monitoring.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0262 | 01 Product/Domain/Subject | Product/Subject - SystemMonitor | monitoring.py | 10 | INTEGRATED | No | Source scan: 13 functions, 13 real, 0 stubs |
| F-0263 | 01 Product/Domain/Subject | Product/Subject - Module Functions | monitoring.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0264 | 01 Product/Domain/Subject | Product/Subject - network_adaptive.py | network_adaptive.py | 10 | IMPLEMENTED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0265 | 46 API | API/Routes - openapi_spec.py | openapi_spec.py | 6 | IMPLEMENTED | Yes | Source scan: 6 functions, 6 real, 0 stubs |
| F-0266 | 46 API | API/Routes - podcast_routes.py | podcast_routes.py | 10 | INTEGRATED | No | Source scan: 14 functions, 14 real, 0 stubs |
| F-0267 | 01 Product/Domain/Subject | Product/Subject - podcast_store.py | podcast_store.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0268 | 01 Product/Domain/Subject | Product/Subject - populate_empty_tables.py | populate_empty_tables.py | 5 | IMPLEMENTED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0269 | 12 Case/Public Opinion | Case Management - pr_case_engine.py | pr_case_engine.py | 10 | INTEGRATED | No | Source scan: 14 functions, 14 real, 0 stubs |
| F-0270 | 12 Case/Public Opinion | Case Management - pr_case_integration.py | pr_case_integration.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0271 | 39 Evidence | Evidence Management - ProductionEvidence | production_evidence_contract.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0272 | 39 Evidence | Evidence Management - ProductionEvidenceContract | production_evidence_contract.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0273 | 25 AI Provider/Gateway | AI Gateway - provider_registry.py | provider_registry.py | 6 | IMPLEMENTED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0274 | 12 Case/Public Opinion | Case Management - public_opinion_cases.py | public_opinion_cases.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0275 | 22 Report | Report Generation - report_api.py | report_api.py | 10 | INTEGRATED | No | Source scan: 18 functions, 18 real, 0 stubs |
| F-0276 | 22 Report | Report Generation - report_engine.py | report_engine.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0277 | 22 Report | Report Generation - report_filter.py | report_filter.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0278 | 01 Product/Domain/Subject | Product/Subject - reprocess.py | reprocess.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0279 | 50 Production Runtime | Production Runtime - resident_health.py | resident_health.py | 10 | IMPLEMENTED | Yes | Source scan: 14 functions, 14 real, 0 stubs |
| F-0280 | 04 Source Library | Source/Adapter - resource_library.py | resource_library.py | 6 | IMPLEMENTED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0281 | 01 Product/Domain/Subject | Product/Subject - review_workflow.py | review_workflow.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0282 | 13 Risk Engine | Risk Engine - risk_engine.py | risk_engine.py | 2 | TESTED | Yes | Source scan: 2 functions, 2 real, 0 stubs |
| F-0283 | 50 Production Runtime | Production Runtime - run_production.py | run_production.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0284 | 01 Product/Domain/Subject | Product/Subject - run_supervised.py | run_supervised.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0285 | 50 Production Runtime | Production Runtime - runtime_bin.py | runtime_bin.py | 4 | TESTED | Yes | Source scan: 4 functions, 4 real, 0 stubs |
| F-0286 | 50 Production Runtime | Production Runtime - runtime_preflight.py | runtime_preflight.py | 10 | TESTED | Yes | Source scan: 14 functions, 14 real, 0 stubs |
| F-0287 | 01 Product/Domain/Subject | Product/Subject - safety_boundary.py | safety_boundary.py | 10 | TESTED | Yes | Source scan: 18 functions, 18 real, 0 stubs |
| F-0288 | 47 DB/Migration | DB/Migration - schema_registry.py | schema_registry.py | 3 | TESTED | Yes | Source scan: 3 functions, 3 real, 0 stubs |
| F-0289 | 48 Security/Audit | Security - security_scanner.py | security_scanner.py | 10 | TESTED | Yes | Source scan: 12 functions, 12 real, 0 stubs |
| F-0290 | 02 Repository/Runtime/Environment | Config/Environment - settings_module.py | settings_module.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0291 | 01 Product/Domain/Subject | Product/Subject - stability_monitor.py | stability_monitor.py | 10 | INTEGRATED | No | Source scan: 23 functions, 23 real, 0 stubs |
| F-0292 | 01 Product/Domain/Subject | Product/Subject - start_tunnel.py | start_tunnel.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0293 | 06 Subject Filter/Dedup | Subject Filter/Dedup - subject_classifier.py | subject_classifier.py | 10 | INTEGRATED | No | Source scan: 14 functions, 14 real, 0 stubs |
| F-0294 | 06 Subject Filter/Dedup | Subject Filter/Dedup - ProductContext | subject_context.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0295 | 06 Subject Filter/Dedup | Subject Filter/Dedup - SubjectContext | subject_context.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0296 | 06 Subject Filter/Dedup | Subject Filter/Dedup - Module Functions | subject_context.py | 6 | IMPLEMENTED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0297 | 06 Subject Filter/Dedup | Subject Filter/Dedup - subject_rules.py | subject_rules.py | 10 | INTEGRATED | No | Source scan: 14 functions, 14 real, 0 stubs |
| F-0298 | 01 Product/Domain/Subject | Product/Subject - swire_group.py | swire_group.py | 10 | INTEGRATED | No | Source scan: 17 functions, 17 real, 0 stubs |
| F-0299 | 01 Product/Domain/Subject | Product/Subject - system_features_api.py | system_features_api.py | 10 | INTEGRATED | No | Source scan: 16 functions, 16 real, 0 stubs |
| F-0300 | 01 Product/Domain/Subject | Product/Subject - system_guardian.py | system_guardian.py | 8 | INTEGRATED | No | Source scan: 8 functions, 8 real, 0 stubs |
| F-0301 | 50 Production Runtime | Production Runtime - system_health_api.py | system_health_api.py | 10 | INTEGRATED | No | Source scan: 18 functions, 18 real, 0 stubs |
| F-0302 | 01 Product/Domain/Subject | Product/Subject - system_watchdog.py | system_watchdog.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0303 | 21 Campaign/Topic | Campaign/Topic - topic_campaign.py | topic_campaign.py | 10 | INTEGRATED | No | Source scan: 45 functions, 45 real, 0 stubs |
| F-0304 | 21 Campaign/Topic | Campaign/Topic - topic_monitor_policy.py | topic_monitor_policy.py | 2 | IMPLEMENTED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0305 | 21 Campaign/Topic | Campaign/Topic - topic_note_detail_backfill.py | topic_note_detail_backfill.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0306 | 21 Campaign/Topic | Campaign/Topic - topic_snapshot.py | topic_snapshot.py | 3 | TESTED | Yes | Source scan: 3 functions, 3 real, 0 stubs |
| F-0307 | 01 Product/Domain/Subject | Product/Subject - tunnel_guardian.py | tunnel_guardian.py | 9 | INTEGRATED | No | Source scan: 9 functions, 9 real, 0 stubs |
| F-0308 | 48 Security/Audit | Security - PageRealityStatus | ui_data_audit.py | 1 | INTEGRATED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0309 | 48 Security/Audit | Security - UIRealityAuditor | ui_data_audit.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0310 | 01 Product/Domain/Subject | Product/Subject - update_reference.py | update_reference.py | 7 | INTEGRATED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0311 | 01 Product/Domain/Subject | Product/Subject - verify_system_e2e.py | verify_system_e2e.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0312 | 25 AI Provider/Gateway | AI Engine - VideoAnalysis | video_intelligence.py | 1 | IMPLEMENTED | Yes | Source scan: 1 functions, 1 real, 0 stubs |
| F-0313 | 25 AI Provider/Gateway | AI Engine - VideoIntelligenceEngine | video_intelligence.py | 2 | TESTED | Yes | Source scan: 2 functions, 2 real, 0 stubs |
| F-0314 | 01 Product/Domain/Subject | Product/Subject - web_monitor.py | web_monitor.py | 9 | INTEGRATED | No | Source scan: 9 functions, 9 real, 0 stubs |
| F-0315 | 01 Product/Domain/Subject | Product/Subject - web_monitor_v570.py | web_monitor_v570.py | 6 | INTEGRATED | No | Source scan: 6 functions, 6 real, 0 stubs |
| F-0316 | 21 Campaign/Topic | Campaign/Topic - web_topic_discovery.py | web_topic_discovery.py | 5 | IMPLEMENTED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0317 | 01 Product/Domain/Subject | Product/Subject - NotificationChannel | wechat_notifier.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0318 | 01 Product/Domain/Subject | Product/Subject - NotificationTemplates | wechat_notifier.py | 7 | IMPLEMENTED | No | Source scan: 7 functions, 7 real, 0 stubs |
| F-0319 | 01 Product/Domain/Subject | Product/Subject - PushPlusChannel | wechat_notifier.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0320 | 01 Product/Domain/Subject | Product/Subject - ServerChanChannel | wechat_notifier.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0321 | 01 Product/Domain/Subject | Product/Subject - WeChatNotifier | wechat_notifier.py | 10 | INTEGRATED | No | Source scan: 11 functions, 11 real, 0 stubs |
| F-0322 | 01 Product/Domain/Subject | Product/Subject - WeChatOfficialAccountChannel | wechat_notifier.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0323 | 01 Product/Domain/Subject | Product/Subject - WeComBotChannel | wechat_notifier.py | 3 | INTEGRATED | No | Source scan: 3 functions, 3 real, 0 stubs |
| F-0324 | 01 Product/Domain/Subject | Product/Subject - Module Functions | wechat_notifier.py | 1 | IMPLEMENTED | No | Source scan: 1 functions, 1 real, 0 stubs |
| F-0325 | 01 Product/Domain/Subject | Product/Subject - weekly_events.py | weekly_events.py | 5 | INTEGRATED | No | Source scan: 5 functions, 5 real, 0 stubs |
| F-0326 | 44 Browser/CDP/Login | Browser/CDP - weibo_login_manager.py | weibo_login_manager.py | 9 | INTEGRATED | No | Source scan: 9 functions, 9 real, 0 stubs |
| F-0327 | 03 Data Collection | Collector - xhs_cdp_collector.py | xhs_cdp_collector.py | 10 | INTEGRATED | No | Source scan: 28 functions, 28 real, 0 stubs |
| F-0328 | 01 Product/Domain/Subject | Product/Subject - NoteTypeClassifier | xhs_collection_optimizer.py | 2 | INTEGRATED | No | Source scan: 2 functions, 2 real, 0 stubs |
| F-0329 | 01 Product/Domain/Subject | Product/Subject - RedNoteLoginKeepalive | xhs_collection_optimizer.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
| F-0330 | 01 Product/Domain/Subject | Product/Subject - XHSCollectionOptimizer | xhs_collection_optimizer.py | 4 | INTEGRATED | No | Source scan: 4 functions, 4 real, 0 stubs |
| F-0331 | 01 Product/Domain/Subject | Product/Subject - Module Functions | xhs_collection_optimizer.py | 10 | INTEGRATED | No | Source scan: 11 functions, 11 real, 0 stubs |
| F-0332 | 44 Browser/CDP/Login | Browser/CDP - xhs_cookie_bridge.py | xhs_cookie_bridge.py | 10 | INTEGRATED | No | Source scan: 34 functions, 34 real, 0 stubs |
| F-0333 | 31 Orchestrator | Orchestrator - xhs_p0_orchestrator.py | xhs_p0_orchestrator.py | 10 | INTEGRATED | No | Source scan: 11 functions, 11 real, 0 stubs |
| F-0334 | 50 Production Runtime | Production Runtime - xhs_runtime_state.py | xhs_runtime_state.py | 10 | INTEGRATED | No | Source scan: 10 functions, 10 real, 0 stubs |
