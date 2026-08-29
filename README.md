# Z-Brand Core

> 品牌舆情监控与传播中台，内含两条产品线：
> - **CTH-POMS**（CorTech Lab·GuangZhou Taikoo Hui Public Opinion Monitoring System）——广州太古汇舆情监测与品牌传播系统（当前主力交付）
> - **ZBMP**（Z-Brand Monitoring Platform）——Z 品牌舆情监控系统（多品牌母平台，预留）
>
> 规划目录：`docs/`（architecture / learning / deployment）、`ai/`（api / web / ollama / gateway）。

## 产品一：广州太古汇舆情监测系统（CTH-POMS）

## 项目简介

广州太古汇小红书舆情监测系统，基于小红书真实数据采集，提供舆情监测、AI分析、风险预警、事件聚合、日报周报生成等功能。

**版本**: v5.7.0
**最后更新**: 2026-08-28

---

## 核心功能

### 1. 数据采集
- ✅ 小红书/Rednote真实数据采集（CDP + Cookie）
- ✅ 搜索发现 → 详情补全 → 评论采集
- ✅ 每日12次采集限制（手动3次 + 自动9次）
- ✅ 智能调度（8:00-23:00每2小时一次）
- ✅ 广州太古汇主体过滤（排除其他城市太古汇）
- ✅ 新账号保护（前3次极轻量模式）
- ✅ 微博全网采集（可选，不占用小红书次数）

### 2. AI分析
- ✅ 情感分析（正面/中性/负面）
- ✅ 风险等级（低/中/高）
- ✅ 关键词提取
- ✅ 业态分类
- ✅ 本地AI（Ollama）+ 云端AI双模式
- ✅ 豆包/GPT/Trae多AI提供商支持

### 3. 风险预警
- ✅ 实时监测高风险舆情
- ✅ 舆情影响上升速度过快自动预警
- ✅ 弹窗通知 + 红点标记
- ✅ 已读红点可消除
- ✅ 负面舆情二次确认机制

### 4. 事件聚合
- ✅ 自动聚合相关笔记为事件
- ✅ 事件紧急/一般分类
- ✅ 事件溯源分析

### 5. 报告导出
- ✅ 日报/周报/月报/年报
- ✅ Word/Excel/CSV格式
- ✅ 精确时间维度（自然周/月/年）
- ✅ 按太古汇汇报模板导出

### 6. 品牌业态监测
- ✅ 198个场内品牌（官方零售清单2026.08.20）
- ✅ 8大业态分类
- ✅ 品牌维度舆情统计
- ✅ 品牌风险等级评估

### 7. 智能助手 Zachary
- ✅ 3D质感浮动AI助手
- ✅ 黑色球体外形，液晶面部
- ✅ 荧光白/荧光蓝表情随机切换
- ✅ 蓝色帽子 + 小耳麦
- ✅ 全局拖拽移动
- ✅ 聊天弹窗（可拖拽）
- ✅ 系统数据联动（舆情/事件/日报/品牌/系统状态）

### 8. 微信通知中心
- ✅ 4种渠道（公众号/企业微信/Server酱/PushPlus）
- ✅ 高风险/严重风险立即推送
- ✅ 系统异常/采集失败/登录失效推送
- ✅ 日报/周报推送
- ✅ 消息去重 + 失败自动重试 + 推送日志

---

## 系统架构

```
小红书/Rednote/微博登录态
        ↓
浏览器采集 (CDP + Playwright)
        ↓
原始笔记数据
        ↓
Pipeline流水线：
  1. 标准化（繁简归一/时间纠错/数字格式化）
  2. 水军过滤（广告/灌水/营销号）
  3. SimHash语义去重
  4. 主体过滤（广州太古汇精准识别）
  5. 持久化（note_id去重入库）
        ↓
AI分析（异步后台）
  ├─ 情感分析
  ├─ 风险等级
  ├─ 关键词提取
  └─ 业态分类
        ↓
事件聚合（异步后台）
        ↓
数据看板展示
        ↓
报告导出（日/周/月/年）
        ↓
人工复核闭环 → 样本回流 → 模型迭代
```

---

## 技术栈

- **后端**: Python 3.x + Flask
- **数据库**: SQLite
- **前端**: HTML + CSS + JavaScript
- **采集**: Playwright + CDP + Cookie
- **AI**: 本地Ollama + 云端API（豆包/GPT/Trae）
- **部署**: Cloudflare Tunnel（公网访问）
- **测试**: pytest + 端到端测试

---

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
npm install
```

### 2. 配置环境变量
复制 `.env.example` 为 `.env`，填写配置：
```
TAIKOO_AUTH_USER=admin
TAIKOO_AUTH_PASSWORD=你的密码
TAIKOO_HOST=0.0.0.0
TAIKOO_PORT=8200
```

### 3. 启动系统
```bash
python app.py
```

### 4. 访问系统
- 本地: http://127.0.0.1:8200
- 局域网: http://你的IP:8200
- 公网: 通过Cloudflare Tunnel

---

## 目录结构

```
广州太古汇舆情监测系统/
├── app.py                    # 主应用
├── database.py               # 数据库操作
├── ai_analyzer.py            # AI分析
├── intelligence.py           # 情报分析
├── risk_engine.py            # 风险引擎
├── report_engine.py          # 报告引擎
├── daily_report.py           # 日报生成
├── collector.py              # 采集器
├── web_monitor.py            # 网页监控
├── monitor_pipeline.py       # 监控流水线
├── function_registry.py      # 函数注册表
├── subject_rules.py          # 主体规则
├── review_workflow.py        # 人工复核闭环
├── wechat_notifier.py        # 微信通知中心
├── collector_v2_integration.py  # collector_v2接入补丁
│
├── collector_v2/             # 采集引擎V2（模块化架构）
│   ├── base.py               # PlatformCollector基类
│   ├── browser_session.py    # 浏览器会话管理
│   ├── xhs/                  # 小红书采集器
│   ├── weibo/                # 微博采集器
│   ├── pipeline/             # 数据处理流水线
│   └── scheduler/            # 智能调度器
│
├── database_migrations.py    # 数据库迁移脚本
├── test_e2e.py               # 端到端测试
├── logger.py                 # 日志系统
├── config.py                 # 配置管理
├── ci_cd.py                  # CI/CD自动化
├── monitoring.py             # 系统监控
│
├── static/                   # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
├── templates/                # HTML模板
├── deployment/               # 部署脚本
│
├── data/                     # 运行数据
│   ├── monitor.db            # 主数据库
│   ├── backups/              # 数据库备份
│   ├── screenshots/          # 笔记截图
│   └── reports/              # 生成的报告
│
├── brand_directory.json      # 品牌目录（198品牌）
├── brand_websites.json       # 品牌官网
├── events_config.json        # 事件配置
├── case_library.json         # 案例库
├── function_map.json         # 函数映射表
├── system_config.json        # 系统配置
├── .env.example              # 环境变量模板
├── requirements.txt          # Python依赖
├── package.json              # Node依赖
│
├── README.md                 # 项目说明
├── ARCHITECTURE.md           # 架构文档
├── DEPLOYMENT.md             # 部署文档
├── USER_GUIDE.md             # 用户指南
├── UPGRADE.md                # 升级指南
├── CHANGELOG.md              # 变更日志
├── VERSION                   # 版本号
│
├── apple-ui-reference/       # 苹果图标&UI设计参考库（GitHub，36仓库/5大类，仅供设计参考）
├── apple-ui-reference-db.zip # 上述参考库备份整包
└── 监测系统-ui架构&互动视频参考案例/  # 自有交互参考（视频/截图）
```

---

## UI 设计参考库（苹果图标 / iOS 风格）

做网页端、手机端及未来 App 端的图标与界面升级时，先查本地参考库，不要凭印象写苹果规范：

- **运行说明与提示重点（先读）**: [apple-ui-reference/运行说明-提示重点.md](apple-ui-reference/运行说明-提示重点.md)
- **分类清单**: [apple-ui-reference/catalog.md](apple-ui-reference/catalog.md)
- **机器可读数据库**: `apple-ui-reference/apple-ui-reference-db.json`（36 个 GitHub 仓库，含用途、链接、已核实源码路径）
- **代码样本**: `apple-ui-reference/code-snippets/`（系统图标矢量提取/导出、类型安全调用、App 图标尺寸、HIG 几何、iOS26 液态玻璃 API）

调用顺序：`catalog.md` 选类 → `db.json` 取仓库与源码路径 → `code-snippets/` 读本地样本 → 翻译为 `templates/`、`static/` 的 HTML/CSS/JS（本项目为 Web 栈，不直接使用 Swift；SF Symbols 仅参考规范，不得作为自有素材上线）。

---

## 版本信息

当前版本: v5.7.0
详见 [CHANGELOG.md](CHANGELOG.md)

---

## 许可证

内部项目，仅限广州太古汇舆情监测使用。
