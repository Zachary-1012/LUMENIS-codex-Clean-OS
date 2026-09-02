# 广州太古汇舆情情报中心 v5.2 Windows 升级说明

## 这版的核心变化

1. **零 Key 本地 AI**：`AI_PROVIDER=<REDACTED> Ollama、LM Studio、llama.cpp；发现可用模型就直接接入。没有本地模型时自动使用内置 `Taikoo Local Intelligence`，系统不因没有 Key 停摆。
2. **历史库 AI/规则复核**：501 条旧笔记先经过主体硬过滤，再经过智能复核；不相关内容不删除，只标记为 `irrelevant` 并保留审计历史。
3. **公开互联网发现层**：Google News RSS、Bing News RSS、GDELT、自定义 RSS、微博/知乎/B站/抖音等平台的公开索引定向查询。它是“公开互联网发现”，不是承诺穷尽所有登录平台。
4. **反哺小红书**：公开来源提取事件词/品牌词，加入下一轮小红书搜索关键词。
5. **事件库**：新增 `event_mentions`、`web_sources`、`web_runs`、`note_review_history`，让事件、来源健康度、运行记录、历史复核都有底层数据。
6. **首页重构**：把长页面改成“现在最值得看 / 跨平台事件 / 情感结构 / 热议主题 / 全网发现 / 情报探索 / 高级模块”，详情采用抽屉式交互；鼠标悬停会显示名词解释和计算方式。

## 明天到公司：推荐运行流程

### A. 先不要删除原项目

把现有 `taikoo-monitor-clean` 整个文件夹复制一份，例如：

`taikoo-monitor-clean-v4.2-backup`

### B. 覆盖升级版文件

把 v5.2 压缩包里的项目文件覆盖到你原来的：

`D:\taikoo-monitor\taikoo-monitor-v4.2-remote-optimized\taikoo-monitor-clean`

如果系统提示是否覆盖，选择覆盖；**不要删除 `data\monitor.db`**。

### C. 打开 PowerShell

```powershell
cd D:\taikoo-monitor\taikoo-monitor-v4.2-remote-optimized\taikoo-monitor-clean
.\.venv\Scripts\Activate.ps1
```

### D. 先做系统测试

```powershell
python test_system.py
```

必须看到：

`ALL TESTS PASSED`

### E. 检查本机 AI

双击：

`check_local_ai.bat`

或者 PowerShell：

```powershell
python -c "import intelligence; print(intelligence.ai_status())"
```

如果电脑有 Ollama / LM Studio / llama.cpp，会自动显示对应 provider；没有也没关系，会显示 `local_rule`。

### F. 第一次升级先备份数据库

```powershell
python -c "import database as db; db.init_db(); print(db.backup_database('data/backups/pre-v51-upgrade.db'))"
```

### G. 对历史 501 条笔记进行重新复核

```powershell
python reprocess.py --limit 5000 --web-limit 0
```

这一步的原则：

- 不相关 → `irrelevant`
- 可疑 → `review`
- 有效 → `relevant`
- 正面 / 中性 / 负面重新判断
- 风险重新计算
- 负面摘要压缩成管理层短句
- 全部保留审计历史

### H. 启动系统

```powershell
python app.py --host 0.0.0.0 --port 8200
```

电脑访问：

`http://127.0.0.1:8200`

同一 Wi-Fi 手机访问：

`http://192.168.0.213:8200`

### I. 5G 远程访问

第一次：

```powershell
copy .env.example .env
notepad .env
```

至少修改：

```text
TAIKOO_AUTH_USER=admin
TAIKOO_AUTH_PASSWORD=<REDACTED>
```

然后双击：

`start_remote_5g.bat`

终端会出现：

`https://xxxx.trycloudflare.com`

手机关闭 Wi-Fi、使用 5G，打开该地址并输入认证账号密码即可。

## 日常使用

- **立即更新**：随时手动触发，不需要等待自动周期。
- **自动采集**：默认每 90 分钟一次；可以在 `.env` 中修改 `AUTO_INTERVAL_MINUTES`。
- **全网发现**：先跑公开互联网，再把事件关键词反馈给小红书。
- **历史复核**：首页“重新复核历史库”可再次运行。
- **备份**：升级或大量采集前先执行数据库备份。

## 本地 AI 的现实边界

如果电脑没有 Ollama / LM Studio / llama.cpp，系统仍然可以完成主体过滤、情感、风险、分类、摘要、去噪和事件聚合，但它属于**可审计本地智能引擎**，不是大语言模型。

如果以后安装免费本地模型，系统会自动接入，无需购买 API Key。推荐优先使用 Ollama；模型名称可在 `.env` 的 `OLLAMA_MODEL` 中指定，也可以留空让系统自动选择本机已有模型。
