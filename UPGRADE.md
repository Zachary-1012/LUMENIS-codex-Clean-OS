# 升级指南

## 升级前准备

### 1. 备份数据库
```bash
# 复制数据库文件
copy data\monitor.db data\backups\monitor_before_upgrade.db

# 或使用系统备份功能
python -c "import database; database.backup_database('data/backups/before_upgrade.db')"
```

### 2. 备份配置文件
```bash
copy .env .env.backup
copy system_config.json system_config.json.backup
```

### 3. 记录当前版本
```bash
type VERSION
```

### 4. 停止系统
```bash
# 按 Ctrl+C 停止运行中的系统
# 或关闭运行系统的终端窗口
```

---

## 升级步骤

### 方式一：源码包升级（推荐）

#### 1. 下载新版本源码包
```
TaikooMonitor_v5.x.x_SOURCE.zip
```

#### 2. 解压到临时目录
```bash
mkdir upgrade_temp
cd upgrade_temp
unzip ..\TaikooMonitor_v5.x.x_SOURCE.zip
```

#### 3. 复制新代码到系统目录
**重要**: 不要覆盖 `data/` 目录和 `.env` 文件！

```bash
# 复制Python文件
copy upgrade_temp\*.py .

# 复制静态资源
xcopy /E /Y upgrade_temp\static\* static\

# 复制模板
xcopy /E /Y upgrade_temp\templates\* templates\

# 复制配置模板（不要覆盖.env）
copy upgrade_temp\.env.example .

# 复制JSON配置（如果有更新）
copy upgrade_temp\*.json .

# 复制新增模块目录
xcopy /E /Y upgrade_temp\collector_v2\* collector_v2\
```

#### 4. 安装新依赖
```bash
pip install -r requirements.txt
npm install
```

#### 5. 数据库迁移
```bash
python database_migrations.py
```

#### 6. 启动系统
```bash
python app.py
```

#### 7. 验证升级
- 访问系统，确认正常登录
- 检查首页数据是否正常显示
- 测试核心功能（采集、报告导出、Zachary等）
- 检查版本号是否更新

---

### 方式二：Git升级（如果使用Git）

```bash
# 拉取最新代码
git pull origin main

# 安装依赖
pip install -r requirements.txt
npm install

# 数据库迁移
python database_migrations.py

# 重启系统
```

---

### 方式三：开发者工具在线升级

1. 登录系统
2. 进入「设置」→「开发者工具」
3. 粘贴升级代码
4. 点击「执行」
5. 系统自动备份并部署
6. 刷新页面验证

**支持的代码类型**:
- Python代码（后端升级）
- JavaScript代码（前端升级）

---

## 版本升级说明

### 从 v5.6.x 升级到 v5.7.0

#### 新增功能
- ✅ 中期4项基础设施（数据库迁移/端到端测试/日志系统/配置管理）
- ✅ 监控告警 + CI/CD自动化
- ✅ 采集引擎V2模块化架构
- ✅ 人工复核闭环（负面舆情二次确认）
- ✅ 微信通知中心
- ✅ 微博采集器
- ✅ SimHash语义去重优化
- ✅ 品牌业态数据更新（198品牌官方清单）

#### 修复问题
- ✅ app.py app.run()位置错误
- ✅ SimHash阈值过低
- ✅ 品牌目录数据不准确

#### 升级注意事项
1. 必须运行 `python database_migrations.py` 进行数据库迁移
2. 新增 `collector_v2/` 目录，需要完整复制
3. 新增 `review_workflow.py`、`wechat_notifier.py`、`collector_v2_integration.py`
4. 配置文件新增微信、AI等配置项，参考 `.env.example`

---

### 从 v5.3.x 升级到 v5.7.0

跨度较大，建议：
1. 完整备份现有系统
2. 使用全新源码包部署
3. 只迁移 `data/monitor.db` 数据库
4. 重新配置 `.env`
5. 运行数据库迁移

---

## 数据库迁移

### 自动迁移
系统启动时会自动检查数据库版本并迁移：
```bash
python app.py
# 启动时自动执行迁移
```

### 手动迁移
```bash
python database_migrations.py
```

### 迁移版本
- v0: 初始版本
- v1: 笔记表扩展
- v2: 事件表
- v3: 报告表
- v4: 品牌表
- v5: 评论表
- v6: 预警表
- v7: 负面确认字段
- v8: 最新版本

### 迁移失败恢复
如果迁移失败，使用备份恢复：
```bash
copy data\backups\monitor_before_upgrade.db data\monitor.db
```

---

## 升级后验证清单

### 基础功能
- [ ] 系统正常启动，无报错
- [ ] 登录页面正常显示
- [ ] 用户名密码登录成功
- [ ] 首页数据正常显示

### 数据功能
- [ ] 笔记库有数据
- [ ] 笔记详情正常查看
- [ ] 事件中心有事件
- [ ] 品牌监测有数据
- [ ] 趋势图正常显示

### 采集功能
- [ ] 采集状态正常显示
- [ ] 手动采集可以触发
- [ ] 采集次数计数正确
- [ ] 新数据可以入库

### 报告功能
- [ ] 报告中心正常访问
- [ ] 日报可以导出
- [ ] 周报可以导出
- [ ] 导出文件可以正常打开

### AI功能
- [ ] Zachary机器人正常显示
- [ ] Zachary可以拖拽
- [ ] Zachary聊天可以打开
- [ ] Zachary回答正常
- [ ] AI分析功能正常

### 其他功能
- [ ] 负面审核页面正常
- [ ] 设置页面正常
- [ ] 开发者工具正常
- [ ] 红点标记正常

---

## 回滚方案

如果升级失败，可以回滚到之前版本：

### 1. 停止系统
```bash
# 按 Ctrl+C
```

### 2. 恢复数据库
```bash
copy data\backups\monitor_before_upgrade.db data\monitor.db
```

### 3. 恢复代码
```bash
# 如果有Git
git reset --hard <旧版本号>

# 如果有备份
# 从备份目录复制旧代码
```

### 4. 恢复配置
```bash
copy .env.backup .env
```

### 5. 重启系统
```bash
python app.py
```

---

## 注意事项

### 永远不要做的事
1. ❌ 不要删除 `data/monitor.db`
2. ❌ 不要用新源码包的 `data/` 覆盖现有数据库
3. ❌ 不要删除 `data/backups/` 目录
4. ❌ 不要在升级前不备份
5. ❌ 不要覆盖 `.env` 文件
6. ❌ 不要删除 `.venv/` 虚拟环境
7. ❌ 不要删除 `node_modules/`

### 必须做的事
1. ✅ 升级前备份数据库
2. ✅ 升级前备份配置文件
3. ✅ 升级后运行数据库迁移
4. ✅ 升级后验证所有功能
5. ✅ 保留旧版本备份至少7天

### 数据安全
- 历史数据库永远是你的资产，源码升级不能碰它
- `data/monitor.db` 和 `data/backups/` 必须保留在本机
- 真实Cookie不进入源码包
- `.env` 文件不提交到代码仓库

---

## 版本号说明

版本号格式: `v主版本.次版本.修订号`

- **主版本**: 重大架构变更
- **次版本**: 新增功能模块
- **修订号**: Bug修复、小优化

示例:
- v5.3.0 → v5.7.0: 新增多个功能模块
- v5.7.0 → v5.7.1: Bug修复
- v5.7.0 → v6.0.0: 重大架构重构

---

## 技术支持

如升级遇到问题：
1. 查看系统日志: `logs/` 目录
2. 查看错误信息: 终端输出
3. 检查数据库: `python database_migrations.py`
4. 恢复备份: 参考回滚方案
