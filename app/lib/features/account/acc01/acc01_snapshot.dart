enum Acc01RuntimeHealth { healthy, degraded, unavailable, unknown }

class Acc01Snapshot {
  const Acc01Snapshot({
    required this.runtimeConnected,
    required this.runtimeHealth,
    required this.productAccountDeferred,
    required this.generatedAt,
    this.focusName,
  });

  final bool runtimeConnected;
  final Acc01RuntimeHealth runtimeHealth;
  final bool productAccountDeferred;
  final String? generatedAt;
  final String? focusName;

  factory Acc01Snapshot.fromIdentity(Map<String, dynamic> response) {
    if (response['ok'] != true) {
      throw const FormatException('ACC-01 identity response is not valid.');
    }

    final guardian = _asMap(response['runtime_guardian']);
    final health = switch (_safeText(guardian?['overall'])?.toLowerCase()) {
      'connected' || 'ok' || 'healthy' || 'available' =>
        Acc01RuntimeHealth.healthy,
      'degraded' || 'warning' || 'partial' => Acc01RuntimeHealth.degraded,
      'offline' || 'unavailable' || 'error' => Acc01RuntimeHealth.unavailable,
      _ => Acc01RuntimeHealth.unknown,
    };
    final focus = _asMap(response['focus_context']);

    return Acc01Snapshot(
      runtimeConnected: health == Acc01RuntimeHealth.healthy,
      runtimeHealth: health,
      productAccountDeferred: true,
      generatedAt: _safeText(response['generated_at']),
      focusName: _safeDisplayText(focus?['display_name']),
    );
  }
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

String? _safeText(Object? value) {
  if (value is! String || value.trim().isEmpty) return null;
  if (value.length > 120 || value.contains(RegExp(r'[\r\n\x00]'))) return null;
  return value.trim();
}

String? _safeDisplayText(Object? value) {
  final text = _safeText(value);
  if (text == null) return null;
  final lower = text.toLowerCase();
  if (text.contains('/') ||
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
