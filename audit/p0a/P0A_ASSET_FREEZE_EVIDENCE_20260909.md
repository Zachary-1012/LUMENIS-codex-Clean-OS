# LUMENIS P0-A 资产冻结证据

状态：`TECHNICAL FREEZE PASS / BASELINE DECISION PENDING`

生成时间：2026-09-09 13:44（Asia/Shanghai）

## 1. 冻结包

- 仓库外目录：`D:\LUMENIS_REBUILD\P0A_BASELINE_20260909_1040`
- 完整 Manifest：`P0A_FULL_ASSET_MANIFEST.json`
- 校验文件：`SHA256SUMS.txt`
- 总大小：95,364,434 bytes
- 数据库备份：11
- 校验条目：12
- SHA-256 复核失败：0
- SQLite sidecar：0

完整 Manifest 与数据库副本禁止加入 Git；Git 只保存生成器、资产定义和本脱敏摘要。

## 2. 源码与 Runtime 资产

| 资产 | HEAD | Git tree | 文件数 | 状态条目 | 文件系统摘要 |
|---|---|---|---:|---:|---|
| clean-core | `f57a45c4b9a95483d7408a7dbe59a75699bb35ee` | `401f70584bdf736a911a5e436bfd64dc549ba5ab` | 3,769 | 3 | `7a2c5739ce18980110cf3d31ddef7ab7bcf844c5b71bfa29cc80b7987c32c7e5` |
| original-workspace | `6f0c9f4fa55c7ca1ea2793e6d66c8ff79ff330dd` | `78b3f5e399bb3ea23a5da75e0ec0722d045ee930` | 25,574 | 2,824 | `fd1c3e6870d0deb3360a952bee9714d08355b53c1ab6a94bbaceb431f6e16a10` |
| runtime-8202-source | `b6b52b55511704d3f25e371fee48c0d6769e0422` | `fa4149b89d15747eb94a5a3f02818cc24f0b5697` | 5,817 | 0 | `c7afc51826406ff7c588cd871c35f411af04c86c0954421076e17ec414c27fb1` |
| runtime-8201-source | `fda599abf5e35aecebe3ff37b0e66060e68c3017` | `db3af8edf316e2e38e320bb3ec735c425c5f2171` | 20,524 | 0 | `68f18c58f5ff7a84b303436315406fe6d1287ce0409529aa7805a2869081b5e9` |
| portable-20260908 | 非 Git | 非 Git | 3,808 | 0 | `47de208e84264ae1992612df8f5bd72f5595bc710d0fb3d12fbea79c17400861` |
| portable-current | 非 Git | 非 Git | 2,077 | 0 | `9b0304d09fcedee63687d886de06bf95d1554c879db6395839295e8e6dc0b361` |

冻结时端口事实：8201、8202、9222 正在监听；11434 未监听。Manifest 保存关联进程、命令行、创建时间和端口，不保存凭据值。

## 3. 数据库摘要

| 候选数据库 | 表 | FK 违规 | Integrity | 恢复副本 |
|---|---:|---:|---|---|
| clean-core `data/monitor.db` | 63 | 7 | ok | PASS |
| original `data/monitor.db` | 129 | 43 | ok | PASS |
| original `backend/data/monitor.db` | 63 | 0 | ok | PASS |
| runtime-8202 `data/monitor.db` | 62 | 0 | ok | PASS |
| runtime-8201 `data/monitor.db` | 128 | 35 | ok | PASS |
| runtime-8201 `staging/monitor.staging.db` | 128 | 35 | ok | PASS |
| runtime-8201 `data/_old_staging_ref.db` | 52 | 0 | ok | PASS |
| portable-20260908 两库 | 1 / 1 | 0 / 0 | ok | PASS |
| portable-current 两库 | 1 / 32 | 0 / 0 | ok | PASS |

活动数据库的源文件 SHA-256 与在线备份 SHA-256 可以不同：SQLite online backup 得到一致性快照，而源 Runtime 可能在摘要与备份间继续提交事务。每个副本均单独通过 `PRAGMA integrity_check`，其摘要记录在仓库外 Manifest。

## 4. 恢复方法

1. 停止目标 Runtime，禁止在运行中覆盖数据库。
2. 对目标当前数据库再次取只读摘要与备份。
3. 从 `SHA256SUMS.txt` 验证选定副本。
4. 在隔离路径恢复并执行 integrity、FK、schema、关键表数量和业务抽样。
5. 只有人工批准后才允许切换目标路径；失败则恢复切换前副本。

## 5. 测试

- `tests/test_p0_asset_freeze.py`：3 passed。
- 覆盖只读摘要、SQLite online backup、源文件不变、配置只记录键名、禁止把输出写入仓库。
- 线程泄漏：0。

## 6. 当前限制

- 原工作区的大量 ignored / untracked Runtime 资产导致文件数显著高于 Git tracked 数；不能以 Git clean 判断 Runtime clean。
- P0-A 的技术冻结已通过，但 Baseline Source / Data 的人工决策尚未批准。
- 在批准前，P0-B 不得执行 Runtime 切换；本地 AI 增补只能在独立分支和 Shadow 数据域内实施。
