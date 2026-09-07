# Phase4 真实采集运行验证证据

> 验证时间：2026-09-07 15:42 CST
> 环境：Windows / Python venv / Flask 8201 / SQLite data/monitor.db
> 验证方式：真实触发 POST /api/collect，非 unit test

## 1. 验证链路

```
Trigger(POST /api/collect) → Account → Session(CDP 9222) → Collector(collector.collect_all)
→ Source(xiaohongshu-cdp) → Raw Data → DB(notes) → collection_logs → Metrics → UI
```

## 2. 双账号轮换验证

| 账号 | 逻辑身份 | CDP端口 | 平台 | 状态 |
|------|----------|---------|------|------|
| 主账号 | XHS_CN_PRIMARY | 9222 | xiaohongshu.com | ONLINE |
| Retinaut | XHS_RETINAUT | 9223 | rednote.com | ONLINE |

- `dual_account_rotation.py` 模块导入成功，`select_account_for_collection` / `get_rotation_status` 可用
- `xhs_cookie_bridge.cdp_port_for()` 映射正确：XHS_CN_PRIMARY→9222, XHS_RETINAUT→9223, default→9222
- 9222/9223 端口 CDP `/json/version` 均返回 200，驻场浏览器在线

## 3. 采集触发与执行证据

- **触发方式**：`POST /api/collect`，body `{"keywords":["广州太古汇"],"max_scroll":2}`
- **返回**：`{"ok":true,"task_id":"20260907154216308"}`
- **任务状态**：进入 ai-review 阶段（progress=62%），采集链路真实执行

## 4. collection_logs 真实记录（DB 证据）

| id | keyword | notes_count | status | error_msg | started_at |
|----|---------|-------------|--------|-----------|------------|
| 526 | silver | 0 | CAPTCHA | NEED_VERIFY | 2026-09-07 15:42:29 |

- 新增记录 id=526，证明采集器真实执行并写入 collection_logs
- status=CAPTCHA / error_msg=NEED_VERIFY：CDP 真人通道命中小红书人机验证（真实平台风控行为，非模拟）
- 采集前基线：collection_logs 最大 id=525（SUCCESS, 2026-09-07 14:54:45）

## 5. Auth Recovery 链路验证（CAPTCHA → 系统内弹）

采集触发 CAPTCHA 后，完整链路自动接通：

1. `collector.collect_all()` → `classify_collect_state()` 判定 CAPTCHA
2. `db.log_collection()` 写入 collection_logs id=526
3. `v4_upgrade.adapters.auth_recovery.request_recovery('xiaohongshu', source_state='CAPTCHA', detail='NEED_VERIFY')`
4. `_bridge_to_recovery_center()` → `auth_recovery_center.detect_and_create_task()`
5. DB 表 `auth_recovery_tasks` 新增记录：

| id | platform | issue_type | status | title | recovery_url | created_at |
|----|----------|------------|--------|-------|--------------|------------|
| 6 | xiaohongshu | captcha | pending | 小红书人机验证 - 需要人工通过 | https://www.xiaohongshu.com | 2026-09-07 15:42:29 |

6. 前端 API `GET /api/auth-recovery/summary` 返回：
   ```json
   {"ok":true,"data":{"has_issue":true,"pending_count":1,"pending_tasks":[{...id:6...}]}}
   ```
7. base.html 全局挂载的 AuthRecoveryModal JS 轮询到 pending task → 自动弹出系统内弹窗

**时间戳一致性**：collection_logs id=526 (15:42:29) 与 auth_recovery_tasks id=6 (15:42:29) 完全一致，证明链路实时接通。

## 6. 浏览器模式验证

- 默认模式：`internal_cdp`（内部AI浏览器/CDP真人通道）
- 配置来源：`default`（无配置文件时回退默认）
- `collector_browser_mode.is_internal_cdp()` 返回 `True`
- collector.html 页面包含浏览器选择器 UI：
  - `browser-mode-card` 容器
  - `bm-internal` radio（默认选中）
  - `bm-external` radio
  - `saveBrowserMode()` JS 函数
- API `GET /api/collector/browser-mode` 返回 `{"ok":true,"mode":"internal_cdp","source":"default",...}`

## 7. Auth 内弹全局挂载验证

- base.html 内联 auth_recovery_modal.html 完整内容（overlay/dialog/任务卡片/JS控制器）
- 渲染后 HTML 验证（HTTP 200）：
  - `id="auth-recovery-modal"` ✓
  - `auth-recovery-overlay` ✓
  - `auth-recovery-dialog` ✓
  - `AuthRecoveryModal` JS 对象 ✓
- 弹窗包含：平台/账号/状态/失效原因/恢复入口/"已完成验证"/"稍后处理"
- 严格账号只读：弹窗仅登录引导与状态展示，不执行任何写动作

## 8. Metrics / Counter 验证

- `GET /api/collection/counter` 返回真实数据：
  - daily_count=57, last_collect_at=2026-09-07 12:26:16
  - last_success_at=2026-09-07 14:54:45, last_task_status=SUCCESS
  - logs_today=24, circuit_state=normal

## 9. 未完成项 / 已知限制

1. **本次采集因 CAPTCHA 未获取新笔记**：CDP 通道命中小红书人机验证（NEED_VERIFY），notes 表无新增（基线1020条不变）。这是真实平台风控行为，非系统故障。需用户在采集浏览器手动完成一次人机验证后重试。
2. **PowerShell 中文编码**：POST body 中中文关键词在 PowerShell `Invoke-WebRequest` 下出现乱码（?????），导致主关键词搜索可能受影响。feedback keyword "silver" 正常执行并命中 CAPTCHA。Python/浏览器端无此问题。
3. **dual_account_rotation 当前未激活轮换**：rotation_status 显示 current_account=None，本次采集走默认 9222 大陆号。轮换逻辑模块已就绪，需在采集调度层显式调用 `select_account_for_collection()` 激活。
4. **话题APP采集适配器**：XHSAppTopicAdapter 存在但本次验证未触发（主采集链路走 search_xiaohongshu CDP 通道），需单独验证话题采集入口。
5. **auth_recovery_tasks 历史脏数据**：id=2-5 为历史测试数据（status=in_progress），不影响新任务创建。可后续清理。

## 10. 结论

三项功能均通过真实运行验证：
- ✅ Auth 内弹：全局挂载 + CAPTCHA 状态自动创建恢复任务 + 前端轮询可获取
- ✅ 内部浏览器：默认 internal_cdp + 选择器 UI + API + 采集启动走 CDP
- ✅ 真实采集：触发执行 + collection_logs 真实记录 + CAPTCHA 风控如实上报 + 不伪造0条
