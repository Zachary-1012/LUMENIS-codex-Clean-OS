# 本轮公开采集研究与采用

日期：2026-10-08；序境基线：`288f222decb48e2c8e9217c712e7af6f6c1aa9ce`。
本记录是研究/改动证据，既有 SYSTEM Collector、Source/Evidence/Canonical 和 Permission 仍为实际 Owner。
本轮只研究/采用匿名公开路线；用户排除需要登录的 OpenCLI 路线。现有平台授权、Skill 商店与 GitHub 增强能力继续按原规则。

## 固定上游版本与判断

| 项目 | 读取提交 | 许可证与实际读取 | 采用判断 |
|---|---|---|---|
| [Agent-Reach](https://github.com/Panniantong/Agent-Reach/tree/94f06c1969dfc1834001269d79d3ad0972d9dee6) | `94f06c1969dfc1834001269d79d3ad0972d9dee6`，2026-10-08 | MIT；LICENSE、pyproject、channels/base、web、twitter、bilibili、xiaohongshu、_opencli_site、probe | ADAPT：按具体能力选择后端、区分安装与健康、记录来源。拒绝整套安装和把 CLI 版本/配置存在当业务健康。 |
| [OpenCLI](https://github.com/jackwener/OpenCLI/tree/24136945847afbfad266c6c46a8cd335377f9112) | `24136945847afbfad266c6c46a8cd335377f9112`，2026-09-25 | Apache-2.0；LICENSE、package、src/registry.ts、browser-bridge说明及 XHS/Bilibili/Instagram/Facebook 适配器 | ADAPT：访问类别和只读动作边界。REJECT_THIS_BATCH：COOKIE/INTERCEPT/UI、浏览器桥接、已登录profile路线。未安装/注册任何OpenCLI后端。 |
| [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell/tree/e406c2befbe65501409026d49259602669f7246a) | `e406c2befbe65501409026d49259602669f7246a`，2026-10-07 | Apache-2.0；LICENSE、README、MXC driver README/policy、supervisor-network policy | RESEARCH_ONLY：借鉴策略不可执行即拒绝、限定文件/出站访问、进程身份归属。当前不安装，不成为第二Runtime。 |
| [bilibili-cli](https://github.com/public-clis/bilibili-cli/tree/dbe28551930df43b633baa52e9639832aeada967) | `dbe28551930df43b633baa52e9639832aeada967`，2026-03-14 | Apache-2.0；README、LICENSE、bili_cli/auth.py、client.py调用边界 | DEFER：公开函数存在，但 CLI credential helper 会加载/刷新浏览器凭据；optional模式也不等于强制匿名。此轮不安装，不为了6平台任务新增B站路线。 |
| [twitter-cli](https://github.com/public-clis/twitter-cli/tree/7c634e0d396b1e7af9f63315b414925fe4f29ae7) | `7c634e0d396b1e7af9f63315b414925fe4f29ae7`，2026-05-07 | Apache-2.0；LICENSE、README、twitter_cli/auth.py | REJECT_THIS_BATCH：会话读取和自动Cookie获取与本批匿名路线不符。没有运行其status/auth，也未读取浏览器。 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp/tree/51bab8a0116f4d8004c315706d809782607d5847) | `51bab8a0116f4d8004c315706d809782607d5847`，2026-09-27 | Unlicense；LICENSE、THIRD_PARTY_LICENSES、README、cookies.py、YoutubeDL.py参数调用 | DEFER：用途是具体公开媒体提取；支持站点不等于每个URL匿名可用。未来要明确无cookie/profile、资源/下载rights和进程边界；预打包二进制另带第三方许可证，不能只看主许可证。 |

日期是读取时的最后提交时间，不是持续维护保证。上述为相关切片源码研究，没有冒称完整审计所有上游文件、插件或传递依赖。许可证不授予平台账号、原始内容或训练用途权利；本批没有引入这些项目代码或运行依赖。

## 关键源码事实及序境修正

- Agent-Reach 的 `web.check()` 无实际网页请求就返回可用，Bilibili 的部分检查只看 `bili --version`；这不能成为真实健康证明。序境继续区分 NOT_CONFIGURED、NEED_VERIFY、真实取材与历史结果。
- Agent-Reach 的 Jina 路径将源URL发送给第三方服务，不等于本机直接匿名HTTP；本批优先已有 PublicSource，不增加该依赖。上游关于平台风控可用性的注释不是本机实测。
- OpenCLI `registry.ts` 包含 PUBLIC/LOCAL/COOKIE/INTERCEPT/UI，省略strategy的browser命令可能走COOKIE；必须核命令实现和请求凭据，不能只按项目“免API”宣传分为Z0。安装还包含postinstall适配器下载，本批未运行。
- OpenCLI Instagram 使用带凭据浏览器请求，部分字段空值被补0；序境保留UNKNOWN。六平台登录路线被排除不表示删除原有授权Collector。
- OpenShell有Windows MXC代码，并非简单“Windows不支持”；但该driver需要指定Windows Insider/组件，交互连接和重启持久性仍有限制，现有桌面产品不应为此切换运行架构。只吸收可执行策略与过程归属原则。

## 本轮架构变更

在现有 `lumenis/system/collector/adapters/` 中加入 capability route 描述与 resolver，扩展既有 CollectionResult 的路由/provenance，不建新Collector或Scheduler。
公开HTTP/RSS/Atom/Sitemap/公众号文章/Instagram精确公开帖子与现有授权session路线按实际能力分开；Z2仅有类型，没有假装官方API已获授权。
现有 Permission 在执行前生效；登录墙、验证、限流、封禁不能触发切换账号/后端。当前没有生产fallback候选；未来只有明确声明、同能力/身份/范围且现有Permission允许的route才可回退。
实际结果身份必须与所选route匹配；attempted route与实际获取成功分开，失败不能记成匿名取材成功。
数据仍由同一 Source → Evidence → Canonical 事务接纳；路由元数据不授予资料用途/训练权限。

## 真实实验与验收入口

六平台×12能力的机器和文字清单：`ZERO-AUTH-MATRIX-20261008.json` / `.md`。
其中源码能力、匿名实际返回字段、网络预检失败和平台限制分别记录；单帖或HTTP成功不等于搜索/评论/历史回填成立。匿名环境没有读取任何已有账号/Cookie/profile。
本次网络失败保留具体阶段、域名、时间与错误；若没有真实材料则不制造Evidence/Canonical记录，不以fixture冒充真实取材。

源码、精确受影响测试/修复和发布状态见CURRENT同批记录；生产运行加载、六平台业务闭环与用户验收仍需各自证据。研究上游、安装软件、测试通过不直接提升这些状态。

## 拟发布源码的组合验证

在 `288f222d` 干净归档中只叠加本批源码，`secondary_collection.py`采用HEAD上的精确发布副本，不混入原有XHS/max_scroll候选。实际命令：

```text
python -m pytest -q tests/test_collector_access_routing.py tests/test_public_source_adapters.py tests/test_secondary_collection_surface.py tests/test_collector_transaction_truth.py --junitxml=../collector-publishable-final.xml
```

结果：**63 passed / 0 failed / 0 errors**，exit 0，无后台线程泄漏。环境为显式空SQLite种子/临时测试库、离线模式；没有采集账号/生产库。JUnit SHA256：`d060aa8d907ecf020c690d211e741948e7077ff1ce6edd673b41709c76199ffa`。

覆盖公开正常读取、分类/路由、错误URL/畸形端口、Instagram查询与公开详情分开、公众号原文与Sogou发现分开、实际platform/provider与请求漂移拒绝、attempted/actual访问分开、未观测计数NULL、原有Permission与Evidence/Canonical事务。发现3类实际源码缺口后修复并复验；没有为绿灯放宽权限或改失败分类。

发布源码副本LF SHA256：`c10a1f4fa02a351d387d589d029c90914158e149574a71c51ce93ee93488200e`。原工作树中此前未发布的唯一行为继续保留；副本仅用于精确暂存/验收，不是第二实现树。

真实网络与字段层仍按72项矩阵如实记录。匿名网页HTTP200及字段名不能证明完整正文/指标/分页，当前没有新增六平台业务闭环或正式Evidence准入的证明。后续闭环必须消费真实材料并验证其保存/继续/来源关系。
