# OSAI 第十四期 · 情感共鸣×主题适配 + OSAI 自主执行闭环 v1

日期：2026-09-03
定位：双子库统一工程基线（UNIFIED-ENGINEERING-BASELINE-2026.09）下，情感共鸣机制深化 + 研发中枢自主闭环第一版真实落地。

---

## 一、本轮做了什么

### 1. 手法×主题词适配约束（引擎反模板化第二层）
- 新增 `_EMO_ROLE_COMPAT`：7 类语义角色（space/food/service/event/ip/aesthetic/general）→ 情感手法白名单。
- 核心规则：**功能性/低语境主题词（service：停车/投诉/积分）收敛到写实手法**（朴素真话/轻描淡写/时间具象），
  禁止高语境手法（越界张力/魔幻现实/交错配列/反问推理）在停车、排队这类场景"出戏"。
- 高语境角色（ip/aesthetic）放开手法面，保留冲击力。
- `_pick_hook` 增加 role 参数，按 `_EMO_ROLE_COMPAT` 过滤候选手法；`generate_ideas` 传 `_topic_role(topic)`。
- 现网验证：主题=停车/积分 时情感共鸣自动落到"首语重复"写实手法——"好的积分，慢一点；好的体面省心的体验，等一会；好的广州太古汇，不急"。

### 2. 文学/戏剧句库扩充（8 组新手法）
- `emo_query` 反问推理（莎士比亚 rhetorical question）
- `emo_repeat` 首语重复 + 无连词排比（anaphora + asyndeton）
- `emo_mirror` 交错配列（chiasmus）
- `emo_slant` 留白斜说（狄金森 "Tell all the truth but tell it slant" + 俳句切字/留白）
- `emo_season` 季语物候（俳句 kigo：季节意象承载情绪）
- `emo_surreal` 魔幻现实（马尔克斯式）
- `emo_understate` 轻描淡写（understatement）
- `_HOOK_EMO_LUX` 同步 8 组高奢版；MECH_TO_HOOK resonate 扩至 14 手法。

### 3. 情感共鸣跨产物接入
- 新增 `idea_generator.emotion_hook(brand, topic, circle, tonality, rng)` 公开函数。
- `video_script.generate_video_script` 返回新增 `emotion_hook`（视频情感钩子）。
- `social_ops.generate_social_matrix` 每个平台新增 `emotion_hook`。
- 现网验证：概念片钩子"四季会换，15周年限时会变——广州太古汇的一年一次的事，一年只等一次"；小红书"谁规定广州太古汇必须是这样？"。

### 4. OSAI 自主执行闭环 v1（研发中枢独立第一步）
- 新建 `osai_engine/`（OSAI 仓库）：config / llm / tools / research / evidence / agent / orchestrator。
- **llm.py**：OSAI 独立智谱调用（不依赖 ZBC 代码，读 ZBC .env 的 ZHIPU_API_KEY）。
- **tools.py**：确定性工具层（git status/commit/push、pytest 全量、读写文件）。
- **research.py**：三源研究接入（learning-feed 知识库检索 + inbox 消化 + 智谱深化；联网检索标记为下一期）。
- **agent.py**：智谱决策 loop（JSON 协议 action=git_commit_push/run_pytest/research/write_evidence/skip）+ 失败自愈。
- **orchestrator.py**：`run_one_round(task)` 完整回合 = 研究→决策→执行→验证→Evidence。
- **evidence.py**：每次闭环写入 `evidence/agent-rounds.md`（时间/任务/阶段/结果/git SHA/智谱调用数）。
- 已真实跑通一个回合：研究(3条知识)→智谱决策(write_evidence)→落盘→Evidence，结果 ok。
- 7 项自测（tests/test_osai_engine.py，可离线跑）。

---

## 二、智谱 glm-4.7 踩坑（复用 SOP，重要）
1. **glm-4.7 是思考模型**：max_tokens 过小时 content 会被 reasoning_content 占满返回空。
2. **快速稳定输出**：加 `"thinking": {"type": "disabled"}` 关闭思考，决策类调用必须关（否则 300s 读超时）。
3. **深度推理**：需要第二意见/复杂拆解时传 thinking=True。
4. **JSON 输出嵌套**：模型可能把整个动作对象塞进 `decision` 字段，解析须归一化（内层 dict 提升顶层）。
5. 超时用 requests（socket 空窗比 urllib 稳健），timeout 300s。

---

## 三、验收（真实证据）
- ZBC 全量回归：reg44 EXIT=0，无失败。
- 现网 8201 三端点验证：ideas（service 适配收敛）、video-script、social-ops（emotion_hook）全 True。
- OSAI osai_engine 7 项自测全绿；闭环回合 Evidence 落盘。
- 智谱本轮实际调用约 10 次（含调试重试），主力归智谱，豆包零推理调用。

---

## 四、下一轮候选（按优先级）
1. OSAI 自主联网研究接入（web 检索工具链，补"自主联网研究"这一大件）。
2. 闭环升级：决策→真实改代码→回归→推送 ZBC 的完整工程回合（当前已到"决策+Evidence+git"）。
3. 更多品类/圈层情感手法扩充（高奢/小众调性品牌句库）。
4. 创意引擎接 UI：输入圈层/热点即出创意卡（前端可视化）。
