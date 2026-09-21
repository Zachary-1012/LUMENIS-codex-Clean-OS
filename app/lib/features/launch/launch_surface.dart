import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../shell/lumenis_workspace_shell.dart';

class LaunchSurface extends StatefulWidget {
  const LaunchSurface({required this.client, super.key});

  final LumenisCoreClient client;

  @override
  State<LaunchSurface> createState() => _LaunchSurfaceState();
}

class _LaunchSurfaceState extends State<LaunchSurface> {
  late Future<_LaunchState> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void didUpdateWidget(covariant LaunchSurface oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client) {
      oldWidget.client.clearCredentials();
      _future = _load();
    }
  }

  @override
  void dispose() {
    widget.client.clearCredentials();
    super.dispose();
  }

  Future<_LaunchState> _load() async {
    final runtime = await widget.client.runtimeIdentity();
    if (runtime['ok'] != true) {
      throw const LumenisCoreException(
        'LUMENIS Core returned an invalid runtime identity.',
      );
    }

    return _LaunchState(
      runtime: runtime,
      subjects: const [],
      subjectDirectoryMessage: '主体目录授权尚未接入；其他工作区不受影响。',
    );
  }

  void _retry() {
    widget.client.clearCredentials();
    setState(() {
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
              if (error is LumenisCoreException &&
                  (error.statusCode == 401 || error.statusCode == 403)) {
                return _AccessDenied(
                  statusCode: error.statusCode!,
                  onRetry: _retry,
                );
              }
              return _Failure(onRetry: _retry);
            }
            return _Ready(client: widget.client, state: snapshot.requireData);
          },
        ),
      ),
    );
  }
}

class _Ready extends StatelessWidget {
  const _Ready({required this.client, required this.state});

  final LumenisCoreClient client;
  final _LaunchState state;

  @override
  Widget build(BuildContext context) {
    return LumenisWorkspaceShell(
      client: client,
      runtime: state.runtime,
      subjects: state.subjects,
      subjectDirectoryMessage: state.subjectDirectoryMessage,
    );
  }
}

class _AccessDenied extends StatelessWidget {
  const _AccessDenied({required this.statusCode, required this.onRetry});

  final int statusCode;
  final VoidCallback onRetry;

  String get _title => statusCode == 403 ? '当前核心请求被拒绝' : '序境核心暂不可访问';

  String get _detail => statusCode == 403
      ? 'LUMENIS Core 返回 HTTP 403。请检查当前运行范围与权限后重试。'
      : 'LUMENIS Core 返回 HTTP 401。请检查服务端连接配置后重试。';

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
              Text(
                _title,
                style: const TextStyle(
                  color: LumenisTheme.foreground,
                  fontSize: 24,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 10),
              Semantics(
                liveRegion: true,
                child: Text(
                  _detail,
                  style: const TextStyle(
                    color: LumenisTheme.muted,
                    height: 1.5,
                  ),
                ),
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
