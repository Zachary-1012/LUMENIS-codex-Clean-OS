# ZBMP — Z-Brand Monitoring Platform

## 项目状态：预留占位

本目录为 **Z-品牌舆情监控系统（ZBMP）** 预留目录，当前版本无业务实现。

## 预留内容

- 路由入口：`/zbrand/`
- 数据库：`zbrand.db`（独立隔离，不与太古汇数据混用）
- 多品牌管理框架
- 品牌监控配置模板

## 升级路径

1. **CTH-POMS V4.0 稳定运行后**，再启动ZBMP开发
2. ZBMP复用V4的认证体系、采集适配器框架、外部导入模块
3. 核心差异：多品牌切换、品牌维度数据隔离、品牌对比分析

## 约束

- 严禁将ZBMP需求混入CTH-POMS太古汇业务逻辑
- LOCK保护的太古汇核心函数（SUBJECT_WORDS/subject_hit/aggregate_events/build_daily_report）不得修改
- ZBMP开发前需单独评估架构和数据模型

## 预计启动时间

CTH-POMS P0/P1全部完成后（约2-3周后）
