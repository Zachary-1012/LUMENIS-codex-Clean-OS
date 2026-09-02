# 广州太古汇·舆情监测系统 v5.3.0
## 明日到公司升级说明（Windows）

### 一、你明天到公司后只做这几步

> **原则：不重建数据库，不删除历史笔记，不重新安装已经正常工作的环境。**

#### 1. 先进入原系统目录
```powershell
cd D:\taikoo-monitor\taikoo-monitor-v4.2-remote-optimized\taikoo-monitor-clean
```

#### 2. 关闭昨晚留下的旧服务
如果 PowerShell 仍然显示：
```text
* Running on http://127.0.0.1:8200
Press CTRL+C to quit
```
先按：
```text
Ctrl + C
```

#### 3. 备份数据库（非常重要）
```powershell
.\.venv\Scripts\Activate.ps1
python -c "import database as db; print(db.backup_database('data\\backups\\before-v5.3.db'))"
```
看到：
```text
data\backups\before-v5.3.db
```
即可继续。

#### 4. 用 v5.3 新代码覆盖旧代码
把本压缩包中的：
- `app.py`
- `database.py`
- `static\index.html`
- `static\css\style.css`
- `static\js\app.js`
- `V5.3_CHANGELOG.md`
- `UPGRADE_V5.3_WINDOWS.md`

复制到原来的 `taikoo-monitor-clean` 对应位置。

**不要覆盖：**
- `.venv`
- `data\monitor.db`
- `data\backups`
- 你的 `.env`

#### 5. 检查环境
```powershell
python --version
python -m pip --version
node --version
npm --version
```
你昨晚已经确认正常：
- Python 3.13.15
- pip 26.2.1
- Node v26.7.0
- npm 11.19.0

无需因为版本提示升级 npm。

#### 6. 做代码自检
```powershell
python test_system.py
```
必须看到：
```text
ALL TESTS PASSED
```

再执行：
```powershell
node --check static\js\app.js
python -m py_compile app.py database.py
```
没有输出错误即可。

#### 7. 启动系统
```powershell
python app.py --host 0.0.0.0
```
如果看到：
```text
广州太古汇舆情监测系统 v5.3.0
```
并且：
```text
Running on http://127.0.0.1:8200
```
说明启动成功。

### 二、先在电脑上验证网页
浏览器打开：
```text
http://127.0.0.1:8200
```

确认：首页看到：
1. 左侧导航
2. 六个核心指标
3. 情感分布
4. 风险等级分布
5. 内容分类 Top 7
6. 风险预警
7. 热门话题
8. 舆情日历
9. 事件中心
10. 近14天变化

### 三、热门话题怎么用
热门话题现在不是只看负面。

例如可能出现：
- 餐饮推荐（正向）
- 新店开业（正向）
- 方所（中性/正向）
- 停车体验（负向）

点击话题右侧：
```text
小红书 ↗
```
会直接打开：
```text
小红书搜索：广州太古汇 + 该话题
```

这是本系统“小红书主平台”的核心入口之一。

### 四、验证手机局域网
电脑启动后，PowerShell 另开一个窗口执行：
```powershell
ipconfig
```
找到 WLAN 的 IPv4，例如：
```text
192.168.0.213
```

手机和电脑连接同一个 Wi-Fi 后打开：
```text
http://192.168.0.213:8200
```

如果打不开：
1. 确认电脑服务窗口仍在运行。
2. 确认手机和电脑在同一个 Wi-Fi。
3. Windows 防火墙允许 Python / 8200 端口。

### 五、5G 手机远程访问

推荐使用项目自带：
```text
start_remote_5g.bat
```

但在启动前必须配置 Basic Auth。

在项目根目录创建 `.env`：
```env
TAIKOO_AUTH_USER=admin
TAIKOO_AUTH_PASSWORD=<REDACTED>
TAIKOO_HOST=127.0.0.1
TAIKOO_PORT=8200
AUTO_INTERVAL_MINUTES=90
```

然后双击：
```text
start_remote_5g.bat
```

Cloudflare 会输出一个：
```text
https://xxxxx.trycloudflare.com
```

手机关闭 Wi-Fi，切换 5G/蜂窝网络后打开这个地址。

浏览器出现登录框时输入 `.env` 中的用户名和密码。

> Quick Tunnel 地址每次启动可能变化；这是正常现象。

### 六、如果 5G 打不开

先在电脑上确认：
```powershell
cloudflared --version
```

如果提示找不到：
```text
cloudflared
```
先安装 Cloudflare cloudflared，再重新运行 `start_remote_5g.bat`。

不要为了这个问题重新安装 Python。

### 七、正常工作后的日常使用

日常不需要一直手动操作。

系统默认：
```text
约每90分钟自动更新
```

需要立即查看最新情况时：
```text
顶部「采集数据」
```

系统流程是：
```text
最新发现
  ↓
主体过滤
  ↓
小红书采集
  ↓
去重/复核
  ↓
情感与风险分析
  ↓
事件聚合
  ↓
首页更新
```

### 八、升级后不要做的事情

不要：
```text
删除 data\monitor.db
删除 .venv
重新 seed 全部数据
重新安装 Node
重新安装 Chromium
```
除非系统出现明确错误并经过排查。

### 九、出现问题时的最短排查顺序

#### 页面打不开
```powershell
python app.py --host 0.0.0.0
```
看有没有 traceback。

#### 提示没有 Flask
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

#### JS 页面异常
```powershell
node --check static\js\app.js
```

#### 数据库异常
不要删除数据库；先复制错误信息并保留：
```text
data\monitor.db
```
然后再处理。

#### 5G 异常
先确认：
```powershell
cloudflared --version
```
然后确认 `.env` 中设置了：
```text
TAIKOO_AUTH_USER
TAIKOO_AUTH_PASSWORD
```

---

## v5.3 产品定位

系统名称固定：

**广州太古汇·舆情监测系统**

产品重点固定：

**小红书为主平台，广州太古汇为唯一核心主体。**

公开互联网发现能力作为底层检索与补充，不在客户首页展示复杂技术架构。
