# 广州太古汇·舆情监测系统 v5.3.1
## Windows 明日到公司升级说明

> 在已跑通的 v5.3.0 基础上升级，不重建数据库、不删除历史笔记、不重新安装 Python / Node / Chromium。

### 1. 进入原目录
```powershell
cd D:\taikoo-monitor\taikoo-monitor-v4.2-remote-optimized\taikoo-monitor-clean
```

### 2. 关闭 v5.3.0
若 PowerShell 显示 `Press CTRL+C to quit`，按 `Ctrl + C`。

### 3. 激活现有环境
```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. 先备份数据库
```powershell
python -c "import database as db; print(db.backup_database('data\\backups\\before-v5.3.1.db'))"
```

### 5. 覆盖 v5.3.1 代码
将压缩包内项目文件复制到原 `taikoo-monitor-clean`，允许覆盖同名代码文件。

必须保留原来的：
- `data\monitor.db`
- `data\backups\`
- `.venv\`
- `.env`

**不要把新包里的 data 文件复制回公司电脑。**

### 6. 不要重新安装环境
你已经确认 Python 3.13.15、pip 26.2.1、Node v26.7.0、npm 11.19.0、Playwright Chromium 均正常。不要因为 npm 新版本提示而升级。

### 7. 回归测试
```powershell
python test_system.py
node --check static\js\app.js
python -m py_compile app.py database.py ai_analyzer.py intelligence.py reprocess.py web_monitor.py
```
第一条必须出现：`ALL TESTS PASSED`。

### 8. 启动
```powershell
python app.py --host 0.0.0.0
```
打开：`http://127.0.0.1:8200`

### 9. AI 接口验证
进入 `系统设置 → 智能引擎`，点击“重新检测”，再点“测试 AI 接口”。

如果本机运行 Ollama / LM Studio / llama.cpp，会显示对应 provider 与模型；如果没有，则显示“本地规则引擎”，这也是正常状态。

### 10. 历史库 AI 复核
网页正常后，点击顶部“AI 分析”。系统重新进行：主体校验 → 去伪存真/无关筛除 → 正负面判断 → 风险判断 → 摘要/事件提示 → 审计留痕。

原始笔记不直接物理删除。

### 11. 全网发现
v5.3.1 默认 Adapter：Google News RSS、GDELT、自定义 RSS。它们只是底层发现层，不改变“小红书为主平台”。发现到的事件词会反哺下一轮小红书搜索。

### 12. 5G
项目提供 `start_remote_5g.bat`。v5.3.1 会在启动 Cloudflare 前检查 Basic Auth。

`.env` 至少配置：
```env
TAIKOO_AUTH_USER=admin
TAIKOO_AUTH_PASSWORD=<REDACTED>
TAIKOO_HOST=127.0.0.1
TAIKOO_PORT=8200
AUTO_INTERVAL_MINUTES=90
AI_PROVIDER=<REDACTED>
```

双击 `start_remote_5g.bat`，看到 `https://xxxxx.trycloudflare.com` 后，手机关闭 Wi-Fi、切换 5G 打开。

### 13. 日常
默认约每 90 分钟自动更新；需要立即查看时点击顶部“采集数据”。

### 14. 禁止操作
不要删除 `data\monitor.db`、`.venv` 或 `.env`；不要重新 seed 历史数据；不要无故重装 Chromium / Python / Node。
