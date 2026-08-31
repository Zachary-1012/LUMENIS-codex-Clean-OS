# ZBC-UPA-001 统一生产架构收敛工程 - 施工台账

## TASK 基本信息

| 字段 | 内容 |
|------|------|
| **TASK ID** | ZBC-UPA-001 |
| **项目** | ZBC / DCC / SICI Unified Production Architecture |
| **版本** | v1.0 |
| **基线** | commit 40073df (v5.8.9) |
| **目标** | 在不破坏现有生产能力的前提下，对ZBC仓库进行统一架构治理、运行环境治理、依赖治理、代码治理和Release治理 |
| **当前阶段** | Phase 1 - INVENTORY（盘点阶段，禁止修改代码） |
| **创建时间** | 2026-08-31 |

## 最高级施工规则

【UNIFIED PRODUCTION RULE】
本项目当前目标不是继续无限升级，而是：
1. 整理现有系统
2. 降低重复代码和重复依赖
3. 明确三个系统边界
4. 建立统一运行与验证环境
5. 保留当前生产能力
6. 最小化修改
7. 完成真实运行验证
8. 达到交付标准后立即上线

**禁止：**
- 重写现有系统
- 无依据替换技术栈
- 大规模迁移
- 直接删除旧代码
- 用新包覆盖旧包
- 因架构优化阻塞ZBC上线
- 把实验代码直接进入生产

**任何删除/替换必须先完成：**
引用分析 → 运行依赖分析 → 替代验证 → 回归测试 → Evidence

## 三个系统定位

| 系统 | 定位 | 职责 | 边界 |
|------|------|------|------|
| **SICI** | Research | 研究、学习、案例、技术候选、知识数据库 | 不直接修改ZBC |
| **DCC** | Governance | 审计、验证、变更地图、Release Gate、Evidence | 不承担ZBC业务功能 |
| **ZBC** | Production | 真实业务、数据、客户、生产、交付 | 当前优先上线 |

## 技术栈最终判断

| 技术 | 决策 | 理由 |
|------|------|------|
| **Docker/Compose** | ✅ 采用 | 解决可重复运行和Staging隔离，成熟Flask项目已有完整实践 |
| **Playwright** | ✅ 提高为主要 | 官方支持CI/Docker，统一浏览器测试/自动化基础设施 |
| **Selenium** | ⚠️ 保留Adapter | 先保留，逐步判断能否退出，回归后再删除 |
| **Flask** | ⏸️ 暂不换 | 成熟生产组合，迁移风险大于收益 |
| **SQLite** | ⏸️ 暂不换 | 当前目标是稳定交付，高并发时再评估PostgreSQL |
| **前端框架** | ⏸️ 暂不换 | 先解决CSS/JS层级污染，复杂SPA再单独立项 |
| **AI** | 🔄 Provider化 | 不绑定豆包，业务层只调用analyze/summarize/classify |
| **采集** | 🔄 Adapter化 | 不把小红书逻辑写进Core，Core只认识CollectedItem |

## Phase 1 盘点任务清单

### 1.1 ARCHITECTURE-MAP（架构地图）
- [ ] 全部文件清单（按目录分类）
- [ ] 模块分层结构（core/domain/collectors/services/web/jobs/tests/docs）
- [ ] 模块依赖关系图
- [ ] 入口点清单（app.py / run_supervised.py / 启动脚本）

### 1.2 DEPENDENCY-MATRIX（依赖矩阵）
- [ ] requirements.txt 全量清单
- [ ] 每个包的实际import扫描（used_by）
- [ ] 分类：CORE / OPTIONAL / BROWSER / TEST / LEGACY / DUPLICATE / UNUSED
- [ ] 版本冲突分析
- [ ] 移除候选清单（selenium/httpx/xlsxwriter/colorama/tqdm）

### 1.3 MODULE-MATRIX（模块矩阵）
- [ ] 所有Python模块分类：ACTIVE / STABLE / LEGACY / DEPRECATED / EXPERIMENTAL / DUPLICATE / UNUSED
- [ ] 死代码识别（app_refactor_blueprint.py 16路由零注册）
- [ ] 重复实现识别

### 1.4 ROUTE-MATRIX（路由矩阵）
- [ ] 全部Flask路由清单
- [ ] API端点清单（/api/v1/）
- [ ] 页面路由清单
- [ ] 路由分组（monitoring/risk/events/knowledge/reports/system）
- [ ] 未注册路由识别

### 1.5 DATABASE-MATRIX（数据库矩阵）
- [ ] SQLite数据库文件清单
- [ ] 全部表结构清单
- [ ] 迁移历史
- [ ] 索引清单
- [ ] 数据量统计

### 1.6 UI-MATRIX（UI矩阵）
- [ ] CSS文件清单（26个业务CSS）
- [ ] JS文件清单（238个业务JS）
- [ ] HTML模板清单（56个）
- [ ] CSS层级污染分析（加载顺序、覆盖关系）
- [ ] 重复样式识别
- [ ] 响应式断点分析
- [ ] 设计令牌统一分析

### 1.7 CLEANUP-MATRIX（清理矩阵）
- [ ] 重复实现清单
- [ ] 无用代码清单
- [ ] 死代码清单
- [ ] 临时文件清单
- [ ] 备份文件清单（app.py.bak-*）
- [ ] 归档建议

### 1.8 敏感文件泄露审计
- [ ] .env 文件检查
- [ ] *.db 文件检查
- [ ] 明文 cookie/token 检查
- [ ] browser profile 检查
- [ ] .gitignore 覆盖验证

## Phase 2-13 后续计划（待Phase 1完成后启动）

- **Phase 2**: 建立ZBC-STAGING-RUNTIME（独立端口8301 + 独立DB + XHS_PRODUCTION=false）
- **Phase 3**: 原样运行当前ZBC，全量测试生成Evidence
- **Phase 4**: 问题分类（PASS/FAIL/ENV/GAP/REGRESSION）
- **Phase 5**: 技术栈替代可能性分析
- **Phase 6**: 统一分层（ZBC=Production / DCC=Governance / SICI=Research）
- **Phase 7**: 代码治理（分类+删除流程）
- **Phase 8**: 统一Provider/Adapter（Collector / AI / Browser）
- **Phase 9**: 统一测试体系（10级）
- **Phase 10**: 统一Evidence数据库
- **Phase 11**: 固定施工格式
- **Phase 12**: ZBC Release Gate（达到条件立即上线）
- **Phase 13**: 上线后持续进化

## 施工记录

| 时间 | 阶段 | 动作 | 结果 | Commit |
|------|------|------|------|--------|
| 2026-08-31 | Phase 1 | 建立施工台账 | ✅ 完成 | - |
| 2026-08-31 | Phase 1 | 精确扫描业务文件 | ✅ 完成（Python 400 / JS 238 / CSS 26 / HTML 56） | - |
| 2026-08-31 | Phase 1 | 研究GPT/Codex参考截图 | ✅ 完成（3张截图分析） | - |

## 不碰清单（全程禁止修改）

- [ ] 运行中的 8200/8201 生产实例
- [ ] 数据库文件和数据
- [ ] 采集任务和调度器
- [ ] DCC / SICI 仓库
- [ ] 计划任务配置
- [ ] 生产配置文件
- [ ] 浏览器 profile（9222 CDP）

## 回滚方案

- Phase 1 纯文档新增，无业务代码改动，删除文档即恢复
- 后续阶段每个Commit独立，可 `git revert <sha>` 回滚
- Staging环境完全隔离，不影响生产
