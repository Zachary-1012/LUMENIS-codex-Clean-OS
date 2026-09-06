# ADR-0001: Hub 不创建 Dev Container

## 状态
Accepted (2026-08-31)

## 上下文
DDC 已有完整的 Dev Container（Node 20 + Python 3.12 + SQLite + ReportLab），作为三仓库共享的验证运行时。Hub 作为纯 Python 研究中枢，是否需要自己的 Dev Container？

## 决策
**Hub 当前不创建 Dev Container。**

## 理由
1. Hub 是纯 Python 项目，CI 使用 `actions/setup-python@v5` 即可覆盖测试
2. DDC 已是验证运行时 Owner，Hub 不需要建立独立的可复现环境
3. 添加 Dev Container 增加维护成本（镜像更新、feature 跟踪），而收益有限
4. Hub 没有本地开发环境一致性的强需求（研究代码不依赖系统级库）
5. 避免"为了智能化而复杂化"

## 后果
- Hub 本地开发依赖开发者自行安装 Python 3.12+
- CI 是唯一的权威验证环境
- 未来如果 Hub 需要系统级依赖或多语言支持，重新评估此决策

## 参考
- CASE-2026-0011: Dev Container 可复现验证环境研究
- DDC `.devcontainer/devcontainer.json` (commit 878ebbf)
