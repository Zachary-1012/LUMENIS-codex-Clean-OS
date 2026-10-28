# Flutter source package｜Flutter 源码包

`app/` holds the shared Flutter/Dart client source for the Web Workspace, Windows/macOS Desktop, and iOS Mobile Companion. It contains Core transport, feature repositories and view models, domain/state data, localization, platform adapters, and Flutter regression tests. It is a source package, not proof that a complete user-facing app is available.

`app/` 保存 Web Workspace、Windows/macOS 桌面端和 iOS Mobile Companion 共用的 Flutter/Dart 客户端源码，包括 Core 传输、功能仓储与 ViewModel、领域和状态数据、本地化、平台适配器及 Flutter 回归测试。源码包本身不代表完整用户应用已经可用。

Run and build commands require the complete application entrypoint (`lib/main.dart`) and its dependencies. Read the current source/release boundary in [CURRENT](../00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md) before selecting a target; package checks do not establish product availability.

运行及构建要求完整的 `lib/main.dart` 入口与其依赖。选择目标前先查 [CURRENT](../00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md) 的实际源码与发布边界；包检查不代表产品已可用。

## Source map｜源码目录

| Path / 路径 | Contents / 内容 |
| --- | --- |
| `lib/core/` | Core client and transport / Core 客户端与传输层 |
| `lib/features/` | Repositories, view models, snapshots, drafts, and owner data / 仓储、ViewModel、快照、草稿及 Owner 数据 |
| `lib/navigation/` | Navigation and leave-guard integration / 导航与离开保护集成 |
| `lib/l10n/` | Chinese, English, and Korean localized data / 中、英、韩本地化数据 |
| `lib/platform/` | Platform-specific adapters / 平台适配器 |
| `test/` | Flutter test sources / Flutter 测试源码 |
| `web/`, `windows/`, `macos/`, `ios/`, `android/`, `linux/` | Flutter platform projects and plugin integration / Flutter 平台工程与插件集成 |

## SDK and dependencies｜SDK 与依赖

[`toolchain.json`](toolchain.json) is the Flutter/Dart SDK version source. [`pubspec.yaml`](pubspec.yaml) declares package dependencies and assets; [`pubspec.lock`](pubspec.lock) records resolved versions. Use the Flutter SDK named by the toolchain file and the dependency versions in the lockfile.

[`toolchain.json`](toolchain.json) 是 Flutter/Dart SDK 版本来源；[`pubspec.yaml`](pubspec.yaml) 声明依赖和资源；[`pubspec.lock`](pubspec.lock) 记录解析后的版本。使用工具链文件指定的 Flutter SDK 与锁文件中的依赖版本。

From the repository root, package-level source checks are:

```powershell
Set-Location app
flutter analyze lib
flutter test --no-pub test/features/ai01/ai01_workspace_draft_test.dart
```

以上是在仓库根目录执行的源码包检查。它们不构建或启动完整产品；只有目标应用入口及对应实现补齐后，才有适用的 `flutter run` / `flutter build <target>` 命令。

## Product and experience references｜产品与体验权威

- [Repository instructions](../AGENTS.md)
- [Current source and acceptance](../00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)
- [Product Architecture](../00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)
- [Experience Constitution](../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)
- [Screen specifications](../contracts/experience/screen-specifications/)

产品范围、工程边界与体验要求以以上唯一权威及其导航为准；本 README 只说明 Flutter 源码包。
