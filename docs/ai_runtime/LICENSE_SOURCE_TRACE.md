# 本地 AI 与研究来源追踪

## Qwen2.5-Coder 1.5B Instruct

- 官方模型库：<https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct>
- 本轮核验版本：`2e1fd397ee46e1388853d2af2c993145b0f1098a`
- Ollama 标签：`qwen2.5-coder:1.5b-instruct`
- Ollama manifest：`d7372fd82851`
- 量化：`Q4_K_M`
- 本地权重 SHA-256：`29d8c98fa6b098e200069bfb88b9508dc3e85586d20cba59f8dda9a808165104`
- 模型与权重许可：Apache-2.0；`ollama show --license` 与官方模型仓库均已核验。
- 商业使用：Apache-2.0 允许，但发布时须遵守许可证与归属要求；本仓库不再分发权重。
- 数据集/资产：本集成不训练模型、不打包训练数据或上游资产；因此没有把上游数据集条款转授给序境。

## Qwen2.5-Coder 7B Agent Profile

本地已有，Apache-2.0 与 SHA-256 已登记。当前节点在真实调用时因可用内存不足而返回 `RESOURCE_LIMIT`，故状态是 `SHADOW`，不得作为本机默认模型。

## Ollama

- 官方 Runtime 文档：<https://docs.ollama.com/>
- 本机版本：0.7.0。
- 本仓库仅调用回环 HTTP API，不提交 Ollama 二进制、模型目录或缓存。

## 研究项目

版本、许可与“仅方法借鉴、不复制源码”的记录见 `autonomous_engineering_research/research_projects.json`。依赖许可只在未来实际引入依赖时重新核验；当前未引入三个研究项目的任何依赖。
