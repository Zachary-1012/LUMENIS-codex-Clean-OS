import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../product/product_domain.dart';
import '../../shell/lumenis_workspace_shell.dart';

class LaunchSurface extends StatefulWidget {
  const LaunchSurface({required this.client, super.key});

  final LumenisCoreClient client;

  @override
  State<LaunchSurface> createState() => _LaunchSurfaceState();
}

class _LaunchSurfaceState extends State<LaunchSurface> {
  late Future<_LaunchState> _future;
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _authenticating = false;
  String? _authenticationError;

  @override
  void initState() {
    super.initState();
    widget.client.onAccessFailure = _handleAccessFailure;
    _future = _load();
  }

  @override
  void didUpdateWidget(covariant LaunchSurface oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client) {
      oldWidget.client.onAccessFailure = null;
      oldWidget.client.clearCredentials();
      widget.client.onAccessFailure = _handleAccessFailure;
      _future = _load();
    }
  }

  @override
  void dispose() {
    widget.client.onAccessFailure = null;
    widget.client.clearCredentials();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<_LaunchState> _load() async {
    final runtime = await widget.client.runtimeIdentity();
    if (runtime['ok'] != true) {
      throw const LumenisCoreException(
        'LUMENIS Core returned an invalid runtime identity.',
      );
    }

    // The Subject registry is an auxiliary browse surface. A registry read
    // failure must not prevent the live Product Core context from opening.
    final subjectDirectory = await _loadSubjects();
    return _LaunchState(
      runtime: runtime,
      subjects: subjectDirectory.subjects,
      subjectDirectoryMessage: subjectDirectory.message,
    );
  }

  Future<_SubjectDirectoryLoad> _loadSubjects() async {
    try {
      return _SubjectDirectoryLoad(subjects: await widget.client.subjects());
    } on LumenisCoreException catch (error) {
      if (error.statusCode == 401) rethrow;
      return _SubjectDirectoryLoad(
        subjects: const [],
        message: switch (error.statusCode) {
          403 => '账号没有 CTH 主体目录读取权限。',
          503 => '主体目录授权服务暂不可用。',
          _ => '主体目录未能读取；请从 CTH-02 查看准确状态。',
        },
      );
    } catch (_) {
      return const _SubjectDirectoryLoad(
        subjects: [],
        message: '主体目录响应无效；请从 CTH-02 查看准确状态。',
      );
    }
  }

  void _retry() {
    setState(() {
      _authenticationError = null;
      _future = _load();
    });
  }

  void _handleAccessFailure(LumenisCoreException error) {
    if (!mounted) return;
    setState(() {
      if (error.statusCode == 401) {
        _usernameController.clear();
        _passwordController.clear();
        _authenticationError = null;
      }
      _future = Future<_LaunchState>.error(error);
    });
  }

  Future<void> _authenticate() async {
    if (_authenticating) return;
    setState(() {
      _authenticating = true;
      _authenticationError = null;
    });

    try {
      await widget.client.authenticate(
        username: _usernameController.text,
        password: _passwordController.text,
      );
      await widget.client.authenticateAccount(
        username: _usernameController.text,
        password: _passwordController.text,
      );
      if (!mounted) {
        widget.client.clearCredentials();
        return;
      }
      _usernameController.clear();
      _passwordController.clear();
      setState(() {
        _authenticating = false;
        _authenticationError = null;
        _future = _load();
      });
    } on LumenisCoreException catch (error) {
      if (!mounted) return;
      setState(() {
        _authenticating = false;
        if (error.statusCode == 403) {
          _authenticationError = null;
          _future = Future<_LaunchState>.error(error);
        } else if (error.statusCode == 401) {
          _passwordController.clear();
          _authenticationError = '账号凭证无效或未获准登录，请重试。';
        } else {
          _authenticationError = '无法验证 Core 连接，请检查地址后重试。';
        }
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _authenticating = false;
        _authenticationError = '无法验证 Core 连接，请检查地址后重试。';
      });
    }
  }

  void _logout() {
    unawaited(widget.client.logout());
    _usernameController.clear();
    _passwordController.clear();
    setState(() {
      _authenticationError = null;
      _future = _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: LumenisTheme.canvas,
      child: SafeArea(
        child: FutureBuilder<_LaunchState>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const _Status(
                title: '序境',
                detail: '正在连接 LUMENIS Production Core…',
              );
            }
            if (snapshot.hasError) {
              final error = snapshot.error;
              if (error is LumenisCoreException && error.statusCode == 401) {
                return _LoginSurface(
                  usernameController: _usernameController,
                  passwordController: _passwordController,
                  error: _authenticationError,
                  busy: _authenticating,
                  onSubmit: _authenticate,
                );
              }
              if (error is LumenisCoreException && error.statusCode == 403) {
                return _AccessDenied(onRetry: _retry, onLogout: _logout);
              }
              return _Failure(onRetry: _retry);
            }
            return _Ready(
              client: widget.client,
              state: snapshot.requireData,
              onLogout: _logout,
            );
          },
        ),
      ),
    );
  }
}

class _ProductMap extends StatelessWidget {
  const _ProductMap();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          '产品边界 · INFORMATION ONLY',
          style: TextStyle(
            color: LumenisTheme.quiet,
            fontSize: 10,
            letterSpacing: 1.1,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 9),
        LayoutBuilder(
          builder: (context, constraints) => Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final domain in ProductDomain.values)
                SizedBox(
                  width: (constraints.maxWidth - 8) / 2,
                  child: _ProductDomainCard(domain: domain),
                ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        Text(
          'Agent Groups · ${CrossProductLayer.agentGroups.principle}',
          style: const TextStyle(
            color: LumenisTheme.muted,
            fontSize: 11,
            height: 1.4,
          ),
        ),
      ],
    );
  }
}

class _ProductDomainCard extends StatelessWidget {
  const _ProductDomainCard({required this.domain});

  final ProductDomain domain;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
      decoration: BoxDecoration(
        color: LumenisTheme.surfaceRaised,
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: LumenisTheme.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${domain.technicalId} · ${domain.zhName}',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: LumenisTheme.foreground,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            domain.principle,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: LumenisTheme.quiet,
              fontSize: 10,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
  }
}

class _Ready extends StatelessWidget {
  const _Ready({
    required this.client,
    required this.state,
    required this.onLogout,
  });

  final LumenisCoreClient client;
  final _LaunchState state;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return LumenisWorkspaceShell(
      client: client,
      runtime: state.runtime,
      subjects: state.subjects,
      subjectDirectoryMessage: state.subjectDirectoryMessage,
      onLogout: onLogout,
    );
  }
}

class _LoginSurface extends StatelessWidget {
  const _LoginSurface({
    required this.usernameController,
    required this.passwordController,
    required this.error,
    required this.busy,
    required this.onSubmit,
  });

  final TextEditingController usernameController;
  final TextEditingController passwordController;
  final String? error;
  final bool busy;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: Container(
            padding: const EdgeInsets.all(26),
            decoration: BoxDecoration(
              color: LumenisTheme.surface,
              border: Border.all(color: LumenisTheme.line),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'LUMENIS CORE ACCESS',
                  style: TextStyle(
                    color: LumenisTheme.cth,
                    fontSize: 11,
                    letterSpacing: 1.4,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  '登录序境',
                  style: TextStyle(
                    color: LumenisTheme.foreground,
                    fontSize: 27,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Core 访问与账号身份分别验证；Basic 凭证和账号会话令牌仅保存在本次运行内存中。',
                  style: TextStyle(color: LumenisTheme.muted, height: 1.5),
                ),
                const SizedBox(height: 22),
                const _ProductMap(),
                const SizedBox(height: 24),
                TextField(
                  key: const ValueKey('auth/username'),
                  controller: usernameController,
                  enabled: !busy,
                  autofocus: true,
                  autocorrect: false,
                  enableSuggestions: false,
                  keyboardType: TextInputType.text,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(
                    labelText: '用户名',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  key: const ValueKey('auth/password'),
                  controller: passwordController,
                  enabled: !busy,
                  obscureText: true,
                  enableSuggestions: false,
                  autocorrect: false,
                  textInputAction: TextInputAction.done,
                  onSubmitted: busy ? null : (_) => onSubmit(),
                  decoration: const InputDecoration(
                    labelText: '密码',
                    border: OutlineInputBorder(),
                  ),
                ),
                if (error != null) ...[
                  const SizedBox(height: 12),
                  Semantics(
                    liveRegion: true,
                    child: Text(
                      error!,
                      key: const ValueKey('auth/error'),
                      style: const TextStyle(color: LumenisTheme.danger),
                    ),
                  ),
                ],
                const SizedBox(height: 22),
                SizedBox(
                  height: 48,
                  child: FilledButton.icon(
                    key: const ValueKey('auth/submit'),
                    onPressed: busy ? null : onSubmit,
                    icon: busy
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.lock_open_rounded),
                    label: Text(busy ? '正在验证…' : '安全登录'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _AccessDenied extends StatelessWidget {
  const _AccessDenied({required this.onRetry, required this.onLogout});

  final VoidCallback onRetry;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.lock_outline_rounded,
                color: LumenisTheme.caution,
              ),
              const SizedBox(height: 14),
              const Text(
                '当前账号没有访问权限',
                style: TextStyle(
                  color: LumenisTheme.foreground,
                  fontSize: 24,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                'LUMENIS Core 返回 HTTP 403。请联系管理员确认该账号的访问范围。',
                style: TextStyle(color: LumenisTheme.muted, height: 1.5),
              ),
              const SizedBox(height: 22),
              Wrap(
                spacing: 12,
                runSpacing: 10,
                children: [
                  OutlinedButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh_rounded),
                    label: const Text('重新连接'),
                  ),
                  TextButton.icon(
                    key: const ValueKey('auth/logout-denied'),
                    onPressed: onLogout,
                    icon: const Icon(Icons.logout_rounded),
                    label: const Text('退出或更换账号'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Failure extends StatelessWidget {
  const _Failure({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 680),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'LUMENIS Core 未连接',
                style: TextStyle(
                  color: LumenisTheme.foreground,
                  fontSize: 24,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                '无法读取 LUMENIS Core。请检查 Core 地址与网络连接后重试。',
                style: TextStyle(color: LumenisTheme.muted, height: 1.5),
              ),
              const SizedBox(height: 22),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('重新连接'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Status extends StatelessWidget {
  const _Status({required this.title, required this.detail});

  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(height: 20),
            Text(
              title,
              style: const TextStyle(
                color: LumenisTheme.foreground,
                fontSize: 30,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 10),
            Text(detail, style: const TextStyle(color: LumenisTheme.muted)),
          ],
        ),
      ),
    );
  }
}

class _LaunchState {
  const _LaunchState({
    required this.runtime,
    required this.subjects,
    required this.subjectDirectoryMessage,
  });

  final Map<String, dynamic> runtime;
  final List<Map<String, dynamic>> subjects;
  final String? subjectDirectoryMessage;
}

class _SubjectDirectoryLoad {
  const _SubjectDirectoryLoad({required this.subjects, this.message});

  final List<Map<String, dynamic>> subjects;
  final String? message;
}
