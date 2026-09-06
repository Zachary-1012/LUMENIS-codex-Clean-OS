# 研究到ZBC落地索引（五态 + Admission链）

> 生成时间: 2026-09-06 20:35:26
> 数据源: intelligence_assets 表

## 铁边界声明

- **OSAI = Intelligence Core**，禁止成为ZBC runtime依赖。OSAI挂了ZBC必须独立运行。
- 研究准入必须经过: Evidence -> Evaluation -> Human Feedback -> Validation -> Generalization -> Admission
- 生命周期: CANDIDATE -> VALIDATED -> GENERALIZABLE -> ADMITTED
- 禁止 import OSAI 作为 runtime 依赖，禁止拷贝其业务代码。
- 共享只能通过版本化、可追溯的 Contract/Artifact。

## 总览统计

| 状态 | 资产数 | 占比 |
|------|--------|------|
| 已落地 | 95 | 13.4% |
| 已实现待验证 | 108 | 15.2% |
| 可直接复用 | 86 | 12.1% |
| 建议转化 | 420 | 59.1% |
| 仅研究不应转化 | 2 | 0.3% |
| **合计** | **711** | **100%** |

### 按产品归属

- **SHARED**: 451 资产
- **ZBC**: 260 资产

## 已落地

> 已在ZBC生产代码中实现（如设计系统V1.1、双域架构、风险引擎）

资产数: 95

### 01_ZBC专项研究

- **AST-0009** `ZBC_FEATURE_MAP_DUAL_DOMAIN_20260906`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

### 06_Security

- **AST-0088** `dual_domain_ai_risk_audit`
  - 来源: Governance | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

### 08_UI-UX

- **AST-0186** `ZBC_Design_System_V1.1`
  - 来源: OSAI | 产品: ZBC/SYSTEM | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0187** `ZBC_PAGE_LEVEL_DESIGN_V1.1`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0193** `ZBIP-ARCHITECTURE-MAP`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0194** `ZBIP-DESIGN-TOKENS`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0195** `ZBIP-FEATURE-OWNERSHIP`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0196** `ZBIP-ICON-SYSTEM`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0197** `ZBIP-MOTION-TOKENS`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

### 10_工程审计方法

- **AST-0451** `LUMENIS_ZBC_DUAL_DOMAIN_AUDIT`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0481** `dual_domain_ai_risk_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0482** `dual_domain_audit_data`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0483** `dual_domain_core_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0484** `dual_domain_ui_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0605** `AI-EXECUTION-CONSTITUTION-UI-RUNTIME-20260904`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0606** `AI-EXECUTION-MASTER-COMMAND-V2-20260904`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0607** `CANONICAL-AI-EXECUTION-BASELINE-V1-20260904`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0608** `CANONICAL-EXECUTION-V3-20260904`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0609** `CANONICAL-NAMING-AND-TWIN-SYNC`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0610** `CANONICAL_REGISTRY`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0611** `GOVERNANCE-AUTHORITY-MAP-20260904`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0612** `LUMENIS-ENGINEERING-GOVERNANCE-V1.0`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0613** `LUMENIS-INTELLIGENCE-OS-DUAL-CORE-ARCHITECTURE-v1.0`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0614** `PROGRESS`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0615** `RELEASE_AND_AUTORUN_GATE`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0616** `TWIN_EXECUTION_GATE`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0617** `UNIFIED_UI_UX_INFORMATION_ARCHITECTURE_V1`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0618** `WEB-NO-SCROLL-INTEGRATED-UI-EXECUTION-CONTRACT-20260904`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0619** `_t10_db_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0620** `_t10_evidence_test`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0621** `ai_provider_matrix_shardB`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0622** `api_matrix_shardC`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0623** `feature_registry`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0624** `feature_registry`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0625** `function_registry_canonical_t4`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0626** `hardcoded_path_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0627** `osai_module_call_graph_shardB`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0628** `schema_registry_t4`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0629** `security_verification_shardC`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0630** `subject_filter_audit_t3`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0631** `ui_only_disposition_shardC`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0632** `ui_page_audit_shardC`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0633** `00-GOVERNANCE__path_backup__split_report_api`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0634** `_split_report_api`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0635** `osai_engine_repository_registry`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0636** `scripts_e2e_loop_check`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0637** `scripts_inventory_feature_crosscheck`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0638** `scripts_inventory_feature_final_verify`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0639** `scripts_reconcile_capabilities`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0640** `scripts_shard_b_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0641** `tests__audit_system`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0642** `tests__diag_cdp_subproc`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0643** `tests__make_preview`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0644** `tests__s07_scan`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0645** `tests_e2e_cross_core_convergence`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0646** `tests_test_ai_channel_flag`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0647** `tests_test_ai_degrade`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0648** `tests_test_compliance_gate`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0649** `tests_test_kol_analysis`
  - 来源: ZBC-internal | 产品: ZBC/ZBMP | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0650** `tests_test_report_special`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0651** `tests_test_resource_guard`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0652** `tests_test_schedule_adapter`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0653** `tests_test_security_scanner_s2`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0654** `tests_test_topic_snapshot`
  - 来源: ZBC-internal | 产品: ZBC/CTH | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0655** `tests_test_v2_p0_2_3`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0656** `tests_test_v2_p0_modules`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0657** `tests_test_v2_p0_remaining`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0658** `active_brand_raw`
  - 来源: ZBC-internal | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0659** `build_feature_registry`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0660** `cross_repo_imports_raw`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0661** `fast_scanner`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0662** `fix_canonical_data`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0663** `fix_missing_os_import`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0664** `fix_osai_registry`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0665** `functions_raw`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0666** `hardcoded_paths_full`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0667** `hardcoded_paths_raw`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0668** `hardcoded_scan_full`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0669** `replace_hardcoded_paths`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0670** `routes_raw`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0671** `shard_d_scanner`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0672** `update_subject_rules`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0673** `IDENTITY-DELEGATION-PRODUCTION-BOUNDARY-V1.0`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0674** `UNIFIED-DATA-INTELLIGENCE-PIPELINE-V1.0`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0675** `CROSS_REPO_CONTRACT_BOUNDARY`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0676** `__init__`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0677** `lumenis_adapter`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0678** `HUMAN_CONTROL_GATE_v1`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0679** `COLLECTION_ACCURACY_GATE_v1`
  - 来源: ZBC-internal | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0680** `KOS_ACCOUNT_ASSET_TEMPLATE_v1`
  - 来源: ZBC-internal | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0681** `KOS_ENTITY_OWNERSHIP_CONTRACT_v1`
  - 来源: ZBC-internal | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0682** `KOS_RELEASE_BASELINE_v1`
  - 来源: ZBC-internal | 产品: ZBC/ZBMP | 证据: E4 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0683** `KOS_UI_INTERACTION_HIERARCHY_v1`
  - 来源: ZBC-internal | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0684** `__init__`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现

- **AST-0685** `repository_registry`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 已在ZBC生产代码中实现


## 已实现待验证

> 代码已写但未充分验证

资产数: 108

### 00_总览

- **AST-0003** `README-main-latest`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

### 01_ZBC专项研究

- **AST-0008** `ZBC_FEATURE_GAP_AUDIT_20260906`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

### 06_Security

- **AST-0087** `SOURCE-PROVENANCE-AUDIT`
  - 来源: Governance | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0089** `risk_audit`
  - 来源: Governance | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0090** `skill_agent_boundary_audit`
  - 来源: Governance | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0091** `track3_ai_risk_evidence_audit`
  - 来源: Governance | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

### 07_Data-Evidence-Evaluation

- **AST-0093** `test_browser_runtime_zbc_compliance`
  - 来源: OSAI | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0094** `test_canonical_data_and_evidence_graph`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0095** `test_contracts_baseline`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0096** `test_lumenis_cross_core`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0097** `test_lumenis_engine_layer`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0098** `test_lumenis_harness_runtime`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0099** `test_lumenis_p0`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0100** `test_lumenis_p0_contracts`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0101** `test_lumenis_p0_new_contracts`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0102** `test_lumenis_p0p1_convergence`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0103** `test_lumenis_phase3_runtime`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0104** `test_lumenis_skill_hub`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0105** `test_lumenis_skills_and_loop`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0106** `test_lumenis_v3_identity`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0107** `test_lumenis_v3_integration`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0108** `test_osai_engine`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0109** `test_v2_p0_2_3`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0110** `test_v2_p0_modules`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0111** `test_v2_p0_remaining`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0112** `test_v4_p0_p1_modules`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

### 09_Research-Hub

- **AST-0233** `ZACHARY-FULL-AUDIT-RESEARCH-SPEC-20260902`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0239** `AI-AUDIT-SCHEDULE`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0249** `R-2026-0005-zbip-unified-convergence-audit`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0250** `R-2026-0006-audit`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0253** `R-2026-0008-runtime-preflight`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0263** `AI-AUDIT-SCHEDULE`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0327** `ZACHARY-FULL-AUDIT-RESEARCH-SPEC-20260902`
  - 来源: DCC | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0335** `V0.5-EFFECTIVE-RULES-AUDIT`
  - 来源: DCC | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0371** `AUDIT_CAPABILITY_REGISTRY_20260901`
  - 来源: SICI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0372** `AUDIT_EFFECTIVE_RULES_20260901`
  - 来源: SICI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0373** `AUDIT_RUNTIME_PREFLIGHT_20260901`
  - 来源: SICI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0399** `R-2026-0005-zbip-unified-convergence-audit`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0400** `R-2026-0006-audit`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0403** `R-2026-0008-runtime-preflight`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0405** `audit_xhs_guangzhou_tgk_20notes`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0409** `AUDIT-SOURCE-FULL-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0410** `AUDIT-TWIN-STATUS-20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

### 10_工程审计方法

- **AST-0434** `AUDIT_BASELINE_XHS_TOPIC_DATA_20260903`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0435** `AUDIT_EXECUTION_HANDOFF_20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0436** `AUDIT_HANDOFF_20260902_UNIFIED_RESOURCE`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0445** `ZACHARY-FULL-AUDIT-RESEARCH-SPEC-20260902`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0447** `ZBC_AI_PROGRAMMING_AUDIT_REPORT_LIST_V1`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0448** `ZBC_AI_PROGRAMMING_AUDIT_REPORT_V1`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0449** `FINAL_RUNTIME_AUDIT`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0454** `SOURCE-PROVENANCE-AUDIT`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0471** `ai_provider_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0472** `api_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0473** `code_quality_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0475** `collector_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0476** `collector_frontend_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0477** `data_quality_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0478** `db_api_guardian_audit`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0485** `evaluation_system_audit`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0486** `evidence_chain_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0487** `gap_closure_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0488** `historical_data_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0491** `report_ai_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0492** `report_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0493** `risk_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0494** `skill_agent_boundary_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0499** `test_results_l1`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0500** `test_results_l1_l3`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0501** `test_results_l4`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0502** `test_results_l5`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0503** `test_summary_report`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0504** `track1_core_runtime_audit`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0507** `track2_collector_guardian_audit`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0508** `track2_guardian_verification`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E3 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0510** `track3_ai_risk_evidence_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0513** `track4_api_frontend_report_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0514** `track4_api_test_results`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0517** `ui_audit`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0545** `CROSS-REPO-AUDIT-RELEASE-GATE-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0546** `DUAL-REPO-FULL-AUDIT-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0547** `FINAL-AUDIT-AND-SPRINT-PLAN-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0553** `ZBC_OSAI_TWIN_REPO_FULL_AUDIT_20260902`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0554** `CANONICAL_CAPABILITY_AUDIT_20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0555** `CANONICAL_WRAP_PROGRESS_20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0556** `DEEP_LEARNING_CYCLE_LOG`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0557** `FILE_CLEANUP_MANIFEST_20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0558** `IC020_028_047_IMPLEMENTATION_EVIDENCE_20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0559** `IC021_039_040_IMPLEMENTATION_EVIDENCE_20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0560** `IC035_044_048_IMPLEMENTATION_EVIDENCE_20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0561** `IC_PRIORITY_BACKLOG_20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0562** `NAMING_SYNC_AUDIT_20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0563** `OWASP_AGENTIC_AUDIT_20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0564** `01_SOURCE_INVENTORY`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0565** `02_ARCHITECTURE_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0566** `03_CAPABILITY_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0567** `04_FUNCTION_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0568** `05_DATABASE_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0569** `06_CONTRACT_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0570** `07_OWNERSHIP_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0571** `08_DEPENDENCY_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0572** `09_UI_UX_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0573** `10_TICKET_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0574** `11_GAP_REGISTER`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0575** `12_FINAL_RECONCILIATION`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0576** `ENGINEERING-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0577** `P0-03-SECRETS-QUARANTINE-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0578** `_SPEC`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证

- **AST-0598** `20_unverified_items`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 代码/规则已实现，待充分验证


## 可直接复用

> 研究结论可直接用于现有模块（如公关话术公式到案例库）

资产数: 86

### 00_总览

- **AST-0006** `公关话术模版-舆情信息`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

### 01_ZBC专项研究

- **AST-0007** `ZACHARY_ZBC_TWIN_REPO_CONTRACT_V1`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0014** `CONTRACT_IC035_044_048_20260904`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0015** `CONTRACT_IC047_20260904`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

### 02_ZBMP研究

- **AST-0025** `KOS_CONTENT_TEMPLATE_EXECUTION_SPEC`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0030** `brand-marketing-knowledge-06-real-cases-taikoo-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0035** `brand-marketing-knowledge-11-creative-engine-v2-anti-templat`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0053** `liangzi-interview-record-v1`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

### 05_Runtime

- **AST-0077** `ZACHARY-DOMAIN-ADAPTER-CONTRACT-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0079** `ZACHARY-INTERNAL-LEARNING-CONTRACT-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0081** `ZACHARY-LEARNING-DATA-CONTRACT-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

### 07_Data-Evidence-Evaluation

- **AST-0113** `2026-08-31-capability-delta-evaluator`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0114** `2026-08-31-dev-container-verification-runtime`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0115** `2026-08-31-github-actions-reusable-workflow`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0116** `2026-09-01-safe-xhs-collection-contract`
  - 来源: ADRH | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0117** `INDEX`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0118** `2026-08-31-capability-delta-evaluator`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0119** `2026-08-31-dev-container-verification-runtime`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0120** `2026-08-31-github-actions-reusable-workflow`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0121** `2026-09-01-safe-xhs-collection-contract`
  - 来源: ADRH | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0122** `INDEX`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0123** `CASE-2026-CONTENT-BENCHMARK-001`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0124** `CASE-2026-CONTENT-BENCHMARK-001`
  - 来源: ADRH | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

### 08_UI-UX

- **AST-0182** `UI-IA-INTERACTION-RESEARCH-CONTRACT-V1-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0185** `UI_UX_NON_REGRESSION_CONTRACT`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

### 09_Research-Hub

- **AST-0216** `CASE-LIBRARY`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0224** `ZACHARY-DOMAIN-ADAPTER-CONTRACT-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0226** `ZACHARY-INTERNAL-LEARNING-CONTRACT-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0228** `ZACHARY-LEARNING-DATA-CONTRACT-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0235** `ZACHARY-ZBC-BIDIRECTIONAL-LEARNING-CONTRACT-20260901`
  - 来源: ADRH | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0242** `TASK-QUEUE-INTEGRATION-PROTOCOL`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0243** `AI-WORK-LOG-AND-REALTIME-PUSH-PROTOCOL`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0244** `CHATGPT-INTERVENTION-PROTOCOL`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0245** `CONTINUOUS-RESEARCH-AND-DEVELOPMENT-POLICY`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0254** `CASE-2026-CONTENT-0001`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0260** `ZACHARY-ZBC-BIDIRECTIONAL-LEARNING-CONTRACT-20260901`
  - 来源: ADRH | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0266** `TASK-QUEUE-INTEGRATION-PROTOCOL`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0267** `AI-WORK-LOG-AND-REALTIME-PUSH-PROTOCOL`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0268** `CHATGPT-INTERVENTION-PROTOCOL`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0282** `13-implementation-contracts`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0292** `AI-LEARNING-CASE-LIBRARY`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0305** `RESEARCH-CASE-LIBRARY`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0311** `V04-CHANGE-CONTRACT`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0312** `V041-CHANGE-CONTRACT`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0329** `ZACHARY-ZBC-BIDIRECTIONAL-LEARNING-CONTRACT-20260901`
  - 来源: DCC | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0351** `INDUSTRY-CASE-STUDY-MULTIAGENT-OS-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0354** `ZELL-LOOP-TEMPLATE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0355** `contract-updates-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0364** `pattern-contract-first-tables-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0392** `SHADOW_LEARNING_PROTOCOL`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0404** `CASE-2026-CONTENT-0001`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0414** `KOS-BENCHMARK-CASES-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

### 10_工程审计方法

- **AST-0439** `AI-COLLABORATION-PROTOCOL`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0444** `SHADOW-LEARNING-PROTOCOL`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0446** `CONTINUOUS-RESEARCH-AND-DEVELOPMENT-POLICY`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0453** `PR_TEMPLATE_CASE_LIBRARY_REQUIREMENT_V1.0`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0457** `WEB-NOSCROLL-CONTRACT-original`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0518** `CTR-BROWSER-RUNTIME-P0-01`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0519** `CTR-CANONICAL-METRICS-P0-01`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0520** `CTR-EVENT-CLUSTER-P1-01`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0521** `CTR-KOS-METRICS-P1-01`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0522** `CTR-OBSERVABILITY-P0-01`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0523** `CTR-XHS-LEADS-P1-01`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0524** `P0-04-task-contract-v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0525** `P0-05-trace-contract-v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0526** `P0-06-evidence-contract-v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0527** `P0-07-evaluation-contract-v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0528** `P0-08-lifecycle-contract-v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0529** `P0-09-skill-contract-v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0530** `P0-10-ai-gateway-contract-v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0531** `GLOBAL_CAPABILITY_STYLE_CONVERGENCE_GATE_v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0532** `HUMAN_CONTROL_GATE_v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0533** `KOS_ACCOUNT_ASSET_TEMPLATE_v1`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0534** `KOS_ENTITY_OWNERSHIP_CONTRACT_v1`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0535** `KOS_RELEASE_BASELINE_v1`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E4 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0536** `KOS_UI_INTERACTION_HIERARCHY_v1`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0537** `module_rules_v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0538** `podcast-ai-runtime-bridge-v1.schema`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0539** `runtime_event_v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0540** `global-runtime-evidence-v1.schema`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0541** `module-compliance-v1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0544** `CONTRACT-25-RECONCILIATION-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0589** `11_contract_matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

### 11_前沿研究

- **AST-0687** `01-CASE-LIBRARY`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0708** `05-IC-052-EMBEDDED-BROWSER-SURFACE-CONTRACT`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块

- **AST-0709** `05-IC-053-VISION-DOM-HYBRID-CONTRACT`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 研究结论可直接复用到现有模块


## 建议转化

> 研究有价值但需要工程化转化（如AI浏览器研究到内置浏览器）

资产数: 420

### 00_总览

- **AST-0001** `INTELLIGENCE_LIBRARY_ARCHITECTURE_V1.0`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0002** `OSAI_ZBC_研究汇编总目录_20260906`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0004** `README`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0005** `THREE_REPO_FEEDING_RULE_V1.0_20260906`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 01_ZBC专项研究

- **AST-0010** `00_P0_MASTER_ARCHITECTURE`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0011** `01-three-pillar-overview`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0012** `ADOPTION_EVAL_2026-09`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0013** `CANONICAL_REGISTRY_ALIGNMENT_P6_SYNC`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0016** `CREATIVE_METHODS_2026`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0017** `INTELLIGENCE_REGISTRY`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0018** `RESEARCH_2026-09-B`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0019** `RESEARCH_2026-09-C-CONSTRAINT`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0020** `RESEARCH_2026-09`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0021** `UDIP_V1_CONVERGENCE_COMPLETE_SYNC`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0022** `UDIP_V1_P345_SYNC`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0023** `UDIP_V1_SYNC_REGISTRY`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 02_ZBMP研究

- **AST-0024** `FINAL_DATA_PIPELINE_KOS_KOC_UGC_IMPLEMENTATION_DIRECTIVE`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0026** `brand-marketing-knowledge-02-cannes-launch-expo-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0027** `brand-marketing-knowledge-03-crosscategory-pitch-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0028** `brand-marketing-knowledge-04-global-4a-creative-engine-20260`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0029** `brand-marketing-knowledge-05-luxury-pitch-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0031** `brand-marketing-knowledge-07-global-2026-trends-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0032** `brand-marketing-knowledge-08-meta-framework-seed-to-world-20`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0033** `brand-marketing-knowledge-09-zhipu-glm47-second-opinion-2026`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0034** `brand-marketing-knowledge-10-real-pitch-l3l0-and-topic-conta`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0036** `brand-marketing-knowledge-12-three-party-perspective-adaptat`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0037** `brand-marketing-knowledge-13-emotional-resonance-kdrama-lite`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0038** `brand-marketing-knowledge-14-emo-role-adaptation-and-osai-lo`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0039** `brand-marketing-knowledge-15-luxury-quiet-narrative-and-osai`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0040** `brand-marketing-knowledge-16-rules-eng-round-pitch-export-ca`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0041** `brand-marketing-knowledge-17-marketing-calendar-kotler-cook-`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0042** `brand-marketing-knowledge-18-marketing-loop-edit-ready-20260`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0043** `brand-marketing-knowledge-19-marketing-loop-frontend-2026090`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0044** `brand-marketing-knowledge-20-edit-closed-loop-overseas-nodes`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0045** `brand-marketing-knowledge-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0046** `brand-marketing-knowledge-21-overseas-cross-csv-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0047** `brand-marketing-knowledge-22-region-overseas-matrix-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0048** `brand-marketing-knowledge-23-global-regions-overseas-ui-2026`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0049** `brand-marketing-knowledge-24-eastasia-oceania-overseas-video`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0050** `brand-marketing-knowledge-25-podcast-playbook-desensitized-2`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0051** `2026-09-03-podcast-intelligence`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0052** `UI_REFERENCE_XIAOYUZHOU_V1`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 03_CTH研究

- **AST-0054** `P0-INSTRUCTION`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0055** `P0-RESEARCH-REPORT`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0056** `P0-STATUS`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 04_OSAI核心技术

- **AST-0057** `s01`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0058** `s02`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0059** `s03`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0060** `s04`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0061** `s05`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0062** `s06`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0063** `s07`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0064** `s08`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0065** `s09`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0066** `s10`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0067** `s11`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0068** `s12`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0069** `learning_assets`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0070** `_watermark`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0071** `zbc-evidence-20260905T100019Z.manifest`
  - 来源: OSAI | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 05_Runtime

- **AST-0072** `LOCAL_AI_CONTINUOUS_RUNTIME_P0`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0073** `ADR-0001-hub-no-devcontainer`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0074** `CONTENT-INTELLIGENCE-SPEC-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0075** `ZACHARY-AI-GROWTH-MODEL-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0076** `ZACHARY-CAPABILITY-BENCHMARK-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0078** `ZACHARY-EXPERIENCE-SCHEMA-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0080** `ZACHARY-INTERNAL-MATURATION-AND-DOMAIN-ISOLATION-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0082** `ZACHARY-LEARNING-PROMOTION-ENGINE-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0083** `ZACHARY-MEMORY-LIFECYCLE-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0084** `ZACHARY_ZBC_AI_PROGRAMMING_BASELINE_V1`
  - 来源: OSAI | 产品: ZBC/SYSTEM | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 06_Security

- **AST-0085** `CROSS-REPO-OWNERSHIP-INCIDENT-2026-09-01`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0086** `XHS-ACCOUNT-SAFETY-INCIDENT-2026-08-31`
  - 来源: SICI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 07_Data-Evidence-Evaluation

- **AST-0092** `e2e_cross_core_convergence`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0125** `agent-rounds`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0126** `084108534b97`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0127** `0a4301841ed1`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0128** `10e1654e2f56`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0129** `13cfa59d5fe3`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0130** `18bdf5bdef6c`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0131** `1aec0e0accab`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0132** `1b1d3cc6b5a4`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0133** `281f9b49b8eb`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0134** `3095496731a2`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0135** `3403b928f05a`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0136** `3482547b9057`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0137** `35deb6671b8f`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0138** `365e38430c2c`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0139** `381f05043ff3`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0140** `390ece0a97b0`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0141** `3a49e7a158d6`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0142** `3e6e928c5974`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0143** `40dad4feb096`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0144** `48601a283393`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0145** `4a2114c27b0d`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0146** `4db671b77d3c`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0147** `4f94520b52e0`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0148** `530b0f38267b`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0149** `5bdad42dcc73`
  - 来源: DCC | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0150** `69956f034317`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0151** `6b261cb13bd6`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0152** `73911700a3a2`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0153** `7440a3e12ebc`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0154** `7504c0d3d576`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0155** `7a1b092de402`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0156** `7b8fa83ba2ea`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0157** `82c953331640`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0158** `83b9a7ff7703`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0159** `83d8f7fdf646`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0160** `8564da7edaf8`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0161** `8725bd27af95`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0162** `888c15378446`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0163** `9062d0417938`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0164** `9b6505234bb2`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0165** `9de2cad3f1da`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0166** `9f768136d299`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0167** `b002fd5e7199`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0168** `b32548f722e1`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0169** `b4c6d025c93b`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0170** `b714db472e42`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0171** `b906cdf4c5b9`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0172** `c895d9b9f8e4`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0173** `d45845ad88ce`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0174** `da37064737dc`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0175** `dcc392025fe8`
  - 来源: DCC | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0176** `ec29a6e0326b`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0177** `f37e2f82a70e`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0178** `f77a76ca2acc`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0179** `fa3cd3dabdd8`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0180** `fde4b72bde68`
  - 来源: OSAI | 产品: SHARED | 证据: E2 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 08_UI-UX

- **AST-0183** `UI_DELETE_MANIFEST`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0184** `UI_UX_ARCHITECTURE_EXECUTION_TASK`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0188** `ZBIP-ARCHITECTURE-MAP`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0189** `ZBIP-DESIGN-TOKENS`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0190** `ZBIP-FEATURE-OWNERSHIP`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0191** `ZBIP-ICON-SYSTEM`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0192** `ZBIP-MOTION-TOKENS`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0198** `FINAL_PRODUCT_EXECUTION_MASTER_DIRECTIVE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0199** `FINAL_UI_UX_IMPLEMENTATION_DIRECTIVE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0200** `LEARNING-UI-FUNCTIONALIZATION`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0201** `UI-HARD-RESET-LEARNING-20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0202** `XUJING-UI-STANDARD`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 09_Research-Hub

- **AST-0203** `2026-09-04-language-brand-life-intelligence-research`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0204** `BRAND-LIFE-PHILOSOPHY-RESEARCH-BASELINE`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0205** `LANGUAGE-BRAND-LIFE-INTELLIGENCE-RESEARCH-2026-09-04`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0206** `LEARNING-UNITS-REGISTRY`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0207** `UNIFIED-DATA-INTELLIGENCE-PIPELINE-V1.0`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0208** `00-PHILOSOPHY`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0209** `01-LIFE-SYSTEMS`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0210** `02-AI-AGENT`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0211** `03-LIFE-SCIENCE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0212** `04-LINGUISTICS-NARRATIVE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0213** `05-NAMING-RESEARCH`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0214** `06-MINIMAX-RESEARCH`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0215** `README`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0217** `README`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0218** `THREE-REPOSITORY-VALIDATION`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0219** `ZBIP_UNIFIED_README`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0220** `ADR-0001-hub-no-devcontainer`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0221** `CONTENT-INTELLIGENCE-SPEC-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0222** `ZACHARY-AI-GROWTH-MODEL-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0223** `ZACHARY-CAPABILITY-BENCHMARK-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0225** `ZACHARY-EXPERIENCE-SCHEMA-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0227** `ZACHARY-INTERNAL-MATURATION-AND-DOMAIN-ISOLATION-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0229** `ZACHARY-LEARNING-PROMOTION-ENGINE-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0230** `ZACHARY-MEMORY-LIFECYCLE-v1`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0231** `M5-ACCELERATED-FULL-INTEGRATION-STATUS-20260902`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0232** `M5-FULL-INTEGRATION-STATUS-20260901`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0234** `ZACHARY-IMMUTABLE-BASELINE-20260902`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0236** `ZBIP_EXECUTION_LOG_2026-08-31`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0237** `ZBIP_EXECUTION_LOG_2026-09-02`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0238** `ZACHARY-AI-CONSOLIDATION-LOG-20260901`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0240** `DOUBAO-HANDOFF-R-2026-0002`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0241** `DOUBAO-HANDOFF-R-2026-0006-AND-R7-FOR-CHATGPT`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0246** `R-2026-0002-capability-delta-research`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0247** `R-2026-0003-safe-xhs-collection`
  - 来源: ADRH | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0248** `R-2026-0004-dual-endpoint-topic-account-cookie-strategy`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0251** `R-2026-0006-credential-sanitization`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0252** `R-2026-0007-ci-secret-scan-fix`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0255** `.gitkeep`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0256** `M5-ACCELERATED-FULL-INTEGRATION-STATUS-20260902`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0257** `M5-FULL-INTEGRATION-STATUS-20260901`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0258** `OSAI_CONTRIBUTION_BRIDGE`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0259** `ZACHARY-IMMUTABLE-BASELINE-20260902`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0261** `ZBIP_EXECUTION_LOG_2026-08-31`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0262** `ZACHARY-AI-CONSOLIDATION-LOG-20260901`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0264** `DOUBAO-HANDOFF-R-2026-0002`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0265** `DOUBAO-HANDOFF-R-2026-0006-AND-R7-FOR-CHATGPT`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0269** `00-README`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0270** `01-whitepaper`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0271** `02-capability-radar`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0272** `03-competitive-matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0273** `04-architecture-2030`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0274** `05-experience-engine`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0275** `06-research-to-code`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0276** `07-ai-browser`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0277** `08-proactive-intelligence`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0278** `09-safety-permission-sandbox`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0279** `10-evaluation-framework`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0280** `11-roadmap`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0281** `12-not-to-do`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0283** `14-market-intel-radar`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0284** `15-synthesis-flow`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0285** `16-cth-poms-report`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0286** `17-zbmp-report`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0287** `18-vision-2029`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0288** `19-roadmap-master`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0289** `capability_registry`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0290** `records`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0291** `AI-INTEGRATION`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0293** `CONTINUOUS-RESEARCH-POLICY`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0294** `DEVELOPMENT-LOG`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0295** `DUAL_REPO_RELEASE_POLICY`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0296** `DUAL_REPO_RELEASE_STATE`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0297** `LEARNING-RUNTIME`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0298** `LEARNING-SHADOW-ARCHITECTURE`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0299** `PLATFORM-VERIFICATION-RUNTIME`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0300** `PRE_CHANGE_THREE_REPO_CHECKLIST`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0301** `PRODUCTION-GATE-XHS-APP`
  - 来源: DCC | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0302** `PRODUCT_NAMING_BASELINE`
  - 来源: DCC | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0303** `REPOSITORY-FACT-BASELINE`
  - 来源: DCC | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0304** `RESEARCH-2026-08-31-CONTINUOUS-ENGINEERING`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0306** `RESEARCH-LEARNING-DATABASE`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0307** `RESEARCH-LEARNING-RUNTIME`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0308** `ROADMAP`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0309** `THREE_REPOSITORY_SYSTEM_MATRIX`
  - 来源: DCC | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0310** `V04-ARCHITECTURE`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0313** `V041-EVIDENCE-SCHEMA`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0314** `V041-LEARNING-ARCHITECTURE`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0315** `V041-P2-EVIDENCE-BUNDLE`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0316** `V041-SHADOW-LEARNING`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0317** `XHS-ACCOUNT-SAFETY-INCIDENT-2026-08-31`
  - 来源: DCC | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0318** `XHS-REDNOTE-BROWSER-GATE-2026-08-31`
  - 来源: DCC | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0319** `XHS-REDNOTE-SAFE-ARCHITECTURE-V2-2026-08-31`
  - 来源: DCC | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0320** `XHS-RESEARCH-GATE-2026-08-31`
  - 来源: DCC | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0321** `XHS-TOPIC-MONITOR-GLOBAL-ADAPTATION-GATE-V2-2026-08-31`
  - 来源: DCC | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0322** `XHS-TOPIC-MONITOR-TEMPORARY-GATE-V1-2026-08-31`
  - 来源: DCC | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0323** `Z-BRAND-INTEGRATION`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0324** `ZACHARY-AI-AND-CONTENT-INTEGRATION-LOG-2026-09-01`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0325** `ZACHARY-CHAT-LOG-2026-09-01`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0326** `ZACHARY-CONTENT-INTELLIGENCE-SUPPLEMENT-2026-09-01`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0328** `ZACHARY-IMMUTABLE-BASELINE-20260902`
  - 来源: DCC | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0330** `ZBIP_CROSS_REPOSITORY_BASELINE`
  - 来源: DCC | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0331** `ZBIP_EXECUTION_LOG_2026-08-31`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0332** `ZBIP_EXECUTION_LOG_2026-09-02`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0333** `ZBMP-GLOBAL-BIL-RESEARCH-MASTER-LOG-2026-09-01`
  - 来源: DCC | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0334** `product-spec`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0336** `2026-09-02-zachary-ai-zbc-research-development-log`
  - 来源: DCC | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0337** `ZACHARY-AI-CONSOLIDATION-LOG-20260901`
  - 来源: DCC | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0338** `AI_CONTINUOUS_DEEP_LEARNING_EXECUTION_V1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0339** `APP_PHASE_GATE_20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0340** `CANONICAL_CAPABILITY_EXECUTION_SPEC_V1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0341** `CURRENT_PROJECT_ALIGNMENT_2026-09-05`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0342** `NAMING-TERMINOLOGY-COMMENT-RUNTIME-GUARDRAILS-V1-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0343** `P0_ZACHARY_MODEL_INDEPENDENCE_20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0344** `SYSTEM_APP_PRODUCT_BOUNDARIES_V1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0345** `FINAL_EXECUTION_COMMAND`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0346** `UI_DATA_PODCAST_BUILD_PLAN_V1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0347** `UI_DATA_PODCAST_RESEARCH_SPEC_V2`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0348** `OSAI_MOBILE_APP_UI_SPEC_V1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0349** `COALA-MEMORY-INDEX`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0350** `CTR-EVENT-CLUSTER-P1-01`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0352** `ZELL-INDEX`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0353** `ZELL-LOOP-001-P0B-AUTO-RECONCILE-20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0356** `github-benchmarks-02-agent-skills-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0357** `github-benchmarks-03-resilience-security-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0358** `github-benchmarks-04-collector-ai-observability-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0359** `github-benchmarks-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0360** `learning-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0361** `legacy-snapshot-vs-frontier-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0362** `pattern-ai-channel-stable-20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0363** `pattern-canonical-wrap-sop-20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0365** `pattern-data-driven-motion-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0366** `report-convergence-gap10-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0367** `seed-sumeru-taiji-mapping-AQ-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0368** `sqlite-alembic-migration-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0369** `zell-p0-loop-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0370** `ZBC_AI_OPINION_INTELLIGENCE_UPGRADE_BASELINE_V1`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0374** `CAPABILITY_REGISTRY`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0375** `CONTINUOUS-RESEARCH-POLICY`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0376** `CROSS-REPO-OWNERSHIP-INCIDENT-2026-09-01`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0377** `PRODUCT_NAMING_BASELINE`
  - 来源: SICI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0378** `THREE_REPOSITORY_MATRIX_POINTER`
  - 来源: SICI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0379** `XHS-ACCOUNT-SAFETY-INCIDENT-2026-08-31`
  - 来源: SICI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0380** `XHS-REDNOTE-RESEARCH-DECISION-2026-08-31`
  - 来源: SICI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0381** `XHS-REDNOTE-SAFE-ARCHITECTURE-V2-2026-08-31`
  - 来源: SICI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0382** `XHS-RESEARCH-SYNTHESIS-2026-08-31`
  - 来源: SICI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0383** `XHS-TOPIC-MONITOR-GLOBAL-ADAPTATION-RESEARCH-V2-2026-08-31`
  - 来源: SICI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0384** `XHS-TOPIC-MONITOR-TEMPORARY-STRATEGY-V1-2026-08-31`
  - 来源: SICI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0385** `ZBIP_CROSS_REPOSITORY_BASELINE`
  - 来源: SICI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0386** `ZBIP_EXECUTION_LOG_2026-08-31`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0387** `ZBIP_EXECUTION_LOG_2026-09-02`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0388** `CTH-POMS_LEARNING_LIBRARY`
  - 来源: SICI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0389** `PLATFORM_LEARNING_LIBRARY_v2`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0390** `PLATFORM_LEARNING_LIBRARY_v3`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0391** `RESEARCH_LEARNING_SCHEMA`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0393** `THREE_REPOSITORY_VALIDATION_RULES`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0394** `cth_poms_learning_records`
  - 来源: SICI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0395** `platform_learning_records`
  - 来源: SICI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0396** `R-2026-0002-capability-delta-research`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0397** `R-2026-0003-safe-xhs-collection`
  - 来源: ADRH | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0398** `R-2026-0004-dual-endpoint-topic-account-cookie-strategy`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0401** `R-2026-0006-credential-sanitization`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0402** `R-2026-0007-ci-secret-scan-fix`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0406** `detail_sample_6a959633_redacted`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0407** `human_browse_behavior_session1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0408** `redacted_xhs_guangzhou_tgk_20notes`
  - 来源: OSAI | 产品: ZBC/CTH | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0411** `AUTO-RECONCILE-P0B-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0412** `CDF-HAILAN-DEEP-RESEARCH-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0413** `KOS-BASELINE-HAILAN-CDF-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0415** `KOS-COLLECTION-SUITE-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0416** `KOS-HAINAN-CDF-PHASE-A-RUNBOOK-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0417** `KOS-INTEL-IMPLEMENTATION-EVIDENCE-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0418** `KOS-METRICS-IMPLEMENTATION-EVIDENCE-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0419** `KOS-RULES-CONTENT-ENGAGEMENT-20260903`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0420** `KOS-ZHIPU-REPLY-IMPLEMENTATION-EVIDENCE-20260904`
  - 来源: OSAI | 产品: ZBC/ZBMP | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0421** `ZELL-BRIDGE-20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0422** `ZELL-P0CDEF-20260904`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0423** `auto-round-20260903-140627`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0424** `category-emotion-narratives-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0425** `eng-round-20260903-142407`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0426** `global-sales-festivals-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0427** `kotler-marketing-theory-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0428** `luxury-quiet-luxury-narrative-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0429** `marketing-calendar-2026-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0430** `overseas-social-algorithm-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0431** `overseas-social-algorithm-2026update-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0432** `timcook-business-growth-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0433** `vertical-industry-nodes-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 10_工程审计方法

- **AST-0437** `CHANGELOG`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0438** `WORK_LOG_20260902_RESOURCE_EVOLUTION`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0440** `CAPABILITY-REGISTRY`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0441** `GLOBAL-CROSS-REPOSITORY-BASELINE`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0442** `PLATFORM_BASELINE`
  - 来源: ADRH | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0443** `RESEARCH-LEARNING-SCHEMA`
  - 来源: ADRH | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0450** `INTERNAL_BROWSER_REQUIREMENT_V1.0`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0452** `PR_DESCRIPTION`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0455** `V2_SUPPLEMENT_DATA_QUALITY`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0456** `VISUAL_REFRESH_AND_APPLEID_ACCOUNT_REQUIREMENT_V1.0`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0458** `ZBC_ASSET_DECISIONS_V1.0_20260906`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0459** `ZBC_CONSOLIDATED_WORK_LEDGER_V1.0_20260906`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0460** `ZBC_OPTIMIZATION_MIGRATION_INVENTORY_V1.0`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0461** `_api_routes_extracted`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0462** `_batch3_browser_check`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0463** `_batch3_filtered`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0464** `_batch3_import_results`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0465** `_batch3_import_results_v2`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0466** `_batch3_verification_summary`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0467** `_module_scan_raw`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0468** `_ref_graph`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0469** `_status_results`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0470** `_table_info`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0474** `code_quality_scan`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0479** `db_empty_tables_classification`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0480** `db_empty_tables_classification`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0489** `module_inventory`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0490** `module_inventory`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0495** `source_provenance`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0496** `source_provenance_scan`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0497** `source_refs`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0498** `table_schemas`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0505** `track1_empty_tables_classification`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0506** `track1_verification_results`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0509** `track3_ai_call_verification`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0511** `track3_full_verification`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0512** `track3_subject_rules_verification`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0515** `track4_frontend_security_error_verification`
  - 来源: ZBC-internal | 产品: ZBC/SYSTEM | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0516** `track4_report_generation_verification`
  - 来源: ZBC-internal | 产品: ZBC/SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0542** `AGENT-YAML-SPEC`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0543** `AI-PROGRAMMING-CONSTRUCTION-REPORT-V1-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0548** `FINAL-RECONCILIATION-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0549** `FIRST-TIER-RND-BASELINE-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0550** `MASTER-ENGINEERING-MATRIX-20260903`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0551** `P0-FRONTEND-HARDCODED-AUTH-ASSESSMENT-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0552** `S1-ZHIPU-AI-ENHANCEMENT-EVIDENCE-20260902`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0579** `01_full_inventory`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0580** `02_file_reconciliation`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0581** `03_sha_reconciliation`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0582** `04_database_reconciliation`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0583** `05_module_reconciliation`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0584** `06_function_reconciliation`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0585** `07_symbol_function_reconciliation`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0586** `08_dependency_graph`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0587** `09_communication_graph`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0588** `10_ownership_matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0590** `12_capability_matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0591** `13_duplicate_matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0592** `14_research_matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0593** `15_evidence_matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0594** `16_migration_matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0595** `17_security_findings`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0596** `18_baseline_matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0597** `19_supplement_matrix`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0599** `21_conflict_items`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0600** `22_final_convergence`
  - 来源: OSAI | 产品: SHARED | 证据: E4 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0601** `000-ZERO-SEQUENCE`
  - 来源: ZBC-internal | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0602** `AI_CONTINUOUS_DEEP_LEARNING_V1`
  - 来源: ZBC-internal | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0603** `CANONICAL_CAPABILITY_CONVERGENCE_V1`
  - 来源: ZBC-internal | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

### 11_前沿研究

- **AST-0686** `00-RESEARCH-MAP`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0688** `02-PAPER-TRACKING`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0689** `03-TECHNOLOGY-RADAR`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0690** `04-IMPROVEMENT-QUEUE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0691** `05-IC-029-NPS-DRI-EVALUATION`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0692** `05-IC-030-PODCAST-8STEP-SOP`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0693** `05-IC-031-AI-SEMANTIC-LAYER`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0694** `05-IC-032-MODEL-COMPRESSION-EVAL`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0695** `05-IC-033-EMOTIONAL-AROUSAL`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0696** `05-IC-034-VISION-MODEL-SELECTION`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0697** `05-IC-036-BRAND-NAMING-PIPELINE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0698** `05-IC-037-MEMORY-ARCHITECTURE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0699** `05-IC-038-REWARD-DESIGN`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0700** `05-IC-041-TALENT-TIERING-STRATEGY`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0701** `05-IC-042-CUSTOM-PERSUASION-STORYLINE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0702** `05-IC-043-LONG-HORIZON-RELIABILITY`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0703** `05-IC-045-BRAND-NARRATIVE-WORLD`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0704** `05-IC-046-COMPLEXITY-EMERGENCE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0705** `05-IC-049-AGENTIC-KNOWLEDGE-GRAPH`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0706** `05-IC-050-AI-NATIVE-APP-ARCHITECTURE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0707** `05-IC-051-AI-BROWSER-AGENT-FRONTIER`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0710** `05-RESEARCH-AI-STANDALONE-APP-ARCHITECTURE`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化

- **AST-0711** `05-RESEARCH-BROWSER-AGENT-COMPUTER-USE-2026`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 有工程价值，需经Admission链转化


## 仅研究不应转化

> 纯理论/探索性研究，不进入生产（如命名候选、部分哲学研究）

资产数: 2

### 08_UI-UX

- **AST-0181** `DESIGN_PHILOSOPHY_SEED_MUSTERY_TAIJI_V1`
  - 来源: OSAI | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 纯理论/探索性，不进入生产

### 10_工程审计方法

- **AST-0604** `PRODUCT_NAMING_AND_TERMINOLOGY`
  - 来源: ZBC-internal | 产品: SHARED | 证据: E3 | Admission: CANDIDATE
  - 理由: 纯理论/探索性，不进入生产


## Admission 准入链状态分布

- **CANDIDATE**: 711 资产

### Admission 链说明

```
Evidence -> Evaluation -> Human Feedback -> Validation -> Generalization -> Admission
  │           │            │                │            │              │
  ▼           ▼            ▼                ▼            ▼              ▼
CANDIDATE -> VALIDATED -> GENERALIZABLE -> ADMITTED
```

- **CANDIDATE**: 研究资产已入库，待评估（默认状态）
- **VALIDATED**: 经Evidence+Evaluation验证，技术可行性确认
- **GENERALIZABLE**: 经Human Feedback，可泛化到ZBC多场景
- **ADMITTED**: 经完整Admission链，准入ZBC生产转化（需人工审批）

## OSAI 六条红线（强制执行）

1. OSAI不拥有ZBC/GGI Production Truth
2. 不直接修改两个产品的生产数据库
3. **不得成为ZBC启动/采集/分析/报告/核心业务的runtime依赖**
4. 不复制两个产品的业务代码
5. 共享只能通过版本化、可追溯的Contract/Artifact
6. 研究结论不得自动变生产规则
