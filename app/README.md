# OEVIRA App｜寰意应用

Current display identity (2026-10-18): **寰意 / OEVIRA**. The existing [canonical naming authority](../00-GOVERNANCE/CANONICAL-NAMING-AND-TWIN-SYNC.md) governs this rename. Technical identifiers, package names, environment variables, commands and source paths retain their compatibility spelling; dated records below preserve their original names and evidence.

This directory contains OEVIRA's Flutter application for the Web Workspace,
Windows/macOS Desktop and iOS Mobile Companion. The public acquisition website
is maintained separately in [`../website/`](../website/README.md).

本目录是寰意的 Flutter 应用，面向 Web Workspace、Windows/macOS 桌面端和
iOS 移动伴侣。Public Website 独立维护在 [`../website/`](../website/README.md)。

## Product and domain boundaries｜产品与领域边界

OEVIRA is one product. The Flutter app presents existing Product Core
capabilities; it does not own a second database, business-rule engine,
Canonical Data, Evidence, Metric, Permission or runtime.

寰意是一个产品。Flutter 应用负责呈现既有 Product Core 能力，不另建数据库、
业务规则引擎、Canonical Data、Evidence、Metric、Permission 或 Runtime。

- **CTH** is Subject-first commerce operations. Preserve the authorized Subject,
  business scope, source lineage and owner-provided results.
- **BMP** is Brand/Market-first brand and market work. Preserve brand, market,
  competitor, creator and campaign context; do not relabel a CTH page as BMP.
- **Shared creation is independently usable.** Users may start research,
  proposals, video or podcast work from the existing Shared entry points without
  first creating a CTH/BMP task. Linking a Shared result to a business task is
  optional and must retain the source domain and object context.
- **Analysis is a backend capability.** Deterministic calculations and normal
  business workflows must work without a model, external AI API, GPU or
  inference service. AI may add explanations, suggestions or generation, but
  it does not create Canonical facts or block the underlying task.
- **Browser is in-product and controlled.** SYS-06 uses the existing SYSTEM
  browser and permission contracts. The product scope is browser work, not
  general operating-system or desktop control.

- **CTH** 是以 Subject 为中心的商业运营。保留已授权 Subject、业务范围、来源
  关系和 Owner 提供的真实结果。
- **BMP** 是以品牌/市场为中心的品牌与市场工作。保留品牌、市场、竞品、创作者
  和 Campaign 上下文，不把 CTH 页面换名为 BMP。
- **Shared 创作可独立使用。** 用户可从现有 Shared 入口直接开始研究、提案、
  视频或播客工作，无须先创建 CTH/BMP 任务。把 Shared 成果关联到业务任务是
  可选操作，并须保留原来源域与对象上下文。
- **分析由后端能力驱动。** 确定性计算和正常业务流程必须在没有模型、外部 AI
  API、GPU 或推理服务时可用。AI 可以补充解释、建议或生成，但不生产
  Canonical 事实，也不阻断基础任务。
- **浏览器在产品内受控运行。** SYS-06 使用现有 SYSTEM 浏览器与权限合同。产品
  范围是浏览器工作，不包含通用操作系统或桌面控制。

## Product Core connection｜Product Core 连接

The default Core URL is `http://127.0.0.1:8201` for native clients. In the Web
Workspace, the Core URL is the current page's origin; a browser build must not
silently send requests to a visitor's localhost. An authorized device/build may
override the URL with:

```text
--dart-define=LUMENIS_CORE_BASE_URL=<authorized-core-url>
```

`LUMENIS_CORE_BASE_URL` is canonical. `LUMENIS_CORE_URL` remains a migration
alias, and the canonical value wins when both are present. Product Core requests
do not follow redirects, preventing context headers from being forwarded to
another origin.

原生客户端默认连接 `http://127.0.0.1:8201`。Web Workspace 使用当前页面源站作为
Core 地址；浏览器版本不得静默连接访问者自己的 localhost。经授权的设备或构建
可使用以下参数指定地址：

```text
--dart-define=LUMENIS_CORE_BASE_URL=<authorized-core-url>
```

`LUMENIS_CORE_BASE_URL` 是规范参数。迁移兼容别名 `LUMENIS_CORE_URL` 仍可读取；
两者同时存在时以规范参数为准。Product Core 请求不跟随重定向，避免上下文请求
头被转发到其他源站。

Existing integration contracts include:

```text
GET /api/experience/runtime/identity
GET /api/experience/screen/<screen_id>
GET /api/settings/subjects?domain_id=CTH
GET /api/auth/config
```

现有集成合同包括以上路由。Screen/ViewModel 数据必须经由其真实 Owner、
Permission 和 Evidence 关系；合同存在不等于接口或用户流程已验收。

### Transport authentication and account boundary｜传输认证与产品账户边界

- Native loopback clients may read the existing Core Basic Auth header from
  `GET /api/auth/config` when Core transport authentication is enabled. The
  header stays in process memory and is transport authentication, not an OEVIRA
  product account.
- Web builds never request or retain a reusable local Basic credential. The
  App never requests that credential from a remote Core or sends it to a
  non-loopback host. Authenticated remote Core transport belongs to the
  existing deployment-side path.
- Authenticated requests do not follow redirects. Do not forward Subject,
  BrandFocus, actor or authorization context across origins.
- CTH Subject selection metadata requires the existing server-side
  `subject_registry/read` Permission. That permission does not grant access to
  business data for every Subject.

- 原生端连接 loopback Core 时，如启用了传输认证，可从
  `GET /api/auth/config` 读取既有 Core Basic Auth 请求头。该请求头仅保存在进程
  内存中，属于传输认证，不是寰意产品账户。
- Web 构建不得请求或保留可复用的本地 Basic 凭据。应用不得向远端 Core 请求该
  凭据，也不得将其发送到非 loopback 主机。远端 Core 认证沿用现有部署侧传输路径。
- 已认证请求不跟随重定向。不得跨源转发 Subject、BrandFocus、actor 或授权上下文。
- CTH Subject 选择元数据须经过服务端既有 `subject_registry/read` Permission；
  这项权限不等于取得任意 Subject 的业务数据权限。

## Web Workspace build and hosting｜Web Workspace 构建与托管

Build the same Flutter application target with:

```powershell
Set-Location app
flutter build web --release --no-web-resources-cdn
```

The source-owned Flutter bootstrap resolves CanvasKit from the document base
URL. Publish the complete `build/web/` output, including `canvaskit/`. This
bundles the renderer; it does not make Core reads or AI execution available
offline. The existing Flask adapter
`lumenis/system/runtime/workspace_host.py` serves the build and rewrites
extensionless `/workspace/*` document requests to `index.html`. Missing assets
remain 404 and a missing build remains unavailable. This adapter does not own
Product Core APIs or restore the retired template frontend.

使用同一 Flutter 应用目标构建 Web：

```powershell
Set-Location app
flutter build web --release --no-web-resources-cdn
```

Flutter 源码维护的 bootstrap 从文档基础 URL 定位 CanvasKit。发布完整
`build/web/`，包括 `canvaskit/`。这只把渲染器纳入构建，不代表 Core 读取或 AI
执行可以离线使用。现有 Flask 适配器
`lumenis/system/runtime/workspace_host.py` 提供构建产物服务，并将无扩展名的
`/workspace/*` 文档请求重写到 `index.html`。缺失资源保持 404，缺少构建产物时
明确不可用。该适配器不拥有 Product Core API，也不恢复已退役的模板前端。

Before accepting a Web build, inspect its generated manifest, icons, fonts,
renderer and `main.dart.js`. Same-origin routing, TLS, access control and actual
user workflows require their own environment-specific verification.

验收 Web 构建前，核对生成的 manifest、图标、字体、渲染器和 `main.dart.js`。
同源路由、TLS、访问控制及真实用户流程需要在各自目标环境独立核验。

### Windows build path｜Windows 构建路径

If the local MSVC/Flutter toolchain cannot handle the Unicode checkout path,
use an unused, verified `subst` drive mapped to this same checkout, then build
from its `app/` directory. Do not overwrite an existing mapping or create a
second repository/data directory. CMake caches retain their path; re-establish
the same mapping for a later incremental build. Build output remains under the
canonical checkout's `app/build/` directory.

如果本机 MSVC/Flutter 工具链无法处理 Unicode 仓库路径，可使用一个未占用且核验
过的 `subst` 驱动器映射到同一仓库，再从映射下的 `app/` 目录构建。不得覆盖已有
映射，也不得创建第二份仓库或数据目录。CMake 缓存会保留构建路径，后续增量构建
须重新建立同一映射。构建产物仍位于规范仓库的 `app/build/` 下。

## Shared media playback｜Shared 媒体播放

The SH-01 workbench reads a saved content-project result through the existing
Core, Artifact and Permission path. Players receive authorized returned media
bytes; they must not receive a platform source URL, Cookie or Core credential.
Windows playback uses `video_player` with the bounded `video_player_win`
adapter for authorized local MP4/WAV lease files. Web playback uses a browser
media element for the same returned bytes. Codec/player failures remain
explicit; the App must not download codecs or claim media played when it did
not. Editing creates a distinct version and does not alter the prior export or
its playhead.

SH-01 工作台通过现有 Core、Artifact 和 Permission 路径读取已保存的内容工程结果。
播放器只能接收已授权返回的媒体字节，不得接收平台原始 URL、Cookie 或 Core 凭据。
Windows 使用 `video_player` 和受限的 `video_player_win` 适配器播放已授权的本地
MP4/WAV 租约文件；Web 使用浏览器媒体元素播放相同返回字节。编解码器或播放器错误
必须如实显示；应用不得下载编解码器，也不得在未播放时声称播放成功。编辑应生成
独立版本，不改变旧导出或旧版本的播放头状态。

## Experience and implementation｜体验与实现

The sole UI/UX authority is
[`LUMENIS-EXPERIENCE-CONSTITUTION.md`](../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md),
with each screen's current contract under
[`contracts/experience/screen-specifications/`](../contracts/experience/screen-specifications/).
Keep each screen's task, hierarchy and interaction specific; shared components
may share accessible behavior and tokens, not flatten different jobs into a
generic template. Bind actions to their existing API/ViewModel, Permission,
Evidence lineage, honest states and recovery behavior. Never invent data or
successful actions to make a screen look complete.

唯一 UI/UX 权威是
[`LUMENIS-EXPERIENCE-CONSTITUTION.md`](../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)，
各屏当前合同位于
[`contracts/experience/screen-specifications/`](../contracts/experience/screen-specifications/)。
每个屏幕保留自己的任务、层级和交互路径；共享组件可以复用无障碍行为和设计变量，
不能把不同任务压平成通用模板。每项操作都须绑定既有 API/ViewModel、Permission、
Evidence 来源关系、真实状态和恢复行为。不得为使界面显得完整而虚构数据或成功操作。

Keep these data states distinct: `UNKNOWN`, `NOT_AVAILABLE`, `NOT_COLLECTED`,
`STALE`, `BLOCKED` and `ERROR`. Missing values are not zero, and a route,
fixture, build or HTTP response is not proof of a working user task.

保持以下数据状态彼此区分：`UNKNOWN`、`NOT_AVAILABLE`、`NOT_COLLECTED`、
`STALE`、`BLOCKED` 和 `ERROR`。缺失值不等于零；路由、fixture、构建或 HTTP
响应都不能单独证明用户任务正常工作。

The app uses Flutter's shipped stack: `go_router` for URL/deep-link presentation
state and `http` for browser-safe Core transport. Do not add a parallel
framework or move business rules into widgets, controllers or local storage.
The version authority for the Flutter/Dart toolchain is `toolchain.json`.

应用使用现有 Flutter 技术栈：`go_router` 管理 URL/深链接呈现状态，`http` 提供
适用于浏览器的 Core 传输。不得引入平行框架，也不得把业务规则转移到 Widget、
Controller 或本地存储。Flutter/Dart 工具链版本以 `toolchain.json` 为准。

## Development commands｜开发命令

From the repository root, run Flutter commands in `app/`. These commands provide engineering checks;
they do not substitute for the real Core-backed user operation, persistence,
revision, reopen and recovery required by the applicable delivery contract.

从仓库根目录运行以下 Flutter 命令。它们用于工程检查，不能替代适用交付合同要求
的真实 Core 用户操作、持久化、修订、重开和恢复验收。

```powershell
Set-Location app
flutter pub get
flutter analyze
flutter test --no-pub
flutter build web --release --no-web-resources-cdn
```

For native targets, use the platform's supported Flutter toolchain. Native
Desktop targets are Windows and macOS; the native Mobile target is iOS. Browser
access remains available independently of the host operating system.

原生目标须使用对应平台受支持的 Flutter 工具链。原生桌面目标为 Windows 和
macOS，原生移动目标为 iOS。浏览器访问不受客户端操作系统范围影响。

### Windows paths｜Windows 中文路径构建

From the repository root, use PowerShell 7.2+ and the installed, version-matched
Flutter SDK in an ASCII path:

```powershell
pwsh -NoProfile -File app/tool/build_windows.ps1 -FlutterSdk '<installed Flutter SDK>'
```

This entry builds the same `app/` through a verified ASCII directory junction
under the current user's local application data. It prevents narrow-argument
encoding failures in `gen_snapshot` without relocating source or changing the
SDK, Windows language, drive mappings or user environment. `-AliasRoot` can
select another ASCII location outside `app/`; an existing unrelated path is
refused. Use this entry consistently and do not run concurrent Flutter builds
against the same app. Required dependencies must already be installed; the
command uses `--no-pub`.

When the build path changes, only generated CMake cache metadata and Flutter's
last-output marker are archived. Logs, actual exit codes, archived paths and
the executable hash are saved in ignored `build/native-build-receipts/`.
The executable remains `build/windows/x64/runner/Release/lumenis_app.exe`.
Preserve its neighboring DLLs and `data/` when running or packaging it.

在仓库根目录使用上述入口，并指定版本匹配且位于英文路径的 Flutter SDK。
入口通过经校验的英文目录联接访问同一份源码，处理原生编译器的中文参数转码
问题；不会迁移工程或修改 SDK、系统语言、盘符映射和用户环境变量。
构建路径变化时，仅归档生成缓存和上次输出标记；日志、真实退出码和产物哈希
保存在 `build/native-build-receipts/`。同一应用不可并发构建。
构建成功与实际界面、业务流程验收分别记录。

## External references and license boundaries｜外部参考与许可边界

- [`motion-web`](https://github.com/Zachary-1012/motion-web) is reading-only
  research. Its CC BY-NC 4.0 license bars commercial use of its Skill, prompts,
  cases and derivative workflows. Do not bring its code, assets, cases,
  parameters, verification recipes or derivative workflows into OEVIRA.
- The public [Toss Design System guide](https://developers-apps-in-toss.toss.im/landing-page/landing-page-en/design/components)
  may inform documentation clarity and consistency only. Its UI Kit materials
  are limited to the Apps in Toss service. Do not reuse its components, assets,
  visual patterns or screen layouts.
- Record each permitted reference's source, abstract principle and the distinct
  OEVIRA task/composition it informs. Third-party licenses remain theirs.

- [`motion-web`](https://github.com/Zachary-1012/motion-web) 仅供阅读研究。其
  CC BY-NC 4.0 许可禁止将 Skill、提示词、案例及衍生工作流用于商业用途。不得把其
  代码、素材、案例、参数、验证方案或衍生工作流带入寰意。
- 公开的 [Toss Design System 指南](https://developers-apps-in-toss.toss.im/landing-page/landing-page-en/design/components)
  仅可用于参考文档清晰度和一致性实践。其 UI Kit 材料仅限 Apps in Toss 服务使用；
  不得复用其组件、素材、视觉模式或屏幕布局。
- 对允许参考的材料，记录来源、抽象原则和受其启发的寰意独立任务/构图。第三方
  许可证仍归其权利人所有。
