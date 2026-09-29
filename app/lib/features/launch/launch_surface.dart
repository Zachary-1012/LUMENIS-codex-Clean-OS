import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import '../../shell/lumenis_workspace_shell.dart';

class LaunchSurface extends StatefulWidget {
  const LaunchSurface({
    required this.client,
    this.initialScreenId = 'CTH-01',
    this.onScreenSelected,
    this.onLocaleChanged,
    super.key,
  });

  final LumenisCoreClient client;
  final String initialScreenId;
  final ValueChanged<String>? onScreenSelected;
  final ValueChanged<Locale?>? onLocaleChanged;

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
    Map<String, dynamic> runtime;
    try {
      runtime = await widget.client.runtimeIdentity();
      if (runtime['ok'] != true) {
        throw const LumenisCoreException(
          'LUMENIS Core returned an invalid runtime identity.',
        );
      }
    } on LumenisCoreException catch (error) {
      if (error.statusCode != 401 && error.statusCode != 403) rethrow;
      // Runtime identity is observability, not a product account gate. Keep
      // the real failure state in the shell while allowing the open workspace
      // to render its own truthful screen/data state.
      runtime = <String, dynamic>{
        'ok': false,
        'state': error.statusCode == 401
            ? 'AUTH_REQUIRED'
            : 'ACCESS_UNAVAILABLE',
        'runtime_available': false,
      };
    }

    Map<String, dynamic>? contextEnvelope;
    try {
      contextEnvelope = await widget.client.settingsContext();
    } on Object {
      // Context is a separate, recoverable workspace capability. Do not turn
      // a context lookup failure into a product-account launch gate.
      contextEnvelope = null;
    }

    return _LaunchState(
      runtime: runtime,
      contextEnvelope: contextEnvelope,
      subjects: const [],
      subjectDirectoryMessage: null,
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
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: FutureBuilder<_LaunchState>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              final copy = context.lumenisL10n;
              return _Status(
                title: copy.text('launch.connecting.title'),
                detail: copy.text('launch.connecting.detail'),
              );
            }
            if (snapshot.hasError) return _Failure(onRetry: _retry);
            return _Ready(
              client: widget.client,
              state: snapshot.requireData,
              initialScreenId: widget.initialScreenId,
              onScreenSelected: widget.onScreenSelected,
              onLocaleChanged: widget.onLocaleChanged,
            );
          },
        ),
      ),
    );
  }
}

class _Ready extends StatelessWidget {
  const _Ready({
    required this.client,
    required this.state,
    required this.initialScreenId,
    required this.onScreenSelected,
    required this.onLocaleChanged,
  });

  final LumenisCoreClient client;
  final _LaunchState state;
  final String initialScreenId;
  final ValueChanged<String>? onScreenSelected;
  final ValueChanged<Locale?>? onLocaleChanged;

  @override
  Widget build(BuildContext context) {
    return LumenisWorkspaceShell(
      client: client,
      runtime: state.runtime,
      contextEnvelope: state.contextEnvelope,
      subjects: state.subjects,
      subjectDirectoryMessage: state.subjectDirectoryMessage,
      initialScreenId: initialScreenId,
      onScreenSelected: onScreenSelected,
      onLocaleChanged: onLocaleChanged,
    );
  }
}

class _Failure extends StatelessWidget {
  const _Failure({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 680),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                copy.text('launch.service_unavailable.title'),
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontSize: 24,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                copy.text('launch.service_unavailable.detail'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 22),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(copy.text('launch.retry')),
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
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 30,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              detail,
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ],
        ),
      ),
    );
  }
}

class _LaunchState {
  const _LaunchState({
    required this.runtime,
    required this.contextEnvelope,
    required this.subjects,
    required this.subjectDirectoryMessage,
  });

  final Map<String, dynamic> runtime;
  final Map<String, dynamic>? contextEnvelope;
  final List<Map<String, dynamic>> subjects;
  final String? subjectDirectoryMessage;
}
