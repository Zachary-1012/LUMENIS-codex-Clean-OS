# LUMENIS Public Website｜序境官网

This package contains the public, static Astro website for introducing LUMENIS
and its product boundaries. It is separate from the Product Core-backed Web Workspace
in [`../app/`](../app/README.md).

本目录是序境面向公众的静态 Astro 官网，用于介绍产品及其边界；它与
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

Unset destinations render an explicit disabled state. The website must not
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

The website introduces LUMENIS; it does not own Product Truth, accounts,
workflow execution, Evidence, Permission, data collection or provider keys.
Do not imply that a link, static page or successful build proves the linked
workspace or service is available.

官网负责介绍序境，不拥有 Product Truth、账户、工作流执行、Evidence、Permission、
数据采集或 Provider 密钥。不得暗示链接、静态页面或构建成功能够证明目标工作区或
服务当前可用。
