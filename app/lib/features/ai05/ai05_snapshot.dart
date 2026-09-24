enum Ai05BindingState { bound, fallbackDiagnostic, unavailable, blocked }

enum Ai05ProviderKind { local, optional, generic }

enum Ai05ProviderState { available, notReady, unavailable, unknown }

class Ai05ProviderStatus {
  const Ai05ProviderStatus({
    required this.kind,
    required this.state,
    this.latencyMs,
  });

  final Ai05ProviderKind kind;
  final Ai05ProviderState state;
  final num? latencyMs;
}

class Ai05Snapshot {
  const Ai05Snapshot({
    required this.bindingState,
    required this.providers,
    required this.callSeries,
    this.generatedAt,
  });

  final Ai05BindingState bindingState;
  final List<Ai05ProviderStatus> providers;
  final List<num> callSeries;
  final String? generatedAt;

  bool get isBound => bindingState == Ai05BindingState.bound;

  factory Ai05Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'AI-05') {
      throw const FormatException('AI-05 response is not valid.');
    }
    final providers = _parseProviders(
      response['providers'] ?? _runtimeItems(response['sections']),
    );
    final bound = response['bound'] == true && response['source'] == 'runtime';
    return Ai05Snapshot(
      bindingState: bound
          ? Ai05BindingState.bound
          : Ai05BindingState.unavailable,
      providers: providers,
      callSeries: _parseSeries(response['call_series']),
      generatedAt: _safeText(response['generated_at']),
    );
  }

  factory Ai05Snapshot.fromAi01Diagnostic(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'AI-01') {
      throw const FormatException('AI-01 diagnostic response is not valid.');
    }
    return Ai05Snapshot(
      bindingState: Ai05BindingState.fallbackDiagnostic,
      providers: _parseProviders(_runtimeItems(response['sections'])),
      callSeries: const [],
      generatedAt: _safeText(response['generated_at']),
    );
  }
}

List<Object?> _runtimeItems(Object? sections) {
  if (sections is! List) return const [];
  for (final item in sections) {
    if (item is! Map) continue;
    if (item['type'] == 'runtime') {
      final items = item['items'];
      return items is List ? items : const [];
    }
    if (item['type'] == 'split' && item['side'] is List) {
      final side = item['side'] as List;
      for (final sideItem in side) {
        if (sideItem is Map && sideItem['type'] == 'runtime') {
          final items = sideItem['items'];
          return items is List ? items : const [];
        }
      }
    }
  }
  return const [];
}

List<Ai05ProviderStatus> _parseProviders(Object? value) {
  if (value is! List) return const [];
  final result = <Ai05ProviderStatus>[];
  for (final item in value) {
    if (item is! Map) continue;
    final kind = _providerKind(item['name']);
    final rawState = item['state'] ?? 'unknown';
    final state = switch ('$rawState'.toLowerCase()) {
      'ok' || 'available' || 'ready' => Ai05ProviderState.available,
      'idle' || 'not_ready' || 'pending' => Ai05ProviderState.notReady,
      'offline' || 'unavailable' || 'error' => Ai05ProviderState.unavailable,
      _ => Ai05ProviderState.unknown,
    };
    final latency = item['latency_ms'];
    final safeLatency = latency is num && latency >= 0 && latency <= 600000
        ? latency
        : null;
    result.add(
      Ai05ProviderStatus(kind: kind, state: state, latencyMs: safeLatency),
    );
  }
  return result;
}

Ai05ProviderKind _providerKind(Object? value) {
  final name = value is String ? value.toLowerCase() : '';
  if (name.contains('ollama') ||
      name.contains('local') ||
      name.contains('本地')) {
    return Ai05ProviderKind.local;
  }
  if (name.contains('zhipu') ||
      name.contains('智谱') ||
      name.contains('optional')) {
    return Ai05ProviderKind.optional;
  }
  return Ai05ProviderKind.generic;
}

List<num> _parseSeries(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<num>()
      .where((item) => item >= 0 && item <= 100000000)
      .take(120)
      .toList(growable: false);
}

String? _safeText(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 120) {
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
