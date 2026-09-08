# Delete Manifest

状态：审计清单；本轮无已执行删除。

| File / Group | Reason | Reference Check | Runtime Check | Test Result | Decision |
|---|---|---|---|---|---|
| 重复 Report / Evidence / Case / Browser / Health 实现 | 可能存在多套实现 | 未完成全量图谱 | 未完成 | 未执行 | KEEP |
| 旧 CSS 类（zbc-* / ld-* / lumenis-* / zbip-*） | 可能仍被模板或运行时引用 | 未完成 | 未完成 | 未执行 | KEEP |
| evaluation / launch / data-center / xiaohongshu / workspace 页面 | 路由存在但导航归属待确认 | 已知有路由引用 | 未完成 | 未执行 | KEEP |
| audit/、backup/、docs/legacy/ 资料 | 可能包含迁移证据与回滚材料 | 未完成 | 不适用 | 未执行 | KEEP |
| `frontend/templates/base.html` 中 BMP “传播声量”导航项 | 与 KOS/KOL/KOC 使用同一 endpoint 与 active_nav，重复入口 | 已核对模板与 `lumenis.zbmp_kos` | 仅移除导航项，生产路由保留 | 目标回归通过 | REMOVED |

任何条目只有在五项证据全部通过后，才可改为 `DELETE` 或 `MIGRATE`。
