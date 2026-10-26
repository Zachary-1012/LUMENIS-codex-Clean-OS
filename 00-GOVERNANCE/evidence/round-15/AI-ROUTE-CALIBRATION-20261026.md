# 寰意全产品规划收敛与 AI 路线校准：变更、核对及实施依赖

本轮依据 PO 于 2026-10-26 提交的两份 Markdown、附加完整执行文本及随后“全部关联文件更新”的直接指令，完成现行规划的原位调整；不是重新定义产品，也不是实现、模型运行或专业能力验收。GPU 训练路线为 **WITHDRAWN_BY_PO**，完整行业 AI 目标保留。本文是采用和交付证据；长期规划仍由原 Architecture、主规划、Owner 和合同维护。

## 1. 授权、双源与保护边界

采样：`2026-10-26T23:21:10.894057+08:00`，主路径 `D:\LUMENIS_REBUILD\序\序境`。在线main经有界fetch和独立Git远端引用核实；不是把缓存当在线结果。

| 对象 | 开工实测 |
| --- | --- |
| GitHub main / origin/main / 本地main | `7361e37705e5599dbacd3e564ed9a5a19cb6a379	refs/heads/main` / `7361e37705e5599dbacd3e564ed9a5a19cb6a379` / `7361e37705e5599dbacd3e564ed9a5a19cb6a379` |
| 原工作分支 / HEAD | `codex/full-product-implementation-20261025` / `ec831c8e80b6463797d7223cdd3c6a20ae327ef2` |
| 与 main 关系 | ahead 2 / behind 0；暂存为空，stash为空 |
| 工作区保护 | 本轮冻结168条dirty/untracked状态；数字是采样，不是完成率；保全文件摘要随本机原任务记录保存 |
| 本轮规划发布基线 | `7361e37705e5599dbacd3e564ed9a5a19cb6a379`；`codex/ai-route-plan-20261026`，原分支不切换 |


三份输入完整读取，文件身份如下。私有附件不复制到公开位置；此处仅记录名称、字节数及摘要。

| 输入 | 字节 | SHA256 |
| --- | ---: | --- |
| OEVIRA_AI双源源码核对与无GPU训练路线校准_20261026.md | 16619 | `34f0fe16a7c02397cca59a400323c78cd9b552b8d921b0c5801eac4a9e369a4e` |
| OEVIRA_给Codex_垂直行业AI规划收敛与撤销GPU训练_20261026.md | 27050 | `c462e7f10b40595cbcd2da9be9b02f557f3d8b273626a621a40d4c90f9819944` |
| 已粘贴的文本.txt | 20600 | `7712f55fbe4ddb38f1dbddf607a9379528f7a52cd58000e399c8999bde6d1777` |


主区有效 Shared、Office、媒体、采集、业务、上下文与打包工作不由本轮覆盖。独立规划工作树基于开工时最新 main，只移植本轮语义差异；主区同步相同 AI 语义，并保留其尚未发布的产品收敛变更。两者不是完全相同的组合版本，本轮不声称线上线下源码已统一。原 PR #146 保持草稿、未合并；本轮 PR 也等待审阅和适用合并批准。提交只引用 `Refs #17`，不关闭该 Issue。

本轮没有修改产品 Python/Dart、模型配置、执行 schema、测试断言、数据库或个人 Codex 配置；没有启动/重启服务、读取生产业务数据、采集、模型推理、训练、下载权重、安装依赖或派遣 Agent。公开模型卡、源码元数据和许可证读取不是模型调用。未将已有 GPU/权重历史删除，未恢复旧开发任务。

## 2. 原要求到消费者的逐项处置

| 原要求与完整章节 | 线上／本地源码事实 | 冲突 | 处置 | 新方案与实际消费者 | 专业质量及成本验收 | 本轮状态 | 后续实现依赖 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| J27、G17、G21、Architecture §6、U18–U20 | main 与主区仍有训练状态、adapter/recipe、CUDA 绑定；本地已有更完整 Shared scope | GPU 必训妨碍合法预训练推理；不能因此撤销行业能力 | 撤销训练路线；保留全 AI；改写分类准入 | 原 Gateway 的 PRETRAINED_INFERENCE / CPU_SPECIALIST / STRATEGY_CONFIGURATION；CTH/BMP/Shared/Agent 仍各自消费 | 权限、模型身份、资源、专业质量、冷重开和回滚；禁止假训练标签 | 规划已改；执行迁移未实现 | 原 owned_service、owned_inference、owned_model_admission 同版升级及明确运行批准 |
| J27、G163、Math adoption | 九 family 有不同有限实现与独立边界；历史 Gibbs 已训练未上线；不等通用推理能力 | 一次基础模型训练或求解器输出被误作智能增益 | G163 保持 OPEN；改写工具/约束/策略与模型协同 | 原数学 Owner 产出有前提/量纲/误差的结果，业务和模型分别引用 | 独立新任务、反例、适用假设、模型与工具贡献分别核；不承诺一般算法已完成 | 规划已改；数学与模型专业验收未完成 | 保留原九 family 未闭项及准入/数据条件，不能靠删除要求闭合 |
| J26、J27、G170、Content Learning | apply_approved_rule 写 inactive candidate；build_prompt_context 读取 promoted 规则/样本 | 提交候选被当作生效/学习增益；默认 DPO/夜间 LoRA 过时 | 改为四类学习，撤销 GPU 参数路线 | 原 Learning/Memory/Evaluation 的资料、用户状态、策略；必要时 CPU 专用参数 | 来源/版本/撤回、激活与消费回执、独立留出收益和预算停止 | 合同已改；激活链与收益未验 | 原消费者补精确版本使用/撤回传播；无自动常驻反思队列 |
| J27、J28、AI-01/03/04 | 主区 ContextPack 已含完整 source-free 历史、人工约束/草稿/决定、排除及派生失效；普通会话 tokenizer 未绑定不算计量 | 用旧 6×800 描述当前本地，或完整存储冒充完整注入 | 复用本地正确实现，校准陈述及 token 合同 | context_pack、conversations、task_binding、planner；必需约束与可选材料分层 | 否定/最新人工稿不丢；必要层超窗不静默截断；新任务、跨日重开与成本 | 规划已改；运行未验 | 实际 tokenizer/runtime、授权材料装配与对应消费者 |
| J26–28、AI Memory、G21 | main/主区词法实现有差异；主区有 BM25、cosine/RRF/scorer 和原文定位/撤权；神经执行器未绑定不能算完成 | 词法计分被称为完整语义检索，BM25 与 cosine 直接相加 | 保留词法基线，设计真实混合检索与少量重排 | 同一授权集合分别召回→RRF→cross-encoder→原文/版本复核；同一 Canonical 派生索引 | Recall/NDCG、引用正确性、来源族去重、撤回与 p95/RAM 同验 | 设计完成；完整神经检索未验 | 权重/许可/核准、索引版本与缓存失效；BM25_ONLY 明示能力边界 |
| CTH/BMP、G168 | 现有领域/Task/Permission/Artifact 是既有消费者；文案曾以帖子数代曝光 | 计量单位错误；预测费用混实支 | 原位修正估算合同 | CPM×展示/1000 或 CPC×点击；市场/时间/币种/税口径/费率来源，预算/承诺/实支/退款分账 | 原件数值、缺失 MISSING、校准误差/区间、预算与真实结果；不预填精度 | 规划已修正，计算执行本轮未改 | 领域费用消费者按新单位及不确定性合同落实 |
| G169、CTH/BMP 专业判断 | MMM 是已有规划，非本轮已运行 | 声量/相关性被冒因果销售贡献或 ROI | 保留 MMM 目标并补识别合同 | 原分析 Owner 核单位/频率/误差、控制/滞后/季节性/共线性与样本充分性 | 敏感性、滚动样本外、实验锚点；识别不足为 INSUFFICIENT，不伪因果 | 规划已改；模型分析未执行 | 可识别数据、工具实现、独立评价；不能恢复 GPU 作为前置 |
| G50、G170、J19–25/27、独立 Shared | 本地已有 Shared workspace scope/真实消费者，不能退回旧 main 的不完整说明 | 外部 API 或业务 Case 被当成所有创作前提 | 保留原 Brief/人工稿/品牌约束与独立使用，整合真实推理/工具 | 原 content_generation/internal_pitch、研究、Office、视频/播客内容 Owner；不新建图像编辑器 | 原创与品牌适配、精确引用、局部修改、保存v1/v2、重开/导出/恢复 | 消费合同已同步；作品质量未验 | 获准模型、原工具和完整专业任务；手写稿保存不替 AI 创作 |
| J28、AI-02/05、Agent/Skills | 原 Task/EffectFence/SkillRegistry 和服务端身份存在；源码存在不等实际效果 | 只写配置/成功状态就报智能任务完成 | 保留真实执行、取消接手与对账 | 原 descriptor/schema→任务→许可→工具→回执→原成果/恢复；模型不授权 | 重复执行、迟到结果、超时未知、撤权/断线；版本及预算 | 原合同补充，未运行任务 | 具体工具能力与资源准入，完整消费者接通 |
| PE-19/21/22、三语/十二语及多模态 | 本轮静态核模型卡；没有任何新增模型加载证据 | OCR冒视觉理解、ASR冒音频理解、三语接口冒十二语质量 | 能力分开准入；保留完整目标 | text/embedding/reranker/OCR/vision/ASR/TTS 各自经原 Gateway；专用模型不是全部 AI | 每语言/模态任务质量、权利、专业人评；CPU/RAM/耗时与恢复 | 推荐组合与限制已记录；全部模型运行未验 | 模型/语音资产许可、转换分片hash、兼容内核、授权和质量 |
| Source Owner、Real Delivery、AI Checklist、AI-01–05、AGENTS/CURRENT | 线上与本地文档/代码不同；已有结果不归零 | 训练、实现、运行、发布和用户成果混为一谈 | 同步原位正文与当前覆盖索引；不复制第二套任务系统 | 原 C2/C3/C4/C5/C6/F 的职责与版本化成果；本轮不派工 | 独立基线/部件消融、最终留出、关键失败门槛、全部原要求逐项验 | 文档 PR；不代签任何能力完成 | 下一阶段明确实施/运行批准及当前代码重新对齐 |

## 3. 分类准入的实际迁移点

源位置以本轮本地读回为准，线上旧实现与本地更改分账：

- `owned_inference._prepare_candidate_files`、`_load_local_kernel`、`_production_runtime_identity`：保留旧版本只读解释，新增类别路由到已准入 CPU 推理内核；不能通过假 adapter、跳过 `_require_cuda` 或空身份让旧 GPU 对象冒新能力。
- `owned_service.OwnedModelAdmissionRequest`、`_validate_admission_request`、`_runtime_identity`：在同一请求合同增加互斥类型和版本，保留本地 Shared workspace scope；精确资源身份与实际运行对象一致。
- `security/owned_model_admission.py::_resource_payload`、`owned_model_admission_resource`、`OwnedModelAdmissionVerifier.recheck`：原审批资源摘要升级时绑定类别/schema、scope、权重或策略、内核、质量和预算；旧批准不自动匹配新资源，也不删除每次重核。
- `context_pack`、`agent_memory/retrieval.py`、`semantic.py`、`core.py`：沿原 tokenizer、授权召回、增量索引和模型状态消费者实现；当前 `token_budget_verified=False` 或未绑定神经模型保持真实，不能只改文字。
- `LearningLoop.apply_approved_rule/build_prompt_context`：候选提交、评审、激活、实际选择、结果评价分别绑定版本。无需 GPU 的更新也不绕过批准、数据权利与回滚。
- `owned_executor/owned_evaluation`、Task/planner、CTH/BMP/Shared 与 AI 界面在实施阶段同步读写/导出/撤权/恢复。新 schema、精确字段校验、模型加载和回归都属于后续代码改动，本 PR 不修改任何执行文件。

下表是磁盘源码身份，不是内存加载身份；本地与main原字节摘要分开，换行差异另作规范化判断。

| 源文件 | 本地主区SHA256 | main blob SHA256 | 规范化后相同 |
| --- | --- | --- | --- |
| `lumenis/system/security/owned_model_admission.py` | `1ce57ae464b0745ffa391748a8c62c1d090950330bdf238b8798cdec47383e6f` | `a8d5ace5315757ea858f30e2a46bd15169a98acfbcdea737539e2e0da7aebcf0` | 否 |
| `lumenis/ai_hub/context_pack.py` | `3d4c3997d62bb141bd6a36877da8d3b81a50177b9b7633a30744cfc4c0ef543e` | `None` | 否 |
| `agent_memory/retrieval.py` | `90068cac61be83d08154a02431eef58abd8773c3a33a45e1f4d0b6dea69d31b8` | `None` | 否 |
| `agent_memory/semantic.py` | `dc99080e952855fc6d7720b7e6dcfd841122b4ef226e1863cef9a2ee100d7a6a` | `03ddfcac676ee688e135dc0c670c2570c43a20cd760dc46f612a43845a613222` | 否 |
| `lumenis/system/ai_gateway/core.py` | `8220358d2e8a196191f0defbf24b3ae79bea35aa85d1756055e15a51ac6a7895` | `7f719548e85dc0ea8b97c409113c1a5d07b6dbc67c77e0fdabefdfa114fa058e` | 否 |
| `lumenis/shared/learning/loop.py` | `0b484c7174c93b59821ddb60cb57b2b2740840315853a2964716b50e24dfac44` | `4c8f17b02284895a5f3bf6787d34704123725ed3b9f3168459fffade4813b383` | 是 |
| `lumenis/system/ai_gateway/owned_inference.py` | `7da442d5b6f2aa936ebe269ad9714004efad8a5258644d65c6fa039454e81a65` | `15466b327a8e46d8f359f6485d5d90f7a435fa4d84a204b640e87540203839ce` | 是 |
| `lumenis/system/ai_gateway/owned_service.py` | `dad590159654e3653eb36e98773f668d3b42a405baf9040ef91ecb8b596b9e94` | `d595e151b075c71a5e0f861006c3721fddd5ea16c98fb2358418c4faef9ca154` | 否 |


## 4. 推荐组合、有限备选与资源取舍

**这是待评估/待准入组合，不是切换主模型命令，也不是声称模型已可用。** 优先复用已合法批准且满足实际质量/资源的现有推理能力；旧 gpt-oss/NF4 只保留历史身份，不因名称相同自动获得预训练推理身份。CPU 默认一次一个重推理作业，按模态加载/卸载，避免同时驻留全部模型；检索分块/缓存，重排限小候选集。正式 RAM/延迟上限要在该台设备测量后冻结，本轮不运行模型。

| 能力 | 推荐及固定 revision | 有限备选／边界 | 资源与质量取舍 |
| --- | --- | --- | --- |
| 行业文本推理/创作 | [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/tree/cdbee75f17c01a7cc42f958dc650907174af0554)，Apache-2.0；拟用已核版本 CPU 内核与可追溯量化 | [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B/tree/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e)，Apache-2.0；只有同任务质量满足才可另选，不自动降级 | 4B×4bit 理论参数约2GB；不是 GGUF 文件大小/运行峰值，另有量化元数据、KV和工作缓冲。1.7B约0.85GB同理；小参数不保证专业判断/创作质量 |
| embedding | [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small/tree/614241f622f53c4eeff9890bdc4f31cfecc418b3)，MIT | 无权重/质量未准入时保 BM25_ONLY，明确未完成神经增强 | 官方 query:/passage: 前缀与512 token窗口；长资料分块、页段锚点，不截断整资料冒完整理解；ONNX量化按CPU指令集实测 |
| reranker | [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3/tree/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e)，Apache-2.0 | CPU可能偏重；先比较8–16候选的有界实验预算，值不是产品上限；未达标不能把RRF冒精排 | 仅对授权融合候选评分；重排收益、漏召回、p95、峰值RAM同测，不能以降低证据范围换快速 |
| OCR/表格图文提取 | [PP-OCRv5 server det](https://huggingface.co/PaddlePaddle/PP-OCRv5_server_det/tree/ca867c897ecbca8873081573a802ad70d499cb94)＋[server rec](https://huggingface.co/PaddlePaddle/PP-OCRv5_server_rec/tree/b26c3587fda8da3c8ec0ce357214b4d661ff1558)，Apache-2.0 | 沿已装解析器与现有源定位；该组合卡片不能作为韩语/十二语完整覆盖证据 | 分页/分图、有界分辨率；保表格结构和位置。OCR字符成功不等图像语义或图表推理 |
| 视觉理解 | [Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct/tree/89644892e4d85e24eaac8bacfd4f463576704203)，Apache-2.0，独立候选 | 内核支持、CPU转换/视觉编码器兼容未验，不能用OCR替签；不自动下载 | 2B×4bit约1GB仅语言/总体参数量级估算，视觉组件和图像token另计；先冻结真实图表/画面任务再验 |
| ASR | [openai/whisper-small](https://huggingface.co/openai/whisper-small/tree/973afd24965f72e36ca33b3055d56a652f456b4d)，所核模型卡 Apache-2.0；内核与模型许可分开 | 已批准本地能力优先复用；faster-whisper CPU int8 为兼容候选 | 分段/时间戳/重叠边界和专业词准确性；ASR不等说话人分离、音乐/情绪理解或完整播客质量 |
| TTS | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M/tree/f3ff3571791e39611d31c381e3a41a3af07b4987)，Apache-2.0；82M×4byte约328MB参数估算 | [MeloTTS-Korean](https://huggingface.co/myshell-ai/MeloTTS-Korean/tree/0207e5adfc90129a51b6b03d89be6d84360ed323)，MIT，仅韩语补充候选；不是默认多套常驻 | 逐语言/声音资产另核许可、韵律/发音及专业听评；现有系统朗读仅预览，不冒制作声音。未证明十二语及声音质量，不补造声纹授权 |
| 数学/经营工具 | 原九family有限实现、确定性统计/单位/费用与适用业务工具 | 不增加新求解真相源；一般算法未完仍保留原缺口 | 工具可算/模型可解释/业务可用分验；错误前提不能由模型流畅文字掩盖 |
| 可选CPU专用学习 | 相关性、实体候选、广告概率、风险/排序校准中有合法标签且有收益的原Owner任务 | 没有独立增益就不采用，不为“自研”标签强加训练 | 先适用规则/统计强基线，锁定主体/时间/来源族留出；参数重载、校准与CPU/RAM/时间预算 |

固定内核元数据和许可证已读取：

| 内核 | 固定提交 | 本轮读取的许可证 |
| --- | --- | --- |
| ggml-org/llama.cpp | `caa8191df159f764fb0160e3d2fc6be008948aee` | [MIT](https://raw.githubusercontent.com/ggml-org/llama.cpp/caa8191df159f764fb0160e3d2fc6be008948aee/LICENSE)；文件SHA256 `94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d` |
| microsoft/onnxruntime | `11fdbcdc56128c20c843445396952261e9953660` | [MIT](https://raw.githubusercontent.com/microsoft/onnxruntime/11fdbcdc56128c20c843445396952261e9953660/LICENSE)；文件SHA256 `2f07c72751aed99790b8a4869cf2311df85a860b22ded05fa22803587a48922c` |
| SYSTRAN/faster-whisper | `9e472ae9de8bb374552f531f752654554b76b2d6` | [MIT](https://raw.githubusercontent.com/SYSTRAN/faster-whisper/9e472ae9de8bb374552f531f752654554b76b2d6/LICENSE)；文件SHA256 `af6798135e729f8aa6c853936d037dfdea449734d26b8ea6a89805fca758c0d5` |
| PaddlePaddle/PaddleOCR | `dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf` | [Apache-2.0](https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf/LICENSE)；文件SHA256 `3840c5c0c61c294264d2dd77b8777be6ddd90121ef4e0e64abcd22edea581d6e` |


上述 pinned 模型卡/许可证仅是研究准入依据，不是转换产物。未来实施必须记录实际输入 checkpoint revision/shard hash、转换脚本/命令/参数、输出所有分片hash、tokenizer/chat-template、内核构建及传递依赖版本。模型卡的 base_model 名称不能证明转换来自批准 revision；本轮不重转、补写历史版本或装新环境。

十二语、多模态和原专业标准完整保留。推荐中未验证的语种/模态/CPU兼容性明确是准入与质量待办，不用隐藏降级、外部强模型或恢复GPU训练补结果。需要外部模型/资源时另行明确用途、成本和授权，本轮无此执行。

## 5. 研究机制采纳及证明边界

- [ACE v3](https://arxiv.org/html/2510.04618v3)：采用有来源/适用条件/反例的结构化增量经验、局部更新与纠错传播；不复制常驻多Agent框架，不把研究分数直接变成产品收益。
- [GEPA v2](https://arxiv.org/abs/2507.19457v2)：采用执行反馈驱动的有限策略候选和独立比较；策略预算、停止条件、激活及撤回都走原Learning/Evaluation。论文方法不证明本地已经优化成功。
- [2026提示优化研究 v1](https://arxiv.org/html/2610.12601v1)：用于约束验证器偏差和选优过拟合风险；最终留出不得反灌，模型裁判不能单独批准自身。文献中的任务、评价器与多seed证据不泛化为寰意所有任务的保证。

优化在相同输入、模型版本和任务预算下比较：原系统/模型直答、检索、业务工具、策略经验、可选小模型、完整组合；工具与模型收益分开。冻结新品牌/主体、时间和来源族留出，原稿/转载不得跨集合；报告多次运行分布和失败。事实/数值回原件，行业判断、原创、品牌自然度与成果可用性独立盲审，关键越权/错归属/幻觉引用/重要否定遗漏/重复效果不能被平均分抵消。成本包括首个有据结果和全任务p50/p95、峰值RAM、tokens、调用费、修改及恢复，不预填节省比例。

## 6. 全产品原位收敛与退役条款处理

不是仅修改AI章节。当前调整已同时进入唯一Architecture、主规划、总草图、Experience、Owner、范围/采集/交付合同、详细界面规格、README、AGENTS、续接入口与原HTML工单。原30成果组、396个唯一coverage_ref和213交互保持；原ID保留变更处置，撤销的路线不改称通过。

| PO决定 | 当前规划落位与清退 |
|---|---|
| 境内经营主体、可添加删减 | 当前范围合同及Architecture、主体设置/关系规格同步；删除全球扩库、国家配额和全球成熟度发布门槛；保历史资料和Permission |
| 精准任务采集与固定监控 | 当前问题、时间、来源缺口驱动；浏览器抓取、舆情/活动/营销监控保留；用户选择监测范围频率，可暂停结束；删入口触发扩库与无限采集要求 |
| 近期时间线 | 近一周/月/半年/一年/自定义；原生事件、发布和捕获时间分开，历史类比不混当前事件 |
| 研究/文稿服务当前工作 | 主规划、草图、Shared/AI/业务规格、README同步；删除强制独立研究产品与结果搬运步骤；原创创作及视频/播客后期可以直接开始 |
| 官网展示 | 官网README/开发参考、原J01及草图同步；只展示制作好的演示、场景/案例/帮助和产品链接，无嵌入功能试用、上传/分析/生成 |
| 前端风格与范围 | 原像素赛博＋植物生态＋复古未来主义、满天星及五植物角色、任务布局、动效选择、三语/无障碍保留；独立图片编辑器不恢复 |
| 无GPU必训行业AI | 本记录§2–5及原J/G/PE/AI规格保留完整能力；分类推理/策略/可选CPU专用学习，不强迫预训练推理拥有自训回执 |
| 执行顺序与连续性 | 原主规划§9.0及原工单按实际能力依赖组织；研究/文档是任务内能力，不让用户逐工程模块通关；已暂停实现不自行恢复 |

两个治理检查器同步适配：主体范围检查不再强制全球覆盖；原则检查不再强制历史固定角色模型。保留账号/模型由PO选择、来源/权限、数据真实性、历史保护、暂停、CI及完整能力要求。增加对应范围负例，防止退役全球门槛回流或把产品实现混入RULES_ONLY_PUBLICATION；没有改必需工作流或降低产品验收。

`OPENAI-MATH-ADOPTION-20261007.json`等历史证据保持原字节身份；日期和原训练回执不构成新训练授权。当前路线在原Markdown和本记录更新。产品加载器、执行配置、数据库和未审实现本轮未修改，其分类迁移依赖仍见§3。

## 7. 验证、保护和发布状态

本次收口核对时间：`2026-10-27T01:12:03.607002+08:00`。仅对文档及受影响治理工具执行必要验证，不启动产品、浏览器采集或模型。

| 检查 | 实际范围与结果 |
|---|---|
| 原要求与工单投影 | 30成果组、396唯一coverage_ref完整；全部当前来源绑定及HTML五项来源摘要核对通过；未提高功能验收状态 |
| 规划一致性 | Constitution、Source adoption、Experience唯一/blueprints/anti-template、Only-One通过 |
| 发布边界 | staged治理门禁、精确路径diff --check通过；实际暂存只有规划/文档与既有治理工具/相应回归 |
| 修改的治理工具 | 三个Python文件编译通过；新增两项政策负例通过；Ruff新增问题为0，原22项格式/既有风格问题保留并明确记录，不称全绿 |
| 原工作区保护 | 冻结4783项已跟踪文件身份；本轮选择路径之外无修改/缺失，原实现分支/暂存和未提交源码保留 |
| 产品运行及专业验收 | NOT_RUN；没有产品执行代码变化，不能由文档检查升级 |

本轮发现并修复的规划核对失败：AGENTS重复规则超过114688字节上限，已删除重复正文而保留唯一规则引用；原则检查仍要求历史固定模型配置，已按当前PO权限修正；README删重时漏掉三个仍有效的域名词，已恢复正确双语定位。原失败记录保留，不改判历史结果。

完整治理文件回归另暴露Windows隔离检出把不可变历史证据换成CRLF而违反原SHA；仅在临时发布工作树按Git已提交blob及原固定SHA核实换行，不改证据内容、检查值或主区文件。换行复原后四项clearance治理回归通过；此前通过的其他治理用例复用原结果，失败日志保留。这不是产品业务回归。

首轮AI规划PR的历史检查：head `89de5080ec794b7bc0c2923adbb3f49eca1e7d68` 的Product `40357328779` / App `40357328954`成功；更早head `1ca51de917e1daa57d15dac6c070195f74af3249` 的Product `40356178544`因许可标识缺失失败，补回许可要求后修复。旧CI不覆盖本次全产品增补；新CI必须按本次推送SHA读回。

| 状态层 | 结论 |
|---|---|
| 当前规划调整 | 已在原位完成并统一当前绑定；不是新总规划 |
| 发布途径 | 原规划PR #147增补，Refs #17保持OPEN；实际提交/CI以该PR精确版本为准 |
| main | 按后续PO“线上线下统一、唯一主线”指令，经审阅与必需CI后仅合入本规划PR；读回前不称main已更新，不合并未审#146 |
| 产品代码与运行 | 保留原有效本地成果，本轮没有实现迁移、模型调用/训练、Core切换或部署 |
| 完整产品闭环 | 尚未交付；原逐能力真实结果、修订/重开/恢复、专业及组合验收仍须实施完成 |

全部改动路径（同一规划PR，包含此前已发布的AI修订）：

- `.agents/skills/lumenis-local-engineering-tools/SKILL.md`
- `.agents/skills/lumenis-progressive-context/SKILL.md`
- `.agents/skills/lumenis-task-router/SKILL.md`
- `.codex/README.md`
- `00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md`
- `00-GOVERNANCE/LOOP-PLAN-20261014/execution-workorder.html`
- `00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md`
- `00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md`
- `00-GOVERNANCE/LUMENIS-AI-PRODUCT-CLOSURE-CHECKLIST-V1.md`
- `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md`
- `00-GOVERNANCE/LUMENIS-CONTENT-CREATION-LEARNING-SOURCE-CONTRACT-V1-20260911.md`
- `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`
- `00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md`
- `00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md`
- `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`
- `00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md`
- `00-GOVERNANCE/LUMENIS-ROUND-02-CHARTER-CURRENT.md`
- `00-GOVERNANCE/LUMENIS-ROUND-03-CHARTER-CURRENT.md`
- `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`
- `00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md`
- `00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`
- `00-GOVERNANCE/evidence/round-15/AI-ROUTE-CALIBRATION-20261026.md`
- `00-GOVERNANCE/evidence/round-15/OPENAI-MATH-ADOPTION-20261007.md`
- `00-GOVERNANCE/evidence/round-15/professional-enhancement-20261024.md`
- `00-GOVERNANCE/evidence/round-15/source-adoption-20261018/EXISTING-OWNER-WORK-HANDOFF.json`
- `AGENTS.md`
- `README.md`
- `contracts/experience/screen-specifications/ACC-02.md`
- `contracts/experience/screen-specifications/ACC-03.md`
- `contracts/experience/screen-specifications/AI-01.md`
- `contracts/experience/screen-specifications/AI-02.md`
- `contracts/experience/screen-specifications/AI-03.md`
- `contracts/experience/screen-specifications/AI-04.md`
- `contracts/experience/screen-specifications/AI-05.md`
- `contracts/experience/screen-specifications/BMP-02.md`
- `contracts/experience/screen-specifications/BMP-06.md`
- `contracts/experience/screen-specifications/README.md`
- `contracts/experience/screen-specifications/SCREEN_SPEC_TEMPLATE.md`
- `contracts/experience/screen-specifications/SH-01.md`
- `contracts/experience/screen-specifications/SH-02.md`
- `contracts/experience/screen-specifications/SH-04.md`
- `contracts/experience/screen-specifications/SYS-02.md`
- `scripts/audit_tools/verify_ai_native_constitution.py`
- `scripts/audit_tools/verify_codex_takeover_governance.py`
- `tests/test_online_progress_governance.py`
- `website/DEVELOPMENT-BRIEF.md`
- `website/README.md`

当前只交规划及对应治理修正。产品实现继续遵守当前暂停，不能把文档收口当作任何功能已完成或恢复旧GPU路线。
