# 本地运行 / Local runtime

本目录仅保留历史名称对应的本地启动包装，统一调用 `../start_local.bat` → `scripts/start_production.ps1`。当前没有临时公网演示入口；外部部署须另行批准。

Local wrappers use the canonical production launcher. Temporary public access is unavailable; deployment requires separate approval.

로컬 실행은 기존 정식 시작 스크립트를 사용합니다. 임시 공개 접속은 제공되지 않으며 외부 배포에는 별도 승인이 필요합니다.

运行状态、来源状态、AI可用性和业务结果分别核验；不得把健康检查视为产品验收。数据库操作仅沿现有授权的备份/恢复入口，禁止删除或重建真实数据。
