# 废弃文件及时清理纪律 V1.0（防读回旧文件）

> 目的：适配融合中被替代/重复/过时的代码文件及时删除，避免后续误 import、误注册、读回旧逻辑。同时严守用户红线：数据、历史、研究库不删。

## 一、应及时删除（主库 D:\Taikoo-monitor-new 内）
1. 已被新模块替代、且无任何活跃引用的旧实现文件。
2. 重复收敛后多余的那份（如 ai_channel 与 runtime_guardian 重复的 CircuitBreaker、safety_boundary 与 security_boundary 重复件——引用迁移完后删废弃方）。
3. 失效副本/临时件：`.bak/.old/.orig/.tmp/~$`、一次性脚本、空目录、过期生成物。
4. 过期 `__pycache__/*.pyc`（源码已删/改名后必须清，防止 Python 读回旧字节码）。

## 二、删除前必做（安全检查，缺一不可）
1. **先证无活跃引用**：全仓 grep 文件名/模块名/import/蓝图注册/路由/模板 url_for/配置引用；有引用先把引用迁到新实现，再删。
2. 同步删除其注册点（import、Blueprint、路由、侧边菜单、模板 script/link），不留悬空引用。
3. 删后立即跑相关 import 测试 + pytest 子集 + 路由注册断言，确认无 ImportError/无断链/服务能起，才算删成功。
4. git 跟踪文件用 git rm；交付清单列出「删除文件路径 + 删除原因 + 由哪个新文件替代」，可追溯。

## 三、严禁删除（用户红线，拿不准先列问、不擅删）
- 任何数据：`data/`、`*.db/*.sqlite*`、数据库表与历史数据、cookie/凭证（data\*.json、data\private、data\cookies）。
- `intelligence_library/` 研究/案例/语料/三语库、OSAI 导入资产。
- `archive/`、`99-ARCHIVE/`、`Taikoo-monitor-new-backups` 等有意保留的备份。
- `.git/`、配置(.env/.env.example)、用户上传资料、`太古汇运营资料`(本就不在库内)。

## 四、边界
- 库外参考目录（D:\Taikoo-staging-ui、Taikoo-security、ADRH、OSAI 等）**不动**；只清理主库内会被运行时读回的废弃副本。参考完毕不等于删除源。
- "废弃但可能有追溯价值的代码"优先靠 git 历史追溯，工作区不留可被 import 的旧文件；是否归档由用户确认，不自行堆 archive。
- 判不准是否废弃的，列入「待确认删除清单」一次性回报，不擅自删、也不长期留。
