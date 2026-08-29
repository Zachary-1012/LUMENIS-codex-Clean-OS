# 部署文档

## 环境要求

- **操作系统**: Windows 10/11 或 Linux
- **Python**: 3.8+
- **Node.js**: 16+（可选，用于前端构建）
- **浏览器**: Chrome/Edge（用于CDP采集）
- **内存**: 最低4GB，推荐8GB+
- **磁盘**: 最低2GB可用空间

---

## 本地部署

### 1. 准备代码
```bash
# 解压源码包
unzip TaikooMonitor_v5.7.0_SOURCE.zip
cd TaikooMonitor_v5.7.0
```

### 2. 安装Python依赖
```bash
# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 3. 安装Node依赖（可选）
```bash
npm install
```

### 4. 配置环境变量
```bash
# 复制配置模板
copy .env.example .env

# 编辑.env文件，填写配置
notepad .env
```

**关键配置项**:
```env
# 基础认证（公网访问必须设置）
TAIKOO_AUTH_USER=admin
TAIKOO_AUTH_PASSWORD=你的强密码

# 服务配置
TAIKOO_HOST=0.0.0.0
TAIKOO_PORT=8200

# AI配置（可选）
AI_PROVIDER=local  # local/doubao/gpt/trae
AI_API_KEY=你的API密钥
AI_API_URL=API地址

# 邮件配置（可选，用于日报推送）
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=你的邮箱
SMTP_PASSWORD=邮箱授权码
SMTP_TO=接收邮箱

# 微信配置（可选）
WECHAT_APP_ID=公众号AppID
WECHAT_APP_SECRET=公众号AppSecret
WECHAT_TEMPLATE_ID=模板ID
```

### 5. 初始化数据库
```bash
# 数据库会自动创建和迁移
python database_migrations.py
```

### 6. 启动系统
```bash
python app.py
```

启动成功后会显示：
```
============================================================
广州太古汇舆情监测系统 v5.7.0
启动地址: http://0.0.0.0:8200
============================================================
```

### 7. 访问系统
- **本地访问**: http://127.0.0.1:8200
- 输入用户名和密码登录

---

## 局域网访问

### 1. 查看本机IP
```bash
ipconfig
# 找到 WLAN 或 以太网 的 IPv4 地址，例如 192.168.1.100
```

### 2. 确保防火墙开放8200端口
```bash
# Windows防火墙添加规则
netsh advfirewall firewall add rule name="TaikooMonitor" dir=in action=allow protocol=TCP localport=8200
```

### 3. 手机/其他设备访问
确保手机和电脑在同一个Wi-Fi下，访问：
```
http://192.168.1.100:8200
```

---

## 5G热点访问

### 1. 电脑连接手机5G热点
- 手机开启个人热点
- 电脑连接该热点Wi-Fi

### 2. 查看电脑在热点网络中的IP
```bash
ipconfig
# 找到 WLAN 的 IPv4 地址，例如 172.20.10.3
```

### 3. 手机访问
手机关闭Wi-Fi（使用5G），或者其他设备连接同一热点，访问：
```
http://172.20.10.3:8200
```

---

## 公网访问（Cloudflare Tunnel）

### 方式一：Quick Tunnel（临时，URL会变）

#### 1. 安装cloudflared
下载地址: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

Windows下载后放到系统目录，或直接使用完整路径。

#### 2. 启动Tunnel
```bash
cloudflared tunnel --url http://127.0.0.1:8200 --protocol http2 --ha-connections 4 --no-autoupdate
```

#### 3. 获取公网URL
启动后会显示：
```
https://xxxx-xxxx-xxxx-xxxx.trycloudflare.com
```

#### 4. 访问
任何网络下都可以访问该URL，输入用户名密码登录。

**注意**: Quick Tunnel URL每次启动会变化，适合临时使用。

### 方式二：Named Tunnel（固定域名，推荐生产环境）

需要注册Cloudflare账号并绑定域名，配置后URL固定不变。

详见: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/

---

## 采集配置

### 小红书采集

#### 方式一：CDP模式（推荐）

1. **启动带CDP的浏览器**
```bash
# Windows
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="D:\taikoo-monitor\edge-cdp-profile"

# 或Chrome
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="D:\taikoo-monitor\chrome-cdp-profile"
```

2. **登录小红书**
在打开的浏览器中访问 https://www.xiaohongshu.com 并登录。

3. **系统自动连接CDP**
启动系统后，采集器会自动连接9222端口的浏览器进行采集。

#### 方式二：Cookie模式

1. **获取Cookie**
浏览器登录小红书后，按F12打开开发者工具，在Application/存储中找到Cookie，复制全部Cookie字符串。

2. **配置Cookie**
在系统设置页面填入Cookie，或创建 `data/private/xhs_cookie.txt` 文件。

### 微博采集（可选）

1. 浏览器登录微博 https://weibo.com
2. 获取Cookie并配置到系统
3. 微博采集不占用小红书采集次数

---

## 本地AI配置（可选）

### 安装Ollama
1. 下载Ollama: https://ollama.com/
2. 安装后启动
3. 下载模型：
```bash
ollama pull qwen2:7b
# 或更小的模型
ollama pull qwen2:1.5b
```

### 配置系统
在 `.env` 中设置：
```env
AI_PROVIDER=local
AI_LOCAL_URL=http://127.0.0.1:11434
AI_LOCAL_MODEL=qwen2:7b
```

---

## 日常运维

### 启动脚本
- `start_windows.bat` - Windows本地启动
- `start_lan.bat` - 局域网访问启动
- `start_remote_5g.bat` - 5G热点+Cloudflare Tunnel启动
- `start_remote_cloudflare.bat` - Cloudflare Tunnel启动

### 数据备份
数据库文件: `data/monitor.db`
定期备份: `data/backups/`

### 日志查看
日志目录: `logs/`
- `app.log` - 应用日志
- `collector.log` - 采集日志
- `error.log` - 错误日志

### 常见问题

**Q: 启动后访问显示401？**
A: 检查 `.env` 中的用户名密码，或临时关闭认证测试。

**Q: 采集没有数据？**
A: 检查浏览器是否登录小红书，CDP端口是否正确，Cookie是否有效。

**Q: 公网URL访问不了？**
A: 检查cloudflared是否在运行，本地系统是否正常启动，防火墙是否放行。

**Q: 数据库报错？**
A: 运行 `python database_migrations.py` 进行数据库迁移。

---

## 安全注意事项

1. **公网访问必须设置强密码**，不要使用默认密码
2. **不要将 `.env` 文件提交到代码仓库**
3. **定期备份数据库**，避免数据丢失
4. **采集频次不要过高**，避免账号被封禁
5. **新账号前3次使用极轻量模式**，保护账号安全
