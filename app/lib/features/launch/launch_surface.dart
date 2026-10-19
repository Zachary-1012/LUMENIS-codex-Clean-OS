import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../navigation/lumenis_workspace_routes.dart';
import '../../shell/lumenis_workspace_shell.dart';
import '../account/acc01/acc01_snapshot.dart';

class LaunchSurface extends StatefulWidget {
  const LaunchSurface({
    required this.client,
    this.initialScreenId = LumenisWorkspaceRoutes.rootScreenId,
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
  static const _loadingRuntime = <String, dynamic>{
    'ok': false,
    'state': 'LOADING',
    'runtime_available': false,
  };

  Map<String, dynamic> _runtime = _loadingRuntime;
  Map<String, dynamic>? _contextEnvelope;
  int _clientRevision = 0;
  int _runtimeRequest = 0;
  int _contextRequest = 0;

  @override
  void initState() {
    super.initState();
    _contextEnvelope = widget.client.currentContextEnvelope;
    _startReads(widget.client, _clientRevision);
  }

  @override
  void didUpdateWidget(covariant LaunchSurface oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client == widget.client) return;

    oldWidget.client.clearCredentials();
    _clientRevision++;
    _runtime = _loadingRuntime;
    _contextEnvelope = widget.client.currentContextEnvelope;
    _startReads(widget.client, _clientRevision);
  }

  @override
  void dispose() {
    widget.client.clearCredentials();
    super.dispose();
  }

  void _startReads(LumenisCoreClient client, int clientRevision) {
    unawaited(
      _loadRuntime(
        client,
        clientRevision: clientRevision,
        request: ++_runtimeRequest,
      ),
    );
    unawaited(
      _loadContext(
        client,
        clientRevision: clientRevision,
        request: ++_contextRequest,
      ),
    );
  }

  Future<void> _loadRuntime(
    LumenisCoreClient client, {
    required int clientRevision,
    required int request,
  }) async {
    Map<String, dynamic> runtime;
    try {
      final identity = await client.runtimeIdentity();
      if (identity['ok'] != true) {
        throw const FormatException(
          'OEVIRA Core returned an invalid runtime identity.',
        );
      }

      final snapshot = Acc01Snapshot.fromIdentity(identity);
      final state = switch (snapshot.runtimeHealth) {
        Acc01RuntimeHealth.healthy => 'CONNECTED',
        Acc01RuntimeHealth.degraded => 'DEGRADED',
        Acc01RuntimeHealth.unavailable => 'OFFLINE',
        Acc01RuntimeHealth.unknown => 'UNKNOWN',
      };
      runtime = <String, dynamic>{
        ...identity,
        'identity_ok': true,
        'ok': snapshot.runtimeConnected,
        'state': state,
        'health_state': snapshot.runtimeHealth.name.toUpperCase(),
        'runtime_available': snapshot.runtimeConnected,
      };
    } on LumenisCoreException catch (error) {
      final state = switch (error.statusCode) {
        401 => 'AUTH_REQUIRED',
        403 => 'ACCESS_UNAVAILABLE',
        null => 'OFFLINE',
        _ => 'ERROR',
      };
      runtime = <String, dynamic>{
        'ok': false,
        'state': state,
        'runtime_available': false,
        'status_code': error.statusCode,
        if (error.errorCode != null) 'error_code': error.errorCode,
        if (error.messageKey != null) 'message_key': error.messageKey,
      };
    } on Object {
      runtime = const <String, dynamic>{
        'ok': false,
        'state': 'ERROR',
        'runtime_available': false,
      };
    }

    if (!_isCurrentClient(client, clientRevision) ||
        request != _runtimeRequest ||
        !mounted) {
      return;
    }
    setState(() => _runtime = runtime);
  }

  Future<void> _loadContext(
    LumenisCoreClient client, {
    required int clientRevision,
    required int request,
  }) async {
    Map<String, dynamic>? contextEnvelope;
    try {
      contextEnvelope = await client.settingsContext();
    } on Object {
      // The shell owns context recovery and keeps an unavailable scope honest.
      contextEnvelope = null;
    }

    if (!_isCurrentClient(client, clientRevision) ||
        request != _contextRequest ||
        !mounted) {
      return;
    }
    setState(() => _contextEnvelope = contextEnvelope);
  }

  bool _isCurrentClient(LumenisCoreClient client, int clientRevision) =>
      clientRevision == _clientRevision && identical(client, widget.client);

  void _retryRuntime() {
    final client = widget.client;
    setState(() => _runtime = _loadingRuntime);
    unawaited(
      _loadRuntime(
        client,
        clientRevision: _clientRevision,
        request: ++_runtimeRequest,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: LumenisWorkspaceShell(
          key: const ValueKey('launch-workspace-shell'),
          client: widget.client,
          runtime: _runtime,
          contextEnvelope: _contextEnvelope,
          subjects: const [],
          subjectDirectoryMessage: null,
          initialScreenId: widget.initialScreenId,
          onScreenSelected: widget.onScreenSelected,
          onLocaleChanged: widget.onLocaleChanged,
          onRetryRuntime: switch (_runtime['state']) {
            'LOADING' || 'CONNECTED' => null,
            _ => _retryRuntime,
          },
        ),
      ),
    );
  }
}
