# P0 对账施工记录（2026-09-02）

> 由 OSAI 研究侧按用户指令「推送到双子库 + 自己施工 + 检查最新仓库说明」执行。
> 本记录归档于 Z-Brand-Core（双子星生产侧），供审计追溯。

## 一、施工前核验（最新仓库说明）

读取 Z-Brand-Core 最新：AGENTS.md（V2.0 协作宪法）/ CURRENT_BASELINE.md / CHANGELOG.md（5.9.9-t0/t1/t2）/ 迭代工单与时间评估.md。
确认 GitHub main 最新 HEAD=d4df89d（含 v5.9.9-t2 小红书 P0 编排层），对账基线（本地 545a3ab）落后于最新代码，施工前以最新代码重核各 P0 项。

## 二、P0 缺口最新核验结果

| GAP | 对账基线结论 | 最新代码核验 | 处置 |
|---|---|---|---|
| P0-01 aggregate_events() 消失 | MISSING | 仍无 def；事件聚合由 daily_report/weekly_events/event_graph 重构替代 | 记录替代映射，不盲目恢复 |
| P0-02 subject_hit 三处冲突 | 3 副本 | 权威 subject_rules.py:38 + app.py:2743(AI替代) + collector_v2/run_live_engine.py:16(AI替代+恒False兜底) | 已统一 |
| P0-04 requirements 缺 waitress | 缺 | 仍缺 waitress（bs4/lxml 已被 t0 补全） | 已补 |
| P0-05 版本号五处不一致 | 5 处 | VERSION/app.py=5.9.9, package.json=5.6.2, base.html=5.8.9 | 已统一 |

## 三、已施工并推送（GitHub 可验证）

### P0-02 subject_hit 统一权威口径
- **collector_v2/run_live_engine.py**（commit 02b1fcd）：`from ai_analyzer import verify_taikoo_location` → `from subject_rules import subject_hit_text`，消除采集链路 AI 替代口径分叉。
- **app.py:2743**（本地 commit 8834d1a，待沙箱恢复后 push）：同样委托 subject_rules.subject_hit_text。
- 分层确认：database.py insert_note/get_events 已用 subject_rules.subject_hit（5 字段权威）兜底入库与展示层；AI verify 仅保留采集时增强标记（合规）。

### P0-04 requirements 补 waitress（commit fec36be）
- requirements.txt 新增 `waitress>=2.1.0`（run_production.py 生产 WSGI 依赖）。

### P0-05 版本号统一 v5.9.9
- **package.json**（commit a4ea9a8）：5.6.2 → 5.9.9。
- **templates/base.html**（commit 73fe04c）：v5.8.9 → v5.9.9（页头/页脚/11 处静态缓存戳）。
- VERSION / app.py 已为 5.9.9，全仓一致。

## 四、验证结果
- py_compile：app.py / subject_rules.py / run_live_engine.py 全部通过。
- subject_hit_text 功能测试 6/6 PASS（广州太古汇/上海太古汇/太古汇保安/成都远洋太古汇/天河路383号/北京三里屯太古汇）。
- package.json JSON 合法性校验通过。

## 五、待用户决策/后续项

### P0-03（高危）OSAI archive 含 ZBC 生产代码副本 + 真实密钥
- 路径：OSAI 本地 `archive/desktop-legacy/taikoo-monitor-clean/`（1643 文件，含完整 ZBC 生产代码副本）。
- `.env` 含 **19 个非空值**（DASHSCOPE_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY / TAIKOO_AUTH_PASSWORD 等真实密钥）。
- 未推送 GitHub（.gitignore 已含 .env，git tracked=0），风险仅限本地残留。
- **建议**：用户授权后删除/隔离该目录并轮换相关密钥。

### P0-01 aggregate_events 替代映射
- 现代等价物：daily_report.generate_daily_digest / weekly_events.weekly_payload / event_graph 系列。
- 建议在架构文档中正式声明该函数名已由模块化聚合替代，避免未来误以为缺失。

## 六、双子星边界声明
- 本次施工为用户显式授权（「你要自己施工」），仅触及主体口径收敛、依赖补全、版本统一三类低风险项；未触碰 SUBJECT_WORDS/SUBJECT_EXCLUDE_WORDS/subject_hit 权威定义、未改生产数据、未碰 Cookie/Token。
- OSAI 研究侧职责保持不变：研究/学习/判断/形成 Contract；本次为用户授权的施工例外。
