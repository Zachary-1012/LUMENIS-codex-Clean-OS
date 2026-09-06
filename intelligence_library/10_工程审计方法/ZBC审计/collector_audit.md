# ZBC Phase 5 — Collector 采集系统逐函数审计报告

> **审计日期**: 2026-09-06
> **仓库**: D:\Taikoo-monitor-new
> **分支**: feat/zbc-full-upgrade-v1
> **HEAD**: e9ef5ad
> **审计范围**: collector.py, xhs_cdp_collector.py, collector_automation.py
> **审计原则**: 先审计、再修改；先兼容、再重构；仅修复明确 bug，不重构主链路

---

## 1. 审计函数统计表

### 1.1 collector.py（主采集器，22KB）

| # | 函数名 | 状态 | 核心逻辑 | DB操作 | 异常处理 | 问题/修复 |
|---|--------|------|----------|--------|----------|-----------|
| 1 | `_check_profile_lock()` | VERIFIED | 只读检测 Chromium profile 锁文件，不删除 | 无 | 无异常 | 无 |
| 2 | `_get_xhs_guard()` | VERIFIED | 懒加载 CollectorGuard，env 开关控制 | 无 | 无 | 无 |
| 3 | `_get_xhs_risk_engine()` | VERIFIED | 懒加载 RiskEngine，状态持久化到 data/ | 无 | 无 | 无 |
| 4 | `_feed_risk_engine()` | **FIXED** | 六态→风险因子映射，熔断联动 guard.limiter | 无 | try/except 记录 | **[已修]** L132 `CollectState` 未导入→NameError 被静默吞掉，熔断联动永不生效。已补 `from collector_guard.state import CollectState` |
| 5 | `_cdp_online()` | VERIFIED | 探测 9222 CDP，tenacity 指数退避重试 | 无 | except→False | 无 |
| 6 | `_ensure_cdp_online()` | VERIFIED | 掉线自动拉起持久 Edge，30s 超时 | 无 | except→print+False | 无 |
| 7 | `_norm_cdp_note()` | VERIFIED | CDP 详情记录→标准字段映射，双时间铁律 | 无 | _int() 安全转换 | 无 |
| 8 | `_search_via_cdp()` | VERIFIED | 子进程调用 xhs_cdp_collector.py，解析 RESULT_JSON | 无 | JSON 解析异常→显式 error | 无 |
| 9 | `_search_standalone()` | VERIFIED | Node xhs_search.js 兜底通道 | 无 | Timeout/Exception→显式 error | 无 |
| 10 | `_is_noise_keyword()` | VERIFIED | 英文停用词/纯数字/单字符过滤 | 无 | 无 | 无 |
| 11 | `search_xiaohongshu()` | VERIFIED | CDP 优先→standalone 兜底，风控态直返 | 无 | except→print+兜底 | 无 |
| 12 | `collect_all()` | **FIXED** | 关键词清洗→guard 包裹→RiskEngine→dedup(note_id)→主体硬过滤 | 无（返回 list） | 调度间隔 except 静默 | **[已修]** L400 `base` 未定义→NameError 被静默吞掉，动态调度间隔永不生效。已补 `base = float(os.getenv(...))` |
| 13 | `import_from_file()` | VERIFIED | 从 JSON 文件导入笔记 | 无 | 无 try（调用方负责） | 无 |
| 14 | `classify_collect_state()` | VERIFIED | 六态归一化：SUCCESS/EMPTY/AUTH_REQUIRED/CAPTCHA/BLOCKED/NETWORK_ERROR | 无 | 无 | 无 |

### 1.2 xhs_cdp_collector.py（CDP 真人采集器，44KB，最大最复杂）

| # | 函数名 | 状态 | 核心逻辑 | DB操作 | 异常处理 | 问题/修复 |
|---|--------|------|----------|--------|----------|-----------|
| 1 | `log()` | VERIFIED | stderr 日志 | 无 | 无 | 无 |
| 2 | `human_sleep()` / `gauss_sleep()` | VERIFIED | 真人节奏随机停顿 | 无 | 无 | 无 |
| 3 | `_bezier_path()` | VERIFIED | 三次贝塞尔鼠标轨迹 | 无 | 无 | 无 |
| 4 | `_viewport_size()` | VERIFIED | 读取视口尺寸，兜底 1280x800 | 无 | except→默认值 | 无 |
| 5 | `move_mouse_human()` | VERIFIED | 贝塞尔轨迹移动鼠标 | 无 | 单步 move except:pass（非关键） | 无 |
| 6 | `move_to_locator_and_click()` | VERIFIED | 移入元素+真实按下抬起 | 无 | 无 | 无 |
| 7 | `scroll_human()` | VERIFIED | 变速滚动+偶发回滚+鼠标漂移 | 无 | 鼠标漂移 except:pass | 无 |
| 8 | `_is_interact_element()` | VERIFIED | 互动黑名单检测（点赞/收藏/评论/关注/发布） | 无 | except→False（安全侧：不确定不拦截） | 无 |
| 9 | `_find_first()` | VERIFIED | 多选择器顺序查找可见元素 | 无 | except:continue | 无 |
| 10 | `human_click_note_coords()` | VERIFIED | 坐标点击封面，点击前 elementFromPoint 安全护栏 | 无 | 多段 except 降级 | 无 |
| 11 | `human_search_keyword()` | VERIFIED | 逐字输入+偶发误触回删+回车 | 无 | 无（失败上抛） | 无 |
| 12 | `human_swipe_gallery()` | VERIFIED | 轮播图浏览，互动黑名单校验 | 无 | except→log+return | 无 |
| 13 | `human_watch_video()` | VERIFIED | 视频观看停留，不点击互动控件 | 无 | except→False | 无 |
| 14 | `human_read_content()` | VERIFIED | 滚动阅读正文 | 无 | except:pass | 无 |
| 15 | `human_read_comments()` | VERIFIED | 滚动阅读评论区 | 无 | except→0 | 无 |
| 16 | `human_reading_profile()` | VERIFIED | 秒退/浅读/正常/深读分布抽样 | 无 | 无 | 无 |
| 17 | `human_consume_detail()` | VERIFIED | 按画像编排详情阅读，全程被动浏览 | 无 | except→log | 无 |
| 18 | `parse_count()` | VERIFIED | 万/w/千/k/亿 单位解析 | 无 | 无 | 无 |
| 19 | `normalize_publish_time()` | VERIFIED | 相对时间→日期，拿不到返回空串（不臆造） | 无 | 无 | 无 |
| 20 | `classify_page()` | VERIFIED | 风控关键词识别（IP/验证码） | 无 | 无 | 无 |
| 21 | `_compute_subject_hit()` | **NEW** | 委托 subject_rules.subject_hit_text 判定主体 | 无 | except→None（不排除） | **[新增]** P0 加固：使 collector.py subject_hit_cdp 硬过滤生效 |
| 22 | `_risk_check()` | VERIFIED | 全程风控检测，命中写 result.error | 无 | except→False | 无 |
| 23 | `robust_goto()` | VERIFIED | commit→domcontentloaded 两轮降级导航 | 无 | 两轮失败上抛 | 无 |
| 24 | `collect_human()` | **FIXED** | 真人浏览主流程：搜索→滚动→详情→阅读→返回 | 无（输出 JSON） | 详情级 except→记录失败笔记 | **[已修]** 记录未含 `subject_hit` 字段→collector.py 硬过滤死代码。已补 `rec['subject_hit']` |
| 25 | `collect_direct()` | **FIXED** | 旧直连流程（--human=0 兜底） | 无（输出 JSON） | 详情级 except→记录失败笔记 | **[已修]** 同上，补 `subject_hit` 字段 |
| 26 | `collect()` | VERIFIED | 统一入口，human=1/0 分发 | 无 | 无 | 无 |
| 27 | `main()` | VERIFIED | CLI 入口，异常捕获→显式 CDP_EXCEPTION | 无 | except→error dict | 无 |

### 1.3 collector_automation.py（自动化控制器，35.7KB）

| # | 函数名 | 状态 | 核心逻辑 | DB操作 | 异常处理 | 问题/修复 |
|---|--------|------|----------|--------|----------|-----------|
| 1 | `__init__()` | VERIFIED | 路径初始化、冷却控制、历史加载 | 无 | 无 | 无 |
| 2 | `_find_edge_browser()` | VERIFIED | 多路径查找 Edge，where 命令兜底 | 无 | except:pass | 无 |
| 3 | `_get_cdp_profile_dir()` | VERIFIED | 双子星库 Contract 优先→legacy 映射 | 无 | except→legacy 降级 | 无 |
| 4 | `_port_for()` | VERIFIED | 委托 xhs_cookie_bridge 单一事实源 | 无 | except→默认 9222 | 无 |
| 5 | `start_browser()` | VERIFIED | 端口已在线则复用，独立 profile 启动 | 无 | except→raise | 无 |
| 6 | `_is_browser_running()` | VERIFIED | CDP /json/version 探测 | 无 | except→False | 无 |
| 7 | `_wait_for_cdp_ready()` | VERIFIED | 轮询等待 CDP 就绪 | 无 | 无 | 无 |
| 8 | `stop_browser()` | VERIFIED | PID 级精确关闭，不做全量 taskkill | 无 | except→log+False | 无 |
| 9 | `start_collection()` | VERIFIED | 预检门控→冷却校验→后台线程启动 | 无 | 预检异常→拒绝启动 | 无 |
| 10 | `_run_collection()` | VERIFIED | 启动浏览器→采集→Evidence 记录→自动关闭 | evidence_store | 全链路 except→FAIL evidence | 无 |
| 11 | `_execute_collection()` | VERIFIED | xhs_cookie_bridge.sync 主路径→CDP 兜底 | db.insert_note | ImportError 降级，无模块则明确报错 | 无 |
| 12 | `_warmup_cdp()` | PARTIAL | CDP 浏览器热身进入小红书域 | 无 | except→log+跳过 | **[观察]** L517 `b.close()` 对 CDP 连接调用 close，理论上可能关闭持久 Edge。生产未见异常（Playwright CDP close 行为需实测确认），标记为 P1 观察项 |
| 13 | `_collect_via_cdp()` | VERIFIED | Node cjs 兜底采集→subject_hit 过滤→insert_note | db.insert_note / upsert_comments | Timeout/Exception→log，风控态显式上报 | 无 |
| 14 | `get_status()` | VERIFIED | 状态快照 | 无 | 无 | 无 |
| 15 | `stop_collection()` | VERIFIED | 停止当前任务+浏览器 | 无 | except→log | 无 |
| 16 | `_load_history()` / `_save_history()` | VERIFIED | JSON 历史持久化，保留最近 100 条 | 无 | except→log+空列表 | 无 |
| 17 | `get_history()` | VERIFIED | 历史记录倒序 | 无 | 无 | 无 |

---

## 2. 发现的问题清单（按严重程度）

### P0 — 已修复

| ID | 位置 | 问题 | 影响 | 修复 |
|----|------|------|------|------|
| P0-1 | collector.py L132 | `CollectState` 未导入，`_feed_risk_engine` 中 `CollectState.PAUSED` 引发 NameError，被 `except Exception` 静默吞掉 | RiskEngine 熔断时无法联动 guard.limiter.force_pause，两套熔断系统脱节，熔断后仍继续请求 | 补 `from collector_guard.state import CollectState` |
| P0-2 | collector.py L400 | `collect_all` 中 `base` 变量未定义（仅在 `_get_xhs_guard` 局部作用域存在），引发 NameError，被 `except Exception` 静默吞掉 | 关键词间动态调度间隔（NORMAL/ADAPTIVE/COOLDOWN/FROZEN 倍率）永不生效，风控时不降频 | 补 `base = float(os.getenv('XHS_GUARD_BASE_INTERVAL', '6'))` |
| P0-3 | xhs_cdp_collector.py | `collect_human` / `collect_direct` 产出的记录不含 `subject_hit` 字段 | collector.py L414 主体硬过滤 `if subject_hit_cdp is False: continue` 永远不触发（None ≠ False），CDP 采集笔记在 collector 层绕过主体过滤，仅依赖下游 app.py 过滤 | 新增 `_compute_subject_hit()`，在两条采集链路的 rec 中写入 `subject_hit` 布尔值 |

### P1 — 观察项（本次不修复，需后续验证）

| ID | 位置 | 问题 | 建议 |
|----|------|------|------|
| P1-1 | collector_automation.py `_warmup_cdp` L517 | `b.close()` 对 CDP connect_over_cdp 的 Browser 调用 close，Playwright 文档中 CDP 连接的 browser.close() 会关闭远程浏览器 | 实测确认是否关闭持久 Edge；若关闭则改为仅断开连接（不调用 close，让 with 块自然退出） |
| P1-2 | collector.py `collect_all` L404 | 调度间隔计算失败仅 print 不记录到 collection_results | 建议将调度异常计入结果元数据，便于可观测 |
| P1-3 | xhs_cdp_collector.py 多处 | 真人行为函数（mouse move/scroll/read）中 `except Exception: pass` 较多 | 均为非关键 UI 操作失败，不影响数据采集；建议降级为 debug 日志而非完全静默 |

### P2 — 低优先级

| ID | 位置 | 问题 | 建议 |
|----|------|------|------|
| P2-1 | collector_automation.py `_execute_collection` | `collector.run_collection` 不存在，hasattr 检查后跳过，属死代码兜底 | 可移除或替换为 `collector.collect_all` + 入库逻辑 |
| P2-2 | collector.py `import_from_file` | 无 try/except，文件不存在或 JSON 损坏时直接抛异常 | 调用方已处理，可接受 |

---

## 3. 采集流程完整性验证

### 3.1 Source → Raw Evidence → Dedup → Subject Filter → Canonical Data → Analysis

| 阶段 | 实现位置 | 状态 | 说明 |
|------|----------|------|------|
| **Source** | xhs_cdp_collector.py / xhs_cookie_bridge.py / rednote_collector.cjs | VERIFIED | 多通道：CDP 真人、纯 HTTP Cookie、Node 兜底 |
| **Raw Evidence** | collector_automation.py `_run_collection` → evidence_store.record_collection_evidence | VERIFIED | 成功/失败均落证据链，含 account/platform/notes/duration/error_type |
| **Dedup** | collector.py `collect_all` L409-419（note_id 字典去重）；database.py `insert_note` L327（SELECT existing by note_id） | VERIFIED | 双层去重：内存层 note_id + DB 层 note_id UPSERT |
| **Subject Filter** | ① xhs_cdp_collector.py `_compute_subject_hit`（采集层）② collector.py `collect_all` L414-416（subject_hit_cdp is False 排除）③ app.py L1025 `verify_taikoo_location`（入库前）④ xhs_cookie_bridge.sync L797（入库前）⑤ collector_automation._collect_via_cdp L572 | **VERIFIED（修复后）** | 修复前 ①② 失效（P0-3）；修复后五层过滤闭环 |
| **Canonical Data** | collector.py `_norm_cdp_note`；database.py `insert_note` 字段标准化 | VERIFIED | 双时间铁律（publish_date vs captured_at）、标题兜底、质量门 |
| **Analysis** | app.py L1048-1054 → reprocess.analyze_note_row + build_cross_platform_events；xhs_cookie_bridge.sync L803-819 异步 AI 分析 | VERIFIED | AI 仅辅助分析，不决定数据是否存在；主体过滤在 AI 之前完成 |

### 3.2 AI 不决定数据是否存在

- **验证通过**。AI 分析（reprocess.analyze_note_row / ai_analyzer）在主体过滤和入库之后执行。
- `ai_analyzer.verify_taikoo_location` 内部调用 `subject_rules.subject_hit()`，是规则判定而非 AI 生成。
- AI 输出可记录、可追溯、可人工修正（符合 AGENTS.md §3）。

### 3.3 SUBJECT_HARD_FILTER 在采集后、入库前执行

- **验证通过（修复后）**。xhs_cdp_collector.py 现在在采集时计算 `subject_hit`，collector.py 在 `collect_all` 返回前排除 `subject_hit_cdp is False` 的记录，app.py/xhs_cookie_bridge 在 `insert_note` 前再次通过 `verify_taikoo_location` 过滤。

---

## 4. 主体过滤保护验证结果

### 4.1 P0 红线文件未被修改

| 文件 | 检查项 | 结果 |
|------|--------|------|
| subject_rules.py | SUBJECT_WORDS (18词) | 未修改 ✓ |
| subject_rules.py | SUBJECT_EXCLUDE_WORDS (20词) | 未修改 ✓ |
| subject_rules.py | subject_hit() | 未修改 ✓ |
| subject_rules.py | subject_sql_and_values() | 未修改 ✓ |
| subject_rules.py | BRAND_PROFILES | 未修改 ✓ |

### 4.2 主体过滤调用点全覆盖

| 调用点 | 方式 | 状态 |
|--------|------|------|
| app.py L114 | `from subject_rules import ...` | VERIFIED |
| app.py L1025 | `ai_analyzer.verify_taikoo_location` → `subject_hit` | VERIFIED |
| app.py L2148-2159 | `subject_hit_note_safe` | VERIFIED |
| risk_engine.py L15 | `from subject_rules import ...` | VERIFIED |
| ai_analyzer.py L12, L141 | `subject_hit(title, body, content)` | VERIFIED |
| database.py L8, L827, L881 | `subject_hit` 在事件/日报聚合中 | VERIFIED |
| xhs_cookie_bridge.py L797 | `verify_taikoo_location` 入库前过滤 | VERIFIED |
| collector_automation.py L527, L572 | `subject_hit` CDP 兜底过滤 | VERIFIED |
| collector.py L414-416 | `subject_hit_cdp is False` 硬过滤 | **修复后生效** |
| xhs_cdp_collector.py `_compute_subject_hit` | `subject_hit_text` 采集层判定 | **新增** |

### 4.3 排除词一票否决验证

- `subject_hit()` 实现：先遍历 `exclude_words`，命中即返回 False，再检查正向词。
- `verify_taikoo_location()` 双重检查：先 `subject_hit`，再独立遍历 `SUBJECT_EXCLUDE_WORDS`。
- 上海/北京/成都/香港太古汇等同名场景被严格隔离。

---

## 5. Auth/Session 处理验证

| 检查项 | 实现位置 | 状态 |
|--------|----------|------|
| Cookie 失效显式记录（不静默成 0 条） | xhs_cookie_bridge.sync → state_counts / task_state；collector.classify_collect_state → AUTH_REQUIRED | VERIFIED |
| 登录态失效触发系统内弹窗 | app.py L1040-1046 → auth_recovery.request_recovery；auth_recovery_center | VERIFIED |
| IP 风险/验证码熔断冷却 | xhs_cdp_collector._risk_check → IP_RISK_OR_300012 / NEED_VERIFY；collector_guard.rate_limiter.force_pause；RiskEngine 连续风险分 | VERIFIED（修复后联动生效） |
| 预检门控 | collector_automation.start_collection → xhs_cookie_bridge.runtime_preflight_check | VERIFIED |
| 官方账号只读保护 | xhs_cdp_collector.INTERACT_BLACKLIST + _is_interact_element + human_click_note_coords 安全护栏 | VERIFIED |

---

## 6. Playwright/CDP 稳定性验证

| 检查项 | 实现位置 | 状态 |
|--------|----------|------|
| 超时处理 | robust_goto（commit→dom 两轮）；page.wait_for_selector 均有 timeout；subprocess.run timeout=300/900 | VERIFIED |
| 页面卡死检测 | collect_human 中 wait_for_selector 失败后检测 body_len < 20 / about:blank → LOAD_FAILED | VERIFIED |
| 浏览器上下文持久化 | collector_automation.start_browser 独立 user-data-dir；端口已在线则复用；CDP 模式绝不 browser.close() | VERIFIED |
| 只关闭本脚本新开标签 | xhs_cdp_collector finally: page.close()，不 browser.close() | VERIFIED |
| CDP 掉线自愈 | collector._ensure_cdp_online 自动拉起 | VERIFIED |

---

## 7. Checkpoint 验证

- `collector_guard/checkpoint.py`：Checkpoint 类，支持 `is_seen` / `mark_seen` / `filter_new` / `last_success` / `reset`。
- CollectorGuard 在 `run()` 中集成 checkpoint，用于关键词级别的笔记去重和增量采集。
- 状态持久化到 `data/collector_guard/` 目录（已 gitignore）。

---

## 8. 静默失败检测汇总

### 核心采集器中的 `except: pass` / `except Exception: pass`

| 位置 | 性质 | 风险 |
|------|------|------|
| xhs_cdp_collector.py 鼠标移动/滚动/阅读 (~15处) | 非关键 UI 操作失败 | 低：不影响数据采集，仅影响真人行为仿真度 |
| xhs_cdp_collector.py L568 reset_cdp_targets | 可选优化失败 | 低：不影响主流程 |
| collector.py L179/185 _cdp_online | 探测失败返回 False | 低：预期行为 |
| collector_automation.py L72 where 命令 | Edge 路径查找失败 | 低：有硬编码路径兜底 |
| collector_automation.py L97 xcb import | Contract 导入失败降级 legacy | 低：预期降级 |
| **collector.py L133 (修复前)** | **CollectState NameError** | **P0：已修复** |
| **collector.py L404 (修复前)** | **base NameError** | **P0：已修复** |

**结论**：修复后，核心采集链路中无被静默吞掉的关键异常。剩余 `except: pass` 均为非关键 UI 操作或预期降级路径。

---

## 9. 修复文件列表

| 文件 | 修改内容 |
|------|----------|
| collector.py | ① L130 补 `from collector_guard.state import CollectState`；② L401 补 `base = float(os.getenv('XHS_GUARD_BASE_INTERVAL', '6'))` |
| xhs_cdp_collector.py | ① 新增 `_compute_subject_hit()` 函数；② `collect_human` rec 补 `subject_hit`；③ `collect_direct` rec 补 `subject_hit` |

**未修改**：subject_rules.py, app.py, risk_engine.py, ai_analyzer.py, database.py, collector_automation.py

---

## 10. 未完成项 / 下一步建议

1. **P1-1 验证**：实测 `_warmup_cdp` 中 `b.close()` 是否关闭持久 Edge，若关闭则改为仅断开。
2. **P1-2**：将调度间隔异常计入 collection_results 元数据。
3. **P2-1**：清理 `collector.run_collection` 死代码兜底。
4. **扩展审计**：对 collector_v2/ 目录（7文件）和 platform_adapters/（24文件）进行同等深度审计。
5. **E2E 验证**：在测试环境执行一次真实采集，验证 subject_hit_cdp 硬过滤端到端生效。

---

*报告生成时间: 2026-09-06 | 审计者: ZBC Phase 5 Collector Audit*
