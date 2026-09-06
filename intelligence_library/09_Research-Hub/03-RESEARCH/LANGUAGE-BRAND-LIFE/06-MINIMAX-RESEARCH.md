# 06 · MiniMax 研究（模型 / 视频 / 语音 / 开源策略）

> 知识库条目规范：`**[条目]** 证据等级 / 状态 / 语言文化 / 时间版本 / 来源`
> 研究日期：2026-09-04。本模块为序境-Intelligence 研究输入；**不改变现网模型选择（智谱主力）**，任何模型替换须经 Contract/Test/Evidence/Audit/Release。

## 1. 公司背景

**[MiniMax 公司]** E3 / VERIFIED / 中英 / 2026-09 / minimaxzh.com；AI Wiki；胡润/福布斯
- 上海稀宇科技，2021-12 成立，闫俊杰（前商汤科技副总裁）创立；高瓴创投领投，阿里/腾讯入局；2024 胡润全球独角兽榜（约 200 亿 RMB 估值），IDC 中国大模型领导者象限。
- 四大支柱：LLM（ABAB / MiniMax-01 / M 系列）、AI 视频（海螺 Hailuo）、陪伴/角色对话（Talkie、星野）、语音与音乐生成（Speech-02、Music-01）。

## 2. 语言 / 推理 / Agent 模型线

**[MiniMax-01 系列（开源）]** E3 / VERIFIED / 中英 / 2025-01-15 / arXiv:2501.08313；MiniMax 官方
- MiniMax-Text-01 + MiniMax-VL-01；456B 总参 / 45.9B 每 token 激活；MoE 32 专家。
- **核心创新：Lightning Attention（线性注意力）**——线性复杂度长上下文，混合架构（每 8 层 7 层 Lightning + 1 层 Softmax）。
- 上下文：训练 1M、推理外推至 **4M**（GPT-4o 的 32 倍、Claude-3.5-Sonnet 的 20 倍）；4M Needle-in-a-Haystack 接近全绿。
- 性能比肩 GPT-4o / Claude-3.5-Sonnet；超长上下文 RULER 保持 0.91–0.96。开源权重于 GitHub（MiniMax-AI）/ HuggingFace。

**[MiniMax-M1（开源推理模型）]** E3 / VERIFIED / 英 / 2025-06-17 / MiniMax-AI；arXiv:2506.13585；Apache-2.0
- 世界首个 open-weight 大规模混合注意力推理模型；1M 上下文（DeepSeek R1 的 8 倍）。
- 效率：100K 生成长度下仅需 DeepSeek R1 约 25–30% FLOPs；TAU-bench 工具使用超所有 open-weight 含 Gemini 2.5 Pro；SWE-bench Verified 56%（当时 open 模型最佳）。

**[MiniMax-M2（开源）]** E3 / VERIFIED / 中英 / 2025-10 / MiniMax 官方
- 230B/10B active，**MIT 许可证**；专为 Agent 和代码而生；约 Claude Sonnet 8% 价格、2 倍速度；Artificial Analysis 全球前五。IPO 后 M2 系列 token 消费 6 倍+、编码工作负载 10 倍+ 增长。

**[MiniMax-M2.5（开源）]** E3 / VERIFIED / 中英 / 2026-02-12 / MiniMax 官方
- 数十万真实环境大规模 RL 训练；SWE-Bench Verified 80.2%、Multi-SWE-Bench 51.3%、BrowseComp 76.3%；复杂 Agentic 任务比 M2.1 快 37%。

**[MiniMax-M2.7（专有）]** E3 / VERIFIED / 中英 / 2026-03-18 / MiniMax 官方
- "模型自我进化"——首个深度参与迭代自己的模型；自动化 RL 研究。
- **License 收紧信号**：改"Modified-MIT"，商用需书面授权——开源策略从 M2 的 MIT 明显收窄。

**[MiniMax-M3（最新，专有）]** E3 / VERIFIED / 中英 / 2026-05-31 / MiniMax 官方
- 全新 **MSA（MiniMax Sparse Attention）** 注意力架构；1M 上下文；原生多模态 Frontier Coding 模型。
- 配 MaxProof（生成式验证 RL 数学证明框架）：M3 在 IMO 2025 与 USAMO 2026 真题上超人类金牌线。

**[MiniMax Agent / Code]** E3 / VERIFIED / 中英 / 2025-06 → 2026-08 / MiniMax 官方
- MiniMax Agent（2025-06，通用长程任务 Agent）→ 桌面 Agent 应用 MiniMax Code（2026-05）→ **MiniMax Code 2.0**（2026-08-07，基于开源 Pi agent framework 重建）。Agent 产品更名 Mavis（"MiniMax as a Jarvis"）。

## 3. 视频生成线（海螺 / Hailuo）

**[Hailuo 2.3]** E3 / VERIFIED / 中英 / 2025 末 / MiniMax 官方
- 文生/图生视频，1080p、~10 秒，物理/表情/指令遵循增强。

**[MiniMax H3（旗舰，已开源）]** E3 / VERIFIED / 中英 / 2026-07-31 发布，2026-08-03 开源 / MiniMax 官方；虎嗅；minimaxh3.art
- **通用全模态视频生成**：单一上下文统一读取文本/图像/视频/音频，直接生成带原生双声道音轨的视频。
- 规格：**2K / 24fps / 4–15 秒**（Extend 模式可延至 ~30s）；对白+音效+环境声一次前向推理同步生成（非事后配音）；33B 参数开源。
- 全模态参考（Omni-reference）：单次最多 9 图 + 3 视频 + 3 音频（合计 12 文件）；基于指令局部编辑（改角色/物体/场景/声音/节奏）；多镜头单段叙事；画幅 21:9/16:9/4:3/1:1/3:4/9:16。
- 附加接口：H3-Context-IR（深度理解生成结构化增强提示词）、视频再生成（768P→2K）；H3-Max（fal.ai 后训练极速版，480P/768P）。
- 开源 License：**MiniMax Community License**（允许商用+二次开发，对再分发/合规有约束，介于开源与闭源之间）——商用前须 LEGAL REVIEW。
- 定位场景：广告/品牌/电商/产品设计/UI/游戏/短剧/变装/绿幕换背景。

## 4. 语音 / 音乐 / 图像线

**[Speech-2.8（语音合成）]** E3 / VERIFIED / 中英 / 2026 / platform.minimaxi.com
- HD + Turbo 两档；**40 种语言、300+ 系统音色**；音色复刻（上传音频生成 voice_id）、音色设计（按描述生成）；长文本异步合成最长 100 万字符（整本书，句级时间戳字幕）；情绪渲染融合语气词。

**[Music 3.0（音乐）]** E3 / VERIFIED / 中英 / 2026-08-13 / MiniMax 官方
- 新一代开放权重、生产级全能音乐模型（HuggingFace/ModelScope 可下）。注意：付费音乐 API 自 2026-08-20 起对新用户停止，免费音乐接口同步停服。

**[image-01 / image-01-live]** E3 / VERIFIED / 中英 / 2026 / platform.minimaxi.com
- 文生图/图生图；live 版手绘/卡通画风增强。

## 5. 定价（研究参考，2026-06 采集）

| 项 | 价格 |
|---|---|
| MiniMax-Text-01 API | $0.4–1.3/M in、$1.3–4.2/M out（依上下文档） |
| MiniMax-01（lmmarketcap） | $0.2/M in、$1.1/M out |
| M3 | ¥4.2/M in（≤512k）、¥16.8/M out；永久五折 |
| M2.7 | ¥2.1/M in、¥8.4/M out；永久五折 |
| Hailuo 2.3 Fast 图生 | ¥1.35/个起 |
| 图像生成 | ¥0.025/张 |

## 6. 与序境的关系判定（研究层评估，不改变现网）

| 能力 | 判定 | 依据 / 前置条件 |
|---|---|---|
| Lightning Attention / MSA 长上下文架构 | EVALUATE | 只作架构知识积累；现网走智谱 API 不涉及本地部署 |
| M2.5/M3 编码与 Agentic 能力 | EVALUATE | 若未来引入第二供应商做编码/研究辅助可评估；现网不替换，付费 API 暂不依赖 |
| MiniMax H3 视频生成（2K+原生音频） | EVALUATE | 序境有创意视频/短剧/TVC 需求；H3 是开源视频底座候选（对比 Seedance/Kling）；需 GPU 算力 + Community License 合规审查 |
| Speech-2.8 TTS（40 语言/音色复刻） | ADAPT/EVALUATE | 序境报告语音/播客/多语言内容可评估 API；需额度与认证 |
| Mavis / MiniMax Code 2.0（Pi 框架） | EVALUATE | 开源 Pi agent framework 可借鉴为 Agent 架构研究 |
| Music 3.0 | EVALUATE | 音乐生成需求研究；注意付费/免费 API 已调整 |
| Modified-MIT / Community License 商用约束 | LEGAL REVIEW | 任何 MiniMax 模型进生产前必须专业合规审查 |
| 用 MiniMax 替换现网主力模型 | REJECT（现阶段） | 用户已定智谱主力、豆包最少；研究不因"最新"替换生产模型 |

## 7. 安全与合规边界

- MiniMax 全部第三方内容仅作研究输入；进入生产前须审查 License、安全性、依赖、可维护性；只学习、验证、借鉴，不复制受保护代码。
- 视频/语音/音乐生成涉及肖像、音乐、品牌权利，使用时必须自证上传/生成素材授权。
- 不绕过付费权限；付费 API 暂不作为系统运行前提。

---

**本模块待补**：MiniMax 与 Seedance/Kling/可灵 视频横向 benchmark 实测、M3/M2.7 与 GLM-5.3 编码对比、MiniMax Community License 全文合规细读。
