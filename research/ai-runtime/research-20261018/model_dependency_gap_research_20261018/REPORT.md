# 序境模型依赖研究补核：固定发行物、复建边界与新增声音链

研究时间：2026-10-18 00:25 UTC。性质：只读研究；不是法律意见、商业分发验收或执行许可。原 20B 基础目标保持，小模型、多模态和多语言是补充。没有修改产品、数据库、运行环境或 GitHub；没有安装/导入所下载代码、运行模型、训练、下载大权重或调用外部模型 API。

## 1. 去重基线与研究方法

已读 owned_ai_research_20261018 的主报告、许可证增补，voice_postproduction_research_20261018/mobile_voice/report.md，第三方盘点最新 followup_training_libraries/REPORT.md 与固定发行元数据，以及 Claude Quickstarts 历史 LICENSE_SERVICE_REVIEW.md。产品基线是第三方盘点 main4dab 副本，commit 4dab98ed6357133da9307de846180ed4f7bba5f5，不把恢复旧副本当最新部署。

既有工作已覆盖：TRL 固定源码读取、text-only loss 与 tokenization 差异、checkpoint safetensors 不代表无 pickle、Whisper 不是 TTS、12 语 ASR 与 10 语 TTS 不同、App 私有声音包不等于通用权重。这些不重复作为新发现。新的问题是：发布的 wheel 实际含什么许可；TTS 与 20B 的环境是否可共存；固定权重与原基座、音色条件的可重建关系是否闭合。

方法：官方 PyPI release JSON → 官方文件地址 → 仅下载两个普通 Python wheel 到研究目录 → SHA256 与 PyPI 声明比较 → 用标准库 zipfile 仅读取文字成员，未执行归档内代码。另读取 GitHub/Hugging Face 官方元数据并将 main 解析为 commit 后读取固定原文。对模型仓库仅读模型卡和 config，不下载权重。所有成功读取 URL、大小、哈希见 SOURCE_MANIFEST.json 与 ADDITIONAL_SOURCE_MANIFEST.json。未成功的 LICENSE 路径另列 READ_FAILURES.json。静态检查/反例不是动态兼容性实验。

## 2. 最高优先级新增发现：固定 Unsloth wheel 是混合许可发行物

### 问题与原证据

旧增补只确认 PyPI 元数据：Unsloth 2026.9.12 声明 Apache-2.0，Zoo 2026.9.8 声明 LGPL-3.0-or-later。该观察正确，但不能替代实际文件级许可闭包。两版 PyPI 发行日期均为 2026-09-28。

官方固定来源：
- https://pypi.org/pypi/unsloth/2026.9.12/json
- https://pypi.org/pypi/unsloth-zoo/2026.9.8/json

已下载并本地验证：
- unsloth-2026.9.12-py3-none-any.whl：SHA256 0b0a8d5694c693ff7a5183b1df073a2b045f503193d76a0beec1696d1fef6013。
- unsloth_zoo-2026.9.8-py3-none-any.whl：SHA256 740aacbb70f6f735ef367905cd753d321b3088aaff404ebfb4f1cdf9f62e56e8。

### 文件级结果与反例

1. Unsloth dist-info/METADATA 第 8 行声明 Apache-2.0；dist-info/licenses/LICENSE 为 Apache2 文本，但同目录 COPYING 是 AGPL3。studio/LICENSE.AGPL-3.0 及 Studio 源文件头明确 AGPL-3.0-only。
2. Zoo METADATA 第 8 行声明 LGPL-3.0-or-later；licenses/LICENSE 为 LGPL3，COPYING 却为 AGPL3。不能简单用 COPYING 覆盖所有文件，也不能忽略它。
3. 更关键，AGPL 并不只在 Studio：unsloth_zoo/pad_token.py 第 1 行 SPDX 标为 AGPL-3.0-only，第 4 行同样如此，但第 6–7 行模板正文允许 version 3 或更晚，存在原文口径冲突，需要上游/法律审阅澄清。
4. 静态可达路径：Unsloth unsloth/models/_utils.py:144 导入 unsloth_zoo.tokenizer_utils；Zoo tokenizer_utils.py:611 导入 .pad_token。Unsloth tokenizer_utils.py:920 另有条件导入 fix_pad_token。因此“删去 Studio 即能保证训练链无 AGPL 文件”已有直接反例。
5. Unsloth 核心目录还发现 dataset_num_proc.py、models/_custom_dtype.py、models/fp8_to_nf4.py、models/grouped_linear_lora.py 等 AGPL 文件头。扫描归档内 Python 文件前 20 行，共找到 623 个含 AGPL 的文件头（包括大量 Studio/CLI 文件），详细记录在 AGPL_FILE_MAP.json。此数字不是完整许可分类数量，也不是实际运行模块数量。

提取许可原文/成员哈希见 sources/unsloth_wheel_members.json、sources/unsloth-zoo_wheel_members.json；训练相关导入证据见 sources/pad_token_import_evidence.json。只把这些作为文件许可及静态导入事实，不推定所有组件同一许可，不推定全部序境产品必须开源，也不凭解释器导入就作法律链接结论。

### 产品适配与下一步

保持 20B 目标，但在批准安装/交付训练镜像前必须明确：实际 wheel、用到的模块、修改内容、内部训练还是向客户分发、是否网络提供相关修改程序、应提供的许可/源码/通知材料。按实际构建物审阅，不能以模型权重 Apache2 替代运行库条款。若需上游澄清，先拟问题，未经许可不联系第三方。本研究未替换版本或规避许可证。

## 3. 可重建依赖：补到了范围，不应伪造精确版本

### 问题与原版本

main4dab/lumenis/system/ai_gateway/owned_training.py:510–515 固定 8 个 NF4 包；PEFT/datasets/safetensors 不在该常量。owned_training_checkpoints.py:46–49 的 14 包集合包含三者，:285–292 按批准摘要验证，:1249 读取运行版本。config/ai-owned-foundation.json:163、219 保留框架 lock SHA 220e8e688ce0fb05779c5f7f640476bf928c11e185e00c0552cb3cf8b3a6ea21。

本轮限定 main4dab 的 JSON/TXT/MD 检索只找到上述摘要，未得到三包精确版本原文。摘要不能反推出版本。既有 followup_training_libraries/version-evidence-search.json 空结果仅说明其限定范围没有发现，不代表历史环境从未记录。

### 新补官方发行约束

Zoo 固定 wheel METADATA:24 要求 peft>=0.18.0 且排除0.11.0；:32 对 datasets 给出 >=3.4.1,<5.0.0，并排除4.0.*、4.1.0、4.4.*、4.5.0。Unsloth 固定 wheel METADATA:36 则要求 datasets>=3.4.1,<4.4.0 并排除4.0.*、4.1.0。这是多个可选版本的约束交集，不是部署锁，也不是任取范围内版本已兼容。Unsloth 声明 Zoo>=2026.9.8，本产品才进一步锁具体 Zoo 版。

反例：同样满足范围的两个 datasets 版本可能具有不同 Arrow、map、缓存和传递依赖；pip 成功解析不能复现之前 checkpoint 的 framework_lock 摘要。即使版本字符串一致，本地补丁与 wheel 内容仍可能不同。

结论：普通训练依赖可重建性仍未闭合，但缺口已从“未知上游约束”缩小为“缺实际完整 lock/wheel/native identity”。下一步先取受控历史 checkpoint manifest 中的 framework_versions 原文或原环境锁/安装收据；随后逐版本核 PEFT target_parameters、datasets 行处理、safetensors 读写。未经授权不连接/修改环境，不选最新版填空，不把 CPU 统计栈替换进训练栈。

## 4. NF4 权重固定，不等于基座转换可重建

问题：已批准原基座 openai/gpt-oss-20b@6cee5e81ee83917806bbde320786a8fb61efebee 与 NF4 变体 @093fba6992ef5a7152481afec0bdfca1ac486998 是否能证明同一原始基座转换而来？

产品 config/ai-owned-foundation.json 明确标 NF4 base_revision_state=UPSTREAM_UNSPECIFIED。官方固定 NF4 模型卡 https://huggingface.co/unsloth/gpt-oss-20b-unsloth-bnb-4bit/blob/093fba6992ef5a7152481afec0bdfca1ac486998/README.md 第 2–4 行给 base_model 名称和 Apache2 元数据，但没有把基础 checkpoint commit 写成产品批准 SHA。本轮 LICENSE 固定路径404，不把模型卡声明冒充已获该仓库独立许可证全文。

静态反例：固定最终文件 hash 可验证“同一制成品”，却不能证明“从指定基础 commit + 指定量化工具/参数重建得相同制成品”。产品配置的文件 hash 是预期身份，不是本次下载权重后实算的结果。本轮没有权重，不能确认数值等价、量化误差或其上 LoRA 与原版可互换。

资源说明：配置所列原始三份权重约13.76GB十进制，NF4四份约12.53GB十进制；这是文件体积，不是 VRAM、反量化峰值、optimizer/KV/activation 或训练预算。保持原20B目标和设备门，不据体积推断16GB卡一定能训。

下一步：补发布方 conversion provenance（原 commit、量化脚本/依赖、dtype、排除模块、随机/确定性设置），再在批准资源上验证文件 hash、重载和同输入差分；若上游未公开则诚实保留不可完全重建，并由批准者决定是否接受该依赖风险。

## 5. Qwen3-TTS：新增声音能力的精确身份与环境冲突

### 来源版本

- 官方代码 commit 022e286b98fbec7e1e916cb940cdf532cd9f488e，提交时间2026-03-17，pyproject 声明 qwen-tts0.1.1。
- Base 权重候选 Qwen/Qwen3-TTS-12Hz-0.6B-Base@5d83992436eae1d760afd27aff78a71d676296fc，HF lastModified 2026-01-29。
- 独立声学 tokenizer Qwen/Qwen3-TTS-Tokenizer-12Hz@7dd38ad4e9bad454aae9cd937d0cd577604fe229，同日更新。
- 两模型卡均声明 Apache2；固定 LICENSE 路径均404，仓库 siblings 不含独立LICENSE。代码仓库有 Apache2全文。不能把这三层写成同一件已完整法律验收的资产；基础训练语料完整权利链亦未获得。

### 新的确定性反例：不能与20B配方原样共用一个环境

固定代码 pyproject.toml:22–24 要求 transformers==4.57.3 和 accelerate==1.12.0，而产品 NF4 固定 transformers==4.56.2。相同环境不可能同时满足两个精确等式。此为文本约束矛盾，无需安装即可确证；不说明模型本身无法并存于同一机器。应研究独立受控 runtime /进程边界及明确通信合同，不能偷偷升级原20B训练依赖。其余 gradio/librosa/torchaudio/soundfile/sox/onnxruntime/einops 多未精确锁定，CUDA/FlashAttention亦须分别锁。

### voice prompt 究竟是什么

固定 qwen_tts/inference/qwen3_tts_model.py:41–51 的 VoiceClonePromptItem 包括 ref_code、ref_spk_embedding、x_vector_only_mode、icl_mode、ref_text；:356–454 用声学tokenizer和说话人embedding生成这些内容；:614–626 生成后还使用参考code长度进行音频拼接/切分。

所以音色包不是一个任意向量或完整独立模型。Base 仓库本身包含 speech_tokenizer/ 子目录；独立Tokenizer仓库用于单独编码/训练数据准备，不能仅凭名称一致推断嵌套权重与独立repo字节相同。必须分别固定实际使用文件hash、采样率、codebook/tensor形状、tokenizer版本和主模型适配关系。

反例：仅导出 speaker embedding 不等价于带 ref_code/ref_text 的完整上下文克隆；传入另一 checkpoint 接受同shape也不保证同音色/文本对齐。官方复用内存中的 prompt_items 示例没有建立跨App长期序列化标准，更未证明 .voicenpc 与其等价。自定义安全容器应保存最小字段与版本，不直接反序列化不可信 pickle。

### 功能、数据与资源边界

官方 finetuning/README.md:1–9 在该固定版本只承诺单说话人微调，多说话人是未来功能；:12–30 要求audio、text、ref_audio，建议同一参考音频；:35–42 使用独立Tokenizer CUDA提取code。它不同于数秒参考条件克隆，不可将两者统称已训练个人完整模型。

语言集合仍为中英日韩德法俄葡西意，缺阿拉伯/印地/印尼；小模型/语音不替换20B文本目标。模型卡97ms是上游声明，未测本环境/手机/产品端到端首包、网络、打断和恢复，不能作为SLA。0.6B只给出参数量，不覆盖全部tokenizer/缓存/峰值内存。无声样、听测、训练数据、GPU实验，质量与耗时均未验。

产品适配：先明确播客离线成片与实时交互各自预算；外部手机录音+准确文本+授权可作为输入，私有音色包导入仍需格式样本和许可。实际安装、声音上传、训练与产品集成都须另获明确授权。

## 6. Claude Quickstarts：只补当前版本边界，不重复旧适配设计

本轮将官方main固定为9ec32b91df50b0d4906cae64b13c6298055ff40d（2026-10-07）。LICENSE为MIT，保留版权及许可文本要求；范围是源码/文档，不提供Claude权重，也不授权序境使用托管/API。https://github.com/anthropics/claude-quickstarts/tree/9ec32b91df50b0d4906cae64b13c6298055ff40d

README:3、7说明集合基于Claude API并要求API key；Managed Agents例子涉及session、vault、webhook、cron等托管语义。复制界面或调度片段不等于可以离线运行整项目。已有历史适配报告仍可复用，但它的旧SDK版本研究不能自动覆盖当前新增示例和锁文件。

本轮仅确认当前入口说明和根许可，未取得每示例精确传递依赖闭包，未调用服务。合法代码二改应先按批准文件范围建立NOTICE、逐文件/依赖许可，再由序境已有Gateway、Task、SourceUse和本地持久化合同替代云服务语义；这是一项待批准的实现，不是研究中已经完成。原20B继续承担其获准能力，不能把Quickstarts当作免费Claude能力。

## 7. 下一步验证顺序及停止边界

1. 最优先：审阅固定wheel混合许可与训练可达文件，明确实际安装/分发方案；任何许可裁决交给合格审阅者，不自动更换训练栈。
2. 找到现有framework_versions原文与相应wheel/native锁，才开展三包精确版本研究。没有原文就保持未知。
3. 冻结NF4转换溯源与最终权重验证计划，分别区分来源可重建和产物可复验。
4. 为TTS单独设计环境锁及音色条件数据合同；以用户授权的本人声样做中英韩专名、数字、长文本、首包/打断/取消、音色撤回验证。样本与模型、tokenizer身份全部绑定，真实运行需另批。
5. Quickstarts只移植获准的许可代码机制，不引入其API、托管、模型服务或自动外传。

停止条件：研究报告与可核原文完成；缺少真实环境/权重/声样/法律判断的项目标为未验，不以静态材料升级成“已商用可用”。本次未触发任何产品晋升、训练、权限授予或对外通信。
