# 序境 Intelligence · 落地评估记录（2026-09-04）

- 状态：EVAL-DONE · 关联：RESEARCH_2026-09-B.md 的 EVALUATE/RESEARCH 项
- 原则：不改现网配置、不破坏现有实现、登记可借鉴点，全部受 License/安全/成本/权限边界约束

## 一、GLM-5.3（智谱）升级评估
- 现状：`ZBC .env` `ZHIPU_STRONG_MODEL=glm-4.7`（强模型），`ZHIPU_MODEL=glm-4.5-air`（常规）；`AI_PROVIDER=zhipu`
- GLM-5.3（2026-09-03）：提升几乎全来自后训练；Terminal-Bench 3.0 4.6→28.3、DeepSWE v1.1 46.2→66.9、Agents' Last Exam 23.8→28.5，多项开源第一
- 序境相关任务映射：Agent 长程（Terminal-Bench）、软件工程（DeepSWE）、通用 Agent（Agents' Last Exam）——均为序境-Intelligence 与 AI Router 的核心场景
- 判定：**ADOPT（条件式）**——待智谱 API 确认 `glm-5.3` 模型名可用后，将 `ZHIPU_STRONG_MODEL` 升级为 `glm-5.3`，再跑序境 AI 任务抽样回归（Agent/代码分析/文案三档）
- 约束：不提前改配置（避免破坏现网 8201）；升级必须伴随回归（现有 AI 调用测试）；保持 `ZHIPU_MODEL=glm-4.5-air` 常规档不变（成本/速度）

## 二、Page Agent / browser-use 对照 internal_browser
- 现状：`internal_browser.py`（353 行）为 CDP 执行层封装：navigate / click_at / type_text / scroll_page / history_action / evaluate / capture_screenshot / list_accounts；**无 agent 规划层**
- Page Agent（阿里，MIT，20.2k★）/ browser-use：提供「规划-执行-恢复」回路——selector 失败时 agent 重规划而不是中止（browser-use QA 87% 40 步无人值守完成）
- 对照结论：序境 internal_browser 覆盖执行层；缺"失败→重规划"恢复回路
- 可借鉴点（登记 P2，不动现有执行层核心）：
  1. `click_at`/`type_text` 失败时增加"重新定位元素→重试→降级为坐标点击"的三级恢复
  2. 步骤执行记录 trace（action/selector/结果/耗时），供 Evidence 可追溯
  3. 长任务（>N 步）设步骤预算与超时，避免死循环（对齐序境"异常恢复有次数上限"）
- 边界：浏览器自动化仍受序境采集安全 Gate（不绕过验证码/限流/平台安全）；外部页面视为不可信输入

## 三、已落地（本轮 ZBC 生产）
- 创意引擎 `scripts/idea_generator.py`：新增「约束即创意」机制（戛纳233范式"创意生于限制"）——MECHANISMS/MECH_TO_L1/_HOOK/_HOOK_LUX/MECH_TO_HOOK/hook_names/mech_order 全链路接入，含高奢约束版（专注即奢侈/留白即分量）
- 测试 `tests/test_idea_generator.py`：+`test_constraint_mechanism_present_and_clean`（句库渲染+premium/LUX 轮转命中+无占位符），18 项全通过
- 真实产出示例：「做不到的，广州太古汇不假装」——15周年，诚实就是一年一次的事

## 四、下一步（待施工）
- GLM-5.3：智谱 API 确认后升级 `ZHIPU_STRONG_MODEL` + 三档抽样回归
- internal_browser：P2 恢复回路（失败重规划/步骤 trace/预算超时）
