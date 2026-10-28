# Public Website source package｜官网源码包

`website/` is the Astro source package for the OEVIRA Public Website. Its public role is product information, prepared demonstrations and cases, help, and real product/download links. The website has no embedded product trial, uploads, generation, or business workflow execution; those operations belong in the product workspace.

`website/` 是 OEVIRA Public Website 的 Astro 源码包。官网用于产品信息、制作好的演示与案例、帮助内容，以及真实产品/下载链接；不提供内嵌试用、上传、生成或业务工作流执行，这些操作属于产品工作区。

Routes live under `src/pages/`; shared host/localization helpers stay in `src/`. See [CURRENT](../00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md) for source availability and release acceptance. A package build alone does not establish a complete or published website.

路由放在 `src/pages/`，源站与本地化辅助代码放在 `src/`。源码可用范围与发布验收见 [CURRENT](../00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)；包构建不等于完整官网或已发布官网。

## Source map｜源码目录

| Path / 路径 | Contents / 内容 |
| --- | --- |
| `src/pages/` | Existing Astro route sources / 现有 Astro 路由源码 |
| `src/` | Public-host validation, localization, and shared content data / 公开源站校验、本地化与共享内容数据 |
| `public/` | Static public assets / 静态公开资源 |
| `tests/` | Node.js package checks / Node.js 包检查 |
| `astro.config.mjs` | Static output, locales, and public-origin input / 静态输出、语言与公开源站参数 |
| `package.json`, `package-lock.json` | Package scripts and pinned dependency resolution / 包脚本与锁定的依赖解析 |

## Package commands｜包命令

Run from the repository root:

```powershell
Set-Location website
npm ci
npm run dev
npm run build
npm test
npm run preview
```

`npm test` runs the package build followed by `node --test tests/*.test.mjs`. `npm run dev`, `npm run build`, and `npm run preview` act on the routes currently present; they do not create missing content pages or perform product operations.

`npm test` 会先执行包构建，再运行 `node --test tests/*.test.mjs`。`npm run dev`、`npm run build` 与 `npm run preview` 仅作用于当前存在的路由，不会生成缺失的内容页，也不执行产品业务操作。

`LUMENIS_PUBLIC_SITE_ORIGIN` is the Astro configuration input for the public site origin. Configure it only with the verified public HTTPS origin appropriate to the build; package build output alone is not publication or destination availability.

`LUMENIS_PUBLIC_SITE_ORIGIN` 是 Astro 配置使用的官网源站参数。仅在对应构建已核验的公开 HTTPS 源站时配置；包构建产物本身不代表发布完成或目标可访问。

## Product and experience references｜产品与体验权威

- [Repository instructions](../AGENTS.md)
- [Current source and acceptance](../00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)
- [Product Architecture](../00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)
- [Experience Constitution](../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)

官网角色与产品/体验边界以以上唯一权威及其导航为准；本 README 只说明 Astro 源码包。
