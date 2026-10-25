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

Use the existing [`tool/build_windows.ps1`](tool/build_windows.ps1) entry and
the Windows instructions below. Its verified ASCII junction addresses Unicode
compiler paths while keeping the same checkout and data ownership. Build output
remains under the canonical checkout's `app/build/` directory.

使用既有 [`tool/build_windows.ps1`](tool/build_windows.ps1) 入口和下方 Windows
说明。入口通过经校验的英文目录联接处理编译器的 Unicode 路径问题，保留同一份
仓库和数据归属。构建产物仍位于规范仓库的 `app/build/` 下。

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
Flutter SDK in an ASCII path. For a Windows portable bundle, build Web first,
then Windows, using the same explicit authorized loopback Core URL and Python
executable. Replace the SDK path and choose the authorized port for the bundle:

```powershell
$flutterSdk = '<installed Flutter SDK>'
$python = (Resolve-Path .venv/Scripts/python.exe).Path
$coreUrl = 'http://127.0.0.1:58724'
$projectAlias = '<existing verified ASCII app path>'

pwsh -NoProfile -File app/tool/build_windows.ps1 -BuildWeb `
  -FlutterSdk $flutterSdk -PythonExecutable $python -CoreBaseUrl $coreUrl `
  -ProjectAlias $projectAlias

pwsh -NoProfile -File app/tool/build_windows.ps1 `
  -FlutterSdk $flutterSdk -PythonExecutable $python `
  -CoreBaseUrl $coreUrl -AppCoreBaseUrl $coreUrl -ProjectAlias $projectAlias
```

`-BuildWeb` invokes `flutter build web --release --no-pub`; the Windows entry
invokes `flutter build windows --release --no-pub`. Both pass the explicit
`LUMENIS_CORE_BASE_URL` Dart define. Build one target at a time. These commands
compile files; they do not start or reuse a running Core.

Both successful builds write `verified-web.json` and `verified-windows.json`
under `app/build/native-build-receipts/`. The receipts bind the actual build
arguments, shared app sources, locked dependency inputs, Flutter toolchain and
complete output hashes. Bundle assembly requires matching source snapshots and
Core endpoints and rechecks both outputs. Matching version numbers alone do not
qualify; a raw `flutter build` does not create these bundle receipts. Rebuild
through this entry after changing app sources, dependencies or build settings.
Backend-only or governance changes do not change the shared app source identity.
Asset and font manifests, declared assets, custom fonts and Material Icons must
also exist with valid bundled bytes before a verified receipt can be issued.

The Windows entry builds the same `app/` through a verified ASCII directory junction
under the current user's local application data. It prevents narrow-argument
encoding failures in `gen_snapshot` without relocating source or changing the
SDK, Windows language, drive mappings or user environment. `-AliasRoot` can
select another ASCII location outside `app/`; an existing unrelated path is
refused. Use this entry consistently and do not run concurrent Flutter builds
against the same app. Required dependencies must already be installed; the
command uses `--no-pub`.

If the toolchain needs an already mapped ASCII app path for native plugin
links, pass `-ProjectAlias '<existing mapped app path>'`. Directory-handle
identity must match this exact checkout; an identical source copy is refused.
The helper neither creates nor removes drive mappings.
Use the same alias for Web and Windows. If no existing mapped path is needed,
omit `-ProjectAlias` from both commands to use the same default junction. When
the Web output spelling changes, only the generated last-build marker is
archived; source assets and prior build outputs are not deleted by the helper.

When the build path changes, only generated CMake cache metadata and Flutter's
last-output marker are archived. Logs, actual exit codes, archived paths and
the executable hash are saved in ignored `build/native-build-receipts/`.
The executable remains `build/windows/x64/runner/Release/lumenis_app.exe`.
Preserve its neighboring DLLs and `data/` when running or packaging it.

制作 Windows 可移植包时，在仓库根目录依次执行上述 Web、Windows 构建命令，
指定同一个获准的 loopback Core 地址、Python 和版本匹配且位于英文路径的
Flutter SDK。示例中的 SDK 路径和端口须按实际授权配置替换。两个目标均使用
release、`--no-pub` 和显式 `LUMENIS_CORE_BASE_URL`，不可并发构建；命令只编译
文件，不启动或复用运行中的 Core。

构建成功后，`app/build/native-build-receipts/` 中生成 `verified-web.json` 和
`verified-windows.json`，绑定实际构建参数、共享应用源码、锁定依赖输入、Flutter
工具链和完整产物哈希。组装时须满足同源码快照、同 Core 地址，并重新核对两套
产物；版本号相同不能代替这些核对。直接运行 `flutter build` 不生成这类打包
收据。应用源码、依赖或构建配置改变后，须通过此入口重新构建；仅后端或治理
文件改变不会改变共享应用源码身份。
签发收据前还会核对资产与字体清单、声明的素材、自定义字体和 Material Icons
实际存在且包内字节有效，缺资源不能仅凭编译退出码记为构建有效。

入口通过经校验的英文目录联接访问同一份源码，处理原生编译器的中文参数转码
问题；不会迁移工程或修改 SDK、系统语言、盘符映射和用户环境变量。
构建路径变化时，仅归档生成缓存和上次输出标记；日志、真实退出码和产物哈希
保存在 `build/native-build-receipts/`。同一应用不可并发构建。
构建成功与实际界面、业务流程验收分别记录。

如原生插件链接要求使用已有英文映射路径，可传入
`-ProjectAlias '<已有映射中的 app 路径>'`。入口通过目录句柄核对它确实指向同一份
工程，拒绝内容相同的另一份源码副本；不会创建、删除或更改盘符映射。
Web 和 Windows 必须使用同一映射路径；无需显式映射时，从两条命令同时省略
`-ProjectAlias`，使用相同的默认联接。Web 输出路径写法改变时，只归档生成的
上次构建标记；入口不删除源码素材或已有构建产物。

After both receipts are valid, the same entry's `-BundleOnly` mode assembles the
existing build without invoking Flutter. Supply an explicit new `-BundleOutput`,
the same `-CoreBaseUrl` and `-AppCoreBaseUrl`, and the selected installed
`-PythonExecutable`, `-PythonSitePackages`, `-MediaDirectory`, `-MediaNotices`,
`-VCRuntimeDirectory` and `-VCRuntimeNotices`. An in-project output must be a new
ignored `app/build/distribution/OEVIRA-<version>` directory. Existing output is
refused. The package includes Core, Web, the Windows runner, Python and selected
dependencies, FFmpeg, the release CRT and their recorded notices; it is a portable
bundle, not an installer or a redistribution-clearance decision.

Launch the package with `Start-OEVIRA.cmd`. To select a data root explicitly, use
its `core/scripts/start_production.ps1 -DesktopBundle -DataRoot <absolute-path>`.
The default is `%LOCALAPPDATA%/OEVIRA/UserData`, outside the package. An existing
nonempty unmarked root requires deliberate `-AdoptExistingDataRoot` adoption;
initialization preserves existing databases. No developer database, credential
or personal configuration is included. Startup refuses an occupied bundle port.

两份收据有效后，使用同一入口的 `-BundleOnly` 组装现有产物，不再调用 Flutter。
须显式提供新的 `-BundleOutput`、相同的 `-CoreBaseUrl` 与 `-AppCoreBaseUrl`，以及
选定的已安装 Python、依赖目录、媒体目录、发行版 CRT 和各自许可原文，对应参数
为上文列出的 `-PythonExecutable` 至 `-VCRuntimeNotices`。项目内输出只允许新的、
已忽略的 `app/build/distribution/OEVIRA-<version>` 目录，拒绝覆盖已有输出。包内
包含 Core、Web、Windows 程序、Python 与选定依赖、FFmpeg、发行版 CRT 及许可
记录；这是可移植包，不是安装器，也不代表已获公开再分发许可。

使用包内 `Start-OEVIRA.cmd` 启动；显式选数据根时，使用包内
`core/scripts/start_production.ps1 -DesktopBundle -DataRoot <绝对路径>`。默认数据
根为包外 `%LOCALAPPDATA%/OEVIRA/UserData`。已有非空且无归属标记的数据根须
明确使用 `-AdoptExistingDataRoot` 接管，初始化保留已有数据库。包内不携带开发者
数据库、凭据或个人配置；启动时若指定端口已被占用，会拒绝启动。

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
