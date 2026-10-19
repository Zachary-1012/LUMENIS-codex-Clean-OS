# 序境自研AI：全产品能力与算力路线研究

研究冻结：2026-10-17 19:55 UTC；目录日期沿任务约定为20261018。状态：研究建议，未经实施批准。没有训练、安装依赖、调用外部模型、使用凭据、修改产品源码/数据库/环境或改变既有基座。

## 1. 核心结论

保留既有gpt-oss-20b/NF4路线，同时建立按任务而非五个角色划分的专用小模型能力。小模型可以是真正的自研模型；是否有产品价值由独立业务测试决定，不由参数大小或是否“训练成功”决定。先统一任务、来源权限、模型版本、评价与可撤回接入；以后可做路由、蒸馏或有条件的MoE组合。异构分类器、ASR、图像模型不能直接拼接权重成为统一大模型。

必须分开三层：第三方基础权重/训练框架；序境自行训练的参数或adapter；序境自己的数据处理、权限、编排、评价和产品逻辑。微调开源基座不得表述为所有基础权重从零自研。模型许可、数据训练权、声音/形象许可与输出使用权分别审查。

## 2. 本次证据与资源事实

源码根：`[LOCAL_WORKSPACE]/recovery_20261017T1925Z/validated_candidates/LUMENIS_20261017T1620Z_dot-zack_NOT_FINAL/product/source`。恢复候选不是最终发布证明。文件SHA256见`SOURCE_MANIFEST.json`。

- `config/ai-owned-foundation.json`、`owned_training.py:18–26`固定`openai/gpt-oss-20b@6cee5e81ee83917806bbde320786a8fb61efebee`；NF4变体固定`unsloth/gpt-oss-20b-unsloth-bnb-4bit@093fba6992ef5a7152481afec0bdfca1ac486998`。不得用小模型替换该批准路线。
- `owned_training.py:316–348`无CUDA明确拒绝，无CPU回退；T4/4090/5090/H100配方各有设备约束。官方Hugging Face教程示范H100 80GB，不是本环境可跑训练的证明。[官方教程](https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers)
- 本次只读系统探针：9个在线CPU，MemTotal=10206484kB（约9.73GiB），当次MemAvailable=8703664kB，32GB overlay约29GB空闲；未见`/dev/nvidia*`。cgroup v2两个路径不存在，因此不声称已读取容器硬限制，也不声称云平台其他GPU资源不可用。训练预算须重新实测，当前不支持既有CUDA配方。
- Jev研究原型v2：`../../research/jev/independent_cpu_prototype_v2/REPORT.md`及`results/evaluation.json`。三类英文合成分类，train/calibration/test各36条、按模板家族隔离；测试准确率58.33%，macro-F1 0.58654。校准集不能同时满足风险≤5%和覆盖≥50%；资格NOT_ELIGIBLE，测试全弃答覆盖0，风险null。24个OOD样本使用上游显式标记，并非学会域外识别。48个回归探针通过不改变模型质量失败。不能继续在已消费test上挑模型/调阈值。
- Gibbs有限匹配策略仍是有限参数数学实验，不是LLM训练或通用推理能力。
- 早前Colab“三步、保存3264 tensors、业务失败”的描述本次未重新找到完整原始运行包，按交接信息标记待独立复核。即使原记录成立，也只证明该次参数更新/产物，不证明完整模型训练、独立业务收益或产品晋升。PEFT保存通常仅含adapter，仍依赖原基座。[PEFT checkpoint](https://huggingface.co/docs/peft/developer_guides/checkpoint)

## 3. 已有接入与真实缺口

### 文本自有服务

`owned_service.py:56–87`准入对象绑定模型/recipe、train/heldout、adapter、checkpoint、评价、人审、SourceUse、runtime与操作范围hash；`_validate_admission_request`允许admit/rollback/revoke。当前文本服务域集合为cth/bmp，runtime类型被固定为OwnedProductionRuntime，不能直接把任意小模型塞进现有服务槽。

调用核查：`core.run_owned_request`委派该服务；`shared/reporting/business_brief.py:850–871`从业务scope构造OwnedServiceRequest；`agent_runtime/task_binding.py`沿受控任务构造agent_plan请求。结论是这些已查文本链面向业务域，不证明全部独立Shared创作覆盖。

### Shared不是完全没有模型入口

`shared/content_creation/speech_transcription.py::build_transcription_files`经源媒体验证、选择音轨、FFmpeg规范化，再调用`system/ai_gateway/owned_speech.py::transcribe_audio`，这是独立Shared合法ASR路径，不走cth/bmp文本槽。返回标注`third_party_pretrained`、MIT、未审阅派生、无说话人分离。取消不提交，恢复从同一已核音频重算；它不自行下载权重。

Whisper base固定revision `31243bad24cc746f07d4c8bfdd2d974872cb1803`；small另有评价权重hash，不推断已产品晋升。声明的12个语言hint是zh/en/ko/ja/fr/de/es/pt/ru/ar/hi/id；接口接受不等于质量合格。

### 不应被配置掩盖的剩余项

- `core.run_owned_multimodal_analysis`仍fail-closed；不能以文本模型或图片传入成功证明视觉理解。
- 独立Shared通用自有文本生成、全部创作/多模态能力的统一SourceUse准入及生产caller闭环，在本次所查代码中未证明；不是断言任何其他路线绝不存在。实施前逐实际caller补齐证据。
- `core.chat:710–724`泛型调用不自动提升为owned。只有`external_user_input=True`且用户明确选Groq才转现有user_api，且注释要求最终adapter重验身份/精确请求；源资料不能因全局配置而获得外传权。不得增加Claude托管、退休provider或自动外部回退。
- 原`providers.py`有历史owned-only文案，而实际Groq例外在user_api；文案、接口、实际权限与可用性必须分开记录，不能仅据registry描述下结论。

## 4. 模型—任务—数据—资源—验收建议矩阵

以下新模型均为研究候选，不是安装、下载、训练、切换许可；候选网页核查时间为本次研究。每次实施须选定精确commit、许可证原文、依赖与字节hash。推荐资源为工程推断/实验起点，不是测得SLA。

| 能力与现有G映射 | 模型/实现路线 | 数据与训练权 | 当前/未来资源 | 必须验证；无AI基础路径 |
|---|---|---|---|---|
| 任务意图、能力候选排序；G31/G83/G108 | 自研字符特征线性分类器/小MLP；多专家共享，不一角色一模型 | 获准真实任务+独立标注；合成仅工程预检；按意图模板/用户/时间隔离 | CPU适合有界小实验；当前v2失败，须新版本与新预封test | 每类F1、选择性风险/覆盖、未知检测、延迟；未达标保留规则或用户直接选动作，模型绝不决定权限 |
| 实体匹配、主题/情感/立场；G153/G181 | 自研匹配/分类头；需要时另审小编码器 | 经训练许可的实体别名与标注对/真实文本；zh/en/ko独立标签说明 | CPU稀疏基线先行，小编码器GPU微调另批 | Precision/Recall、每语言/领域F1、校准、误合并反例；实体事实仍人工核对/确定性匹配 |
| 检索/排序/引用；G108/G189 | BM25基线+候选BGE-M3嵌入，后续领域reranker | 资料可读不等于可训；明确检索使用权；训练query-positive-hard-negative需额外MODEL_TRAIN | 小batch CPU推理可实验，吞吐未测；全量索引和微调需独立预算 | Recall@k/MRR/NDCG、引用落点、时效/撤权；普通关键词检索持续可用 |
| 文本分析、提案、脚本、受控工具建议；G23/G31/G121/G136 | 保持20B基座，领域SFT/LoRA；不承诺全参数从零训练 | 从training_cases签名review+rights输出合格JSONL；教师输出须另有权利 | 当前无CUDA阻断；精确既有GPU配方批准后小预算探针再完整训练 | 同基座同token/算力预算、独立真实任务盲评、数值/引用一致、长任务恢复；手工研究/文稿/计算可完成 |
| OCR/图表/图片/视频片段理解；G23/G124 | 先确定性抽帧与可核OCR；候选Qwen2.5-VL-7B单独审查，不换20B | 有权图片/原页、bbox/文字/图表标注；按文档/视频/实体隔离 | 新GPU评价资源待定；不把7B BF16权重可装入视为全工作内存预算 | CER、字段/表格准确、定位、幻觉/拒答；保留真实页面、人工标注；单帧不冒称全视频理解 |
| ASR与字幕；G23/G128 | 先验现有Whisper base，small仅候选评价；微调独立授权 | 录音取得、转写、训练三种权限分开；按speaker/session隔离 | base短音频CPU质量/时长探针；吞吐与内存实测后才定批量 | 各语言WER/CER、时间戳、数字专名、静音幻觉、取消/源变更、试听；手工稿/字幕编辑、导入仍可用 |
| 配音/播客与实时语音；G23/G128 | 候选Qwen3-TTS-0.6B-Base，独立准入；ASR/TTS/打断并非同一能力 | 只用明确许可声音，克隆需声音本人/权利人同意；内容权利另审 | 官方示例CUDA；本CPU实时性未验证；训练/推理预算分开 | 发音可懂度、专名、时长/响度、授权、打断延迟/回连；人工录音/已许可素材可制作，系统朗读不是最终配音 |
| 图片、视频生成；G23/G121/G128及规划§14 | 图像候选FLUX.1-schnell；视频候选Wan2.1-T2V-1.3B；非当前可用或“全部自研” | 获准Brief/素材、人物/商标/音乐权利、训练集各自核准 | 当前不运行；Wan官方8.19GB VRAM是特定推理声明，不是训练预算；FLUX含附属编码器资源，需整体测量 | Brief一致、人物/物体连续、品牌/文本准确、风险与来源；手动剪辑/渲染/许可素材正常可交付 |
| 受控学习/记忆；G109/G110/G92/G163 | 反馈资产、数据审查、候选实验、评价与批准；记忆检索不是自动改权重 | 正负偏好成对、来源版本、同意、撤回/删除传播；点踩不自动形成DPO样本 | CPU整理/验证；训练独立批准 | 独立留出及真实业务优于旧版、风险不恶化、回滚读回；无模型时继续编辑与人工决定 |

模型来源与限制：
- [BGE-M3模型卡](https://huggingface.co/BAAI/bge-m3)：MIT、支持100+语言，适合检索候选；上游覆盖不是序境各语言验收。
- [Qwen2.5-VL-7B](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)：模型卡Apache-2.0；选择7B仅用于明确候选，不套用同家族其他尺寸许可。本次3B卡许可未解析确认，未列为已核许可候选。
- [Whisper官方仓库](https://github.com/openai/whisper)：代码与权重MIT；转写/翻译/语言识别能力，不是声纹分离或TTS。
- [Qwen3-TTS-0.6B](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base)：Apache-2.0，模型卡列10语言zh/en/ja/ko/de/fr/ru/pt/es/it，与产品12语言集合不同；缺ar/hi/id，不能说一模型覆盖产品全部创作语言。
- [FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell)：Apache-2.0，当前页面提示访问需共享联系信息/接受条件；没有执行该访问流程，不能默认为已获文件或已接受条款。
- [Wan2.1-T2V-1.3B](https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B)：模型卡Apache-2.0；官方给出4090上5秒480P约4分钟例子，不能转为本机承诺，也不将家族全部功能归给此checkpoint。

## 5. 语言与多模态不是一个总开关

UI zh/en/ko是界面本地化验收；创作至少10+语言是内容理解/写作/翻译/字幕/配音分别验收。维持language×task×model_revision×domain矩阵，逐格标not_tested/partial/accepted。12种ASR hints不能代替12语配音；TTS十语有意大利语却没有阿拉伯/印地/印尼语，不能用语言数量相同替代集合核对。未验语言给真实限制、人工校对/导入路径，保留文本/音频/字幕版本与引用，不自动外调API补齐。

## 6. 数据、学习与晋升流程

1. 原Owner冻结任务与评价条件。确认SourceUse用途（读取、索引、派生、MODEL_TRAIN、导出）及人声/肖像条件，禁止仅凭网上可见或已导入推断可训练。
2. 沿`shared/learning/training_cases.py`的review/rights Evidence审查与隔离；去重按实体、文档、模板、speaker、时间及来源家族做，不能仅hash不同就算独立。数据hash、标注者分歧和排除原因随数据卡记录。
3. `training_review.py:101–163`独立精确MODEL_TRAIN审批。模型、数据、预算、依赖、输出、可恢复边界先冻结。没有审批不跑训练。
4. 同任务强规则基线/原模型对照。验证集调参，test只作预封终评。已看过的test转回归集，另收新test；随机种子、统计区间与失败子群一并披露。
5. artifact重载、完整身份绑定、有限资源探针、断点恢复与撤权测试。完成step/loss下降/文件存在均不是质量门通过。
6. 人工业务质量审查+风险评估后才申请admit；持久服务由产品自有运行环境承载。免费临时GPU、Codex会话、开发电脑在线都不是生产SLA。
7. shadow评价不产生外部效果；灰度采用也须批准。现有Gateway服务只接收有权限、有SourceUse的请求，结果派生标识不可改成Canonical。保留旧版本，明确rollback目标hash；撤销先阻断新请求，校验未完任务处理与最终读回。

当前`shared/evaluation/runner.py::measure_content_pattern`只是精确短语覆盖，明确NOT_ELIGIBLE、缺独立heldout/真实业务结果；不能借覆盖率自动晋升。学习资产数量/批阅次数、48回归通过等也不能替代效果证据。

## 7. 可审核分段路线与退出条件

A. 现在：只读材料/合同/实际产物核对；建立本报告与G映射。已完成，不改产品。
B. 待批准的数据准备：选择一个真实业务痛点，例如意图分类或检索重排；明确数据来源/训练权、目标人群、强基线、风险与覆盖要求、硬预算、新test。先修数据不足，不直接把失败v2改名上线。
C. 待批准CPU独立研究：按冻结预算训练单个小专家，保存失败也交付；退出是重载+独立评价结论，未达标即NOT_ELIGIBLE。成功仅允许进入产品接入审查。
D. 待批准产品集成：沿既有Gateway/Task/SourceUse/Evaluation Owner扩展明确类型适配，不建第二Gateway、不更换20B。先核实际caller，填独立Shared文本/视觉缺口但不伪造cth/bmp scope绕过检查。
E. 待资源与批准：20B领域LoRA和具体ASR/视觉/TTS/生成任务逐个预算、固定依赖、权限、checkpoint测试；推理和训练分别验收。是否购买算力由用户决定，不以“免费GPU”承诺时限。
F. 合并研究：可先保持路由系统；蒸馏需教师输出权利和统一训练任务；BTX要求同基础起点、架构/隐藏维度/词表兼容，并需训练token路由；不是把异构模型二进制拼接。小专家最可靠可迁移资产是标签、数据、评价、失败案例和合法监督，不承诺权重将来都能合并。[BTX原论文](https://arxiv.org/abs/2403.07816)、[蒸馏原论文](https://arxiv.org/abs/1503.02531)、[LoRA原论文](https://arxiv.org/abs/2106.09685)。

## 8. 训练依赖与恢复边界

`owned_training.py:504–650`的NF4版本锁：unsloth2026.9.12、unsloth_zoo2026.9.8、transformers4.56.2、trl0.22.2、torch2.11.0+cu128、bitsandbytes0.50.2、tokenizers0.22.2、triton3.6.0。此为源码要求，不是本机已安装或依赖安全证明。peft/datasets/safetensors在该局部版本锁没有精确版本，需完整环境锁补充，不能猜测。

真实调用：FastLanguageModel.from_pretrained/get_peft_model；Dataset.from_list；AutoTokenizer.apply_chat_template；非NF4 AutoModelForCausalLM+Mxfp4Config(dequantize=True)+LoraConfig/get_peft_model；SFTConfig/SFTTrainer.train。禁remote code/local_files_only；report_to=none、push_to_hub=False，不能复制官方教程上传Hub/遥测行为。callback在step/substep/pre-optimizer等边界核权限；恢复绑定checkpoint策略并恢复optimizer/RNG/data位置，adapter文件本身不足以恢复训练。

第三方盘点交叉核查：仅按imports/requirements计数会漏掉运行时版本门中的unsloth_zoo、bitsandbytes、tokenizers、triton；应纳入依赖清单，不能把未直接import等同未依赖。Whisper产品解码配置beam_size=1、temperature标量0.0，不具有默认多温度阶梯回退；上游可选行为不等于产品已启用。

统计CPU环境`requirements-statistics-cpu.txt`另列torch2.14.1+cpu及transformers5.20.1，不能为安装小专家把训练GPU锁静默升级成这一套。依赖版本相容性、许可证、工件字节、冷启动和恢复分别验证。

官方资料补证：[Transformers v4.56.2 LICENSE](https://github.com/huggingface/transformers/blob/v4.56.2/LICENSE)、[PEFT LICENSE](https://github.com/huggingface/peft/blob/main/LICENSE)、[Datasets LICENSE](https://github.com/huggingface/datasets/blob/main/LICENSE)、[Safetensors LICENSE](https://github.com/safetensors/safetensors/blob/main/LICENSE)。后三个链接为当前上游，不是本项目精确安装版本法律/字节验收。本次TRL v0.22.2 LICENSE网页读取Internal Error；需在冻结下载或官方可读源码补验，不标已核。

## 9. 未核与停止边界

没有启动服务观察、全产品caller穷举、原Colab产物独立重载、新模型下载、实测训练或真实多语言人评。候选资源/SLA未测；免费GPU可用性未知；模型商用许可元数据不豁免数据和人格权。公开材料研究不构成训练/安装/产品修改授权。研究结束于提交本报告与映射，下一执行动作须明确批准模型、数据、资源与改动范围。
