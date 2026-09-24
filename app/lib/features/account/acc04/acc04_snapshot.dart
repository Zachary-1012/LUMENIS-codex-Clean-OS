enum Acc04GuardState { available, blocked, unavailable, unknown }

class Acc04Snapshot {
  const Acc04Snapshot({
    required this.guardState,
    required this.productAccountDeferred,
    required this.recoveryPaths,
    this.reason,
    this.generatedAt,
  });

  final Acc04GuardState guardState;
  final bool productAccountDeferred;
  final List<Acc04RecoveryPath> recoveryPaths;
  final String? reason;
  final String? generatedAt;

  factory Acc04Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'ACC-04') {
      throw const FormatException('ACC-04 response is not valid.');
    }
    final bound = response['bound'] == true && response['source'] == 'runtime';
    final guard = _asMap(response['guard']);
    final paths = <Acc04RecoveryPath>[];
    final rawPaths = guard?['recovery_paths'];
    if (rawPaths is List) {
      for (final path in rawPaths) {
        switch (path) {
          case 'retry' || 'recheck':
            paths.add(Acc04RecoveryPath.recheck);
          case 'switch_context' || 'switch':
            paths.add(Acc04RecoveryPath.switchContext);
          case 'request_access' || 'request':
            paths.add(Acc04RecoveryPath.requestAccess);
          case 'return':
            paths.add(Acc04RecoveryPath.returnToWorkspace);
        }
      }
    }
    if (paths.isEmpty) paths.add(Acc04RecoveryPath.recheck);
    return Acc04Snapshot(
      guardState: bound && guard != null
          ? Acc04GuardState.available
          : Acc04GuardState.unavailable,
      productAccountDeferred: true,
      recoveryPaths: paths.toSet().toList(growable: false),
      reason: _safeText(guard?['reason'] ?? response['note']),
      generatedAt: _safeText(response['generated_at']),
    );
  }

  factory Acc04Snapshot.blocked() => const Acc04Snapshot(
    guardState: Acc04GuardState.blocked,
    productAccountDeferred: true,
    recoveryPaths: [Acc04RecoveryPath.recheck],
  );

  factory Acc04Snapshot.unavailable() => const Acc04Snapshot(
    guardState: Acc04GuardState.unavailable,
    productAccountDeferred: true,
    recoveryPaths: [Acc04RecoveryPath.recheck],
  );
}

enum Acc04RecoveryPath {
  recheck,
  switchContext,
  requestAccess,
  returnToWorkspace,
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

String? _safeText(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 180) {
    return null;
  }
  final text = value.trim();
  final lower = text.toLowerCase();
  if (text.contains(RegExp(r'[\r\n\x00]')) ||
      text.contains('/') ||
      text.contains('\\') ||
      lower.contains('token') ||
      lower.contains('secret') ||
      lower.contains('password') ||
      lower.contains('provider=') ||
      lower.contains('model=')) {
    return null;
  }
  return text;
}
