# 豆包 × GitHub 定时升级协议

## 目标

豆包/本地开发环境完成一次本地任务后，以及按固定周期运行升级检查：

```text
本地任务完成
  ↓
python scripts/github_upgrade_check.py
  ↓
比较本地 HEAD 与 GitHub main
  ↓
无更新 → 不修改源码
有更新 → 生成 .runtime/github_upgrade_task.md
  ↓
豆包读取升级任务
  ↓
审计 GitHub 变更
  ↓
审计本地实际源码
  ↓
兼容性分析
  ↓
最小补丁
  ↓
测试/回归
  ↓
通过后提交 Git
```

## 推荐 Windows 定时任务

建议使用 Windows Task Scheduler 每 60 分钟运行一次；本地正在进行大规模修改时可以暂停该任务。

程序入口：

```bat
cd /d C:\你的项目目录
python scripts\github_upgrade_check.py --repo-dir .
```

不要把 Cookie、Session、代理认证、API Key 写入任务文件或提交 Git。

## 豆包执行规则

豆包每次看到 `upgrade_available` 后必须：

1. 获取 GitHub 最新提交/变更。
2. 对照本地真实源码，而不是只看文档。
3. 先审计，再修改。
4. 先旁路，再切换。
5. 保留生产数据库和历史数据。
6. 保留广州太古汇主体过滤口径。
7. 小红书优先，抖音第二，其他五个平台只保持扩展接口。
8. 不复制 MediaCrawler 受限许可证实现。
9. 不绕过验证码、安全验证、IP 风控或访问控制。
10. 测试失败不得提交“看起来能运行”的版本。
11. 每次升级记录：变更、原因、测试、风险、回滚方法。

## 版本同步原则

GitHub 是协作基线，不是自动覆盖本地生产环境的命令源。任何远程更新必须经过本地源码审计和回归测试后才能合并。
