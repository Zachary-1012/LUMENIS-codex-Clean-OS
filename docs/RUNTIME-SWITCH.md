# 采集运维控制面：Kill Switch + Dry-run · 2026-09-03

> 研究来源：**baldurhq/baldur** System-Control（Apache-2.0）。
> 范式：instant kill switch（全局 on/off，翻转带 reason 可问责，持久化跨重启，fail-safe）
> + dry-run 观察/演练模式（正常评估但不行动，离开需 confirm）。

## 一、为什么

生产采集遭遇风控/登录失效时，自动化重试可能加剧事态。运维需要一个"大红按钮"：
**立即停所有采集自动化，不重启不改配置**；以及一个演练开关：**dry-run 下完整评估熔断/调度
决策但不发任何真实请求**（上真实流量前的试飞）。

## 二、模块

| 文件 | 说明 |
|---|---|
| collector_guard/runtime_switch.py | RuntimeSwitch：enabled/disabled x dry_run；持久化+审计+fail-safe；get_switch() 单例 |
| tests/test_runtime_switch.py | 8 测试（默认/禁用必填reason/启用需confirm/dry-run开关/跨重启保持/fail-safe/审计轨迹） |
| scripts/runtime_switch_ops.py | CLI：status/disable/enable/dry-run/audit |
| 数据 | data/runtime-switch.json + data/runtime-switch-audit.jsonl（gitignore） |

## 三、CLI

python scripts/runtime_switch_ops.py status
python scripts/runtime_switch_ops.py disable "风控熔断处置"
python scripts/runtime_switch_ops.py enable
python scripts/runtime_switch_ops.py dry-run on | off
python scripts/runtime_switch_ops.py audit

## 四、程序化接线（collector 真实行动前检查）

from collector_guard.runtime_switch import get_switch
sw = get_switch()
if sw.is_enabled() and not sw.is_dry_run():
    result = search_xiaohongshu(kw, ...)   # 才真正发起采集请求
else:
    # disabled：不发请求（运维总闸）；dry_run：演练，记录 would-have 决策
    log("would-have collect", kw, state=sw.status()["state"])

## 五、与现有体系的关系（不重复）

| 层 | 触发方 | 语义 |
|---|---|---|
| 用户暂停 collect-pause/resume | 用户 | 单平台手动暂停（恢复需用户 resume） |
| CollectorGuard / RiskEngine / ResourceGuard | 自动化 | 熔断/冷却/冻结（自动恢复） |
| RuntimeSwitch Kill Switch | 运维 | 全局总闸，覆盖自动化，disable 立即生效且跨重启保持 |
| RuntimeSwitch Dry-run | 运维 | 演练：评估全开、动作全抑制 |

## 六、验证

- 单测 8/8 过（含跨重启保持 disabled、fail-safe、审计轨迹）
- 全量回归 EXIT=0
- Evidence：staging/baseline-evidence/、git commit、OSAI learning-feed
