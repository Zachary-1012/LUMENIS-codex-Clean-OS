# 本轮生产收敛证据（2026-09-13）

仓库：Zachary-1012/LUMENIS-codex-Clean-OS。
工作目录：D:/LUMENIS_REBUILD/LUMENIS-codex-Clean-OS。
分支：codex/production-convergence；开始 HEAD：1344fb4。
远端 main 核验为 516fb68。接手时本地 ac39791、1344fb4 及未提交运行时/E2E 工作均保留。

## 已验证

- CI：语法、pytest、HIGH/CRITICAL 边界检查恢复阻断；测试依赖显式安装。远端 CI 尚未验收。
- Python 3.11 AST：1075 个 tracked Python 文件，0 错误；检查不生成字节码。
- 数据库隔离、AI intent 权限、Experience 样板测试联合运行通过（41 项）。
- 候选库 Flask Blueprint 集成：5 项通过，覆盖 44 屏接口、38 个 runtime binding、外部指标 NULL、真实权限门、源库 SHA 不变。它不是整机 supervisor 或浏览器 E2E 验收。
- 新增资产准入和并发注册回归：2 项通过。准入要求 FACT/VERIFIED 且 ADMITTED；PENDING、CONCEPT、CANDIDATE、NULL 不作为生产知识。
- 边界检查 HIGH 从 2 降到 0；剩余 MEDIUM 8、INFO 11。OSAI 未指定，因此跨仓检查覆盖不完整。
- 启动依赖检查使用现有 D:/Taikoo-monitor-new/.venv/Scripts/python.exe 返回 OK。
- 启动脚本根路径改为脚本所在仓库；未运行生产启动脚本，未部署。

## 修复与复核

懒加载注册表在成功导入后才发布完成状态，并用锁保护；失败可重试。
候选 E2E 初次失败原因是 conftest 的内存权限 bypass；测试现在显式关闭内存及环境旁路，重跑通过。
智谱本轮唯一一次 OpenCode 探针失败（Unexpected server error），未重试。
OpenCode/Ollama 7B 只读任务无及时输出，已终止；Ollama 1.5B 真实调用返回复核意见。
本地模型意见只作参考：关于 RLock 同线程死锁及 with 未释放的泛化说法未采纳；以并发/失败重试测试为证据。

## 未验收

整机生产启动、监督器恢复、真实浏览器关键 E2E、全量遗留测试分类、全屏状态回归及全仓安全/恢复仍未完成。
4 个缺源屏与 2 个 N/A 的既有状态未在本轮扩展。
本轮没有迁移、删除或修改生产数据库；测试使用临时库或候选库副本。

PRODUCTION_READY = NO
