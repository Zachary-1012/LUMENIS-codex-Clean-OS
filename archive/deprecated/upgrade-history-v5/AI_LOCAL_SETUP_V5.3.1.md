# v5.3.1 本地 AI 接入说明

系统不要求购买 API Key 才能运行。

自动检测顺序：
1. Ollama
2. LM Studio
3. llama.cpp
4. 若未来配置云端 Key，可接入 Qwen / OpenAI / DeepSeek
5. 全部不可用时，使用内置本地规则引擎

“自动接入”指自动发现本机已经运行的本地 AI 服务并调用；不会未经允许自动安装、下载模型或启动第三方程序。

网页入口：系统设置 → 智能引擎

可看到当前引擎、模型、运行状态，并使用“重新检测”“测试 AI 接口”。

后端接口：
- GET `/api/ai/status`
- POST `/api/ai/test`

推荐环境变量：
`AI_PROVIDER=auto`

未来若使用云端 Key，只放 `.env`，不要写入前端代码。
