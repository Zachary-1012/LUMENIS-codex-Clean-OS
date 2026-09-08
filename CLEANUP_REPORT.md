# LUMENIS Cleanup Report

审计状态：进行中；本轮未执行大规模删除。

## Removed

- `frontend/templates/base.html` 中 BMP 重复的“传播声量”导航项已移除；“KOS/KOL/KOC”入口保留，生产 endpoint 未删除。
- 其余当前工作树删除/新增未纳入本轮清理。

## Deprecated / Candidate

- 重复的 Report / Evidence / Case / Browser / Health 实现：先做 import、route、runtime、template、test 图谱，再标记 deprecated。
- 旧 CSS 类名与孤立样式：先保留，只有 0 import、0 runtime、0 template、0 build、0 test 才可删除。
- evaluation、launch、data-center、xiaohongshu、workspace：页面存在不等于导航入口，需通过路由与权限证据决定归属。

## Migrated

无。本轮只建立骨架和设计系统基线，未切换生产实现。

## Kept

Backend、Database、API、Collector、Evidence、Runtime、AI Gateway、权限边界、主体过滤、时间口径和既有测试全部保留。

## Gate

每次删除必须先更新 `DELETE_MANIFEST.md`，完成依赖、运行时和回归检查，并保留可回滚 Git SHA。
