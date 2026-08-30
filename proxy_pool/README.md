# ProxyPool 可插拔代理池 v1.0

独立、可插拔、默认关闭的网络出口管理层。**只做合法出口管理 / 健康检查 / 故障切换**，不实现验证码绕过、指纹伪装、风控/封禁绕过。可整目录删除而不影响主系统启动。

## 1. 设计边界（硬约束）
- 默认 `PROXY_POOL_ENABLED=false`：关闭时系统行为与无代理版本完全一致。
- 不修改主体词口径（SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit / _subject_sql_and_values / aggregate_events / build_daily_report），不改数据库表结构。
- 代理异常 → 节点冷却 → 切换其他健康节点 → 仍不可用时按平台策略决定是否直连，**绝不让舆情主系统崩溃**。
- 敏感信息（VLESS UUID、Reality 密钥、账号密码）一律不进源码，只通过本机 v2rayN/Xray 端口或 `.env` 注入。
- GitHub 免费公开节点只能**人工审核后**写入 `config/proxy_nodes.json`，本模块不自动抓取未知节点，不把 Cookie/登录态交给未知代理。

## 2. 分层关系
```
采集器 → ProxyPool → 127.0.0.1:本地端口 → v2rayN/Xray → 付费 VLESS → 互联网
```
ProxyPool 不需要知道 UUID/密钥，只对接 v2rayN 暴露的本地 HTTP/SOCKS 端口。

## 3. 安装 / 开启
1. 依赖仅 `requests`（主系统已装），无需新增。
2. 在 `.env` 增加（不写进源码、不提交）：
   ```
   PROXY_POOL_ENABLED=true
   PROXY_POOL_MODE=local
   # v2rayN 参数设置→核心：本地 HTTP / SOCKS 监听端口，按实际填
   PROXY_HTTP=http://127.0.0.1:10809
   PROXY_SOCKS=socks5h://127.0.0.1:10808
   # 可选：健康检查地址 / 超时 / 冷却
   PROXY_HEALTHCHECK_URL=https://www.gstatic.com/generate_204
   PROXY_HEALTHCHECK_TIMEOUT=8
   PROXY_COOLDOWN_SECONDS=300
   PROXY_ALLOW_DIRECT_FALLBACK=true
   ```
   现有 `GOOGLE_PROXY` / `OPENAI_PROXY` 也会被自动识别为本机节点（向后兼容）。
3. 启动时加载（Flask 初始化处，已在 app.py 接线）：
   ```python
   from proxy_pool.loader import load_proxy_nodes
   load_proxy_nodes()
   ```

## 4. 增加节点
复制 `config/proxy_nodes.example.json` 为 `config/proxy_nodes.json`，按模板添加；`platform` 支持 general/xhs/weibo/bilibili/instagram/google/github。`proxy_nodes.json` 含真实节点，已加入 .gitignore，不提交。

## 5. 检查节点 / 状态
- `GET /api/proxy/status`：节点健康、延迟、成功/失败、是否冷却（URL 做脱敏）。
- `POST /api/proxy/check`：对全部节点立即做一次健康检查。

## 6. 采集器怎么接（渐进，不重写采集器）
```python
from proxy_pool import safe_request, create_session
# 普通平台：代理失败可回退直连
resp = safe_request("GET", url, platform="weibo", timeout=30, headers=headers)
# 强制出海平台：不允许悄悄漏到直连，失败即抛错并冷却节点
resp = safe_request("GET", url, platform="instagram", allow_direct=False, timeout=30)
# 或用会话
sess = create_session(platform="google")
```

## 7. 关闭 / 恢复原系统
`.env` 设 `PROXY_POOL_ENABLED=false`（或直接删除该变量）重启即可，系统等同直连原版；整目录删除也不影响启动。

## 8. 选路与冷却规则
- 评分：优先级 > 成功率 > 低延迟；连续失败进入冷却（默认 300s），期间跳过该节点。
- 冷启动：无已验证健康节点时，允许未知节点试一次，成功即转健康，避免永远无法首验。
- 是否回退直连由总闸 `PROXY_ALLOW_DIRECT_FALLBACK` 与调用处 `allow_direct` 共同决定；出海平台默认收紧。
