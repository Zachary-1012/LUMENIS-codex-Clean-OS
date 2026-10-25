# OEVIRA Public Website｜寰意官网

Current display identity (2026-10-18): **寰意 / OEVIRA**. The existing [canonical naming authority](../00-GOVERNANCE/CANONICAL-NAMING-AND-TWIN-SYNC.md) governs this rename. Technical identifiers, package names, environment variables, commands and source paths retain their compatibility spelling; dated records below preserve their original names and evidence.
The approved brand domain is `oevira.com`; the positioning line is “An Open Space for Thought and Creation.” This documentation does not configure DNS, a public origin or deployment, or establish that the destination is live. Existing verified-origin and unavailable-link rules below still apply.

This package contains the public, static Astro website for introducing OEVIRA
and its product boundaries. It is separate from the Product Core-backed Web Workspace
in [`../app/`](../app/README.md).

本目录是寰意面向公众的静态 Astro 官网，用于介绍产品及其边界；它与
[`../app/`](../app/README.md) 中的 Web Workspace 相互独立。

## Local development｜本地开发

From the repository root, run the existing package commands in `website/`:

```powershell
Set-Location website
npm install
npm run build
npm test
```

从仓库根目录进入 `website/`，运行现有工程命令：

```powershell
Set-Location website
npm install
npm run build
npm test
```

## Routes and localization｜路由与本地化

The static site provides these locale routes:

- `/` — 简体中文
- `/en/` — English
- `/ko/` — 한국어

静态官网提供以下语言路由：

- `/` — 简体中文
- `/en/` — English
- `/ko/` — 한국어

Keep each language's content aligned in meaning and product facts. A locale
route must not imply an unsupported feature, service, permission or availability.

Each locale also has addressable `products/`, `solutions/`, `outcomes/`, `help/`,
`trust/`, `updates/`, `download/`, `contact/`, `terms/`, `privacy/` and `license/`
pages. Language switching retains the current family. The help library covers
starting work, sources, research, writing, video, podcast, commerce, brand,
recovery and preferences; its content remains readable without JavaScript.
Search filters the displayed guide text locally and provides a clear reset.

每种语言还提供产品、使用场景、成果与操作、帮助、信任、更新、下载、联系及法律
文本状态等独立页面。切换语言保留当前家族；帮助可在无脚本时完整阅读，搜索仅在
当前页面筛选指南。真实操作视频、客户案例、正式法律文本与发行包未提供时，页面
明确说明状态，不以虚构演示、占位下载或模拟提交代替。

保持各语言内容在产品含义与事实上的一致。语言路由不得暗示尚未支持的功能、服务、
权限或可用状态。

## Build and public-origin contract｜构建与公开源站合同

When no public origin is configured, `npm run build` creates a preview build:
it includes `noindex,nofollow`, blocks robots and omits canonical URLs and
`hreflang` links. Preview output is not a production SEO build.

未配置公开源站时，`npm run build` 生成预览构建：输出包含 `noindex,nofollow`、
屏蔽 robots，并省略 canonical URL 与 `hreflang` 链接。预览产物不是生产 SEO 构建。

For a public deployment, set `LUMENIS_PUBLIC_SITE_ORIGIN` to the verified public
HTTPS origin before building. Optional destination URLs are:

- `LUMENIS_PUBLIC_TRIAL_URL`
- `LUMENIS_PUBLIC_CONTACT_URL`
- `LUMENIS_PUBLIC_HELP_URL`
- `LUMENIS_PUBLIC_WORKSPACE_URL`

Public URLs must resolve to reachable HTTPS destinations. Reserved example
hosts (`example.invalid`, `example.com`, `.test`) and localhost are rejected
when supplied as public URLs. Do not use an unverified or private host as the
canonical origin.

公开部署前，将 `LUMENIS_PUBLIC_SITE_ORIGIN` 设置为已核验的公开 HTTPS 源站。
以下目标链接为可选配置：

- `LUMENIS_PUBLIC_TRIAL_URL`
- `LUMENIS_PUBLIC_CONTACT_URL`
- `LUMENIS_PUBLIC_HELP_URL`
- `LUMENIS_PUBLIC_WORKSPACE_URL`

公开 URL 必须指向可访问的 HTTPS 目标。配置公开 URL 时，保留示例域名
（`example.invalid`、`example.com`、`.test`）和 localhost 会被拒绝。不得将未核验
或私有主机设为 canonical 源站。

Unset external destinations render an explicit disabled state. The generated
local help page is available independently of an external help channel.
Configured workspace links use only the existing product routes and creation
entry values; earlier task queries and fragments are not carried into new work.
The website must not
pretend to submit a form, store user credentials, handle provider secrets or
execute Product Core workflows. Product data, Evidence, Permission and business
actions remain with their existing owners.

未设置的目标链接应呈现明确的禁用状态。官网不得伪装表单已提交、存储用户凭据、
处理 Provider 密钥或执行 Product Core 工作流。产品数据、Evidence、Permission
和业务操作仍归既有 Owner 管理。

## Content and design ownership｜内容与设计归属

`DEVELOPMENT-BRIEF.md` records website-scoped implementation context and
reference research. It is supporting material, not a competing product or
design authority. The repository's Product Architecture and sole Experience
Constitution define the product and experience boundaries.

`DEVELOPMENT-BRIEF.md` 记录官网范围内的实现背景与参考研究。它是辅助材料，不是
第二套产品或设计权威。产品范围由仓库的 Product Architecture 定义，体验边界由
唯一的 Experience Constitution 定义。

The website introduces OEVIRA; it does not own Product Truth, accounts,
workflow execution, Evidence, Permission, data collection or provider keys.
Do not imply that a link, static page or successful build proves the linked
workspace or service is available.

官网负责介绍寰意，不拥有 Product Truth、账户、工作流执行、Evidence、Permission、
数据采集或 Provider 密钥。不得暗示链接、静态页面或构建成功能够证明目标工作区或
服务当前可用。
