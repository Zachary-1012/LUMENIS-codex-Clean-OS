enum Acc03RuntimeState { connected, degraded, unavailable, unknown }

enum Acc03Destination { commerce, brand, ai }

class Acc03StartupCheck {
  const Acc03StartupCheck({required this.name, required this.state});

  final String name;
  final Acc03RuntimeState state;
}

class Acc03LaunchCard {
  const Acc03LaunchCard({
    required this.destination,
    required this.title,
    required this.description,
    required this.domain,
  });

  final Acc03Destination destination;
  final String title;
  final String description;
  final String domain;
}

class Acc03Snapshot {
  const Acc03Snapshot({
    required this.runtimeState,
    required this.contextState,
    required this.launchCards,
    required this.startupChecks,
    this.currentView,
  });

  final Acc03RuntimeState runtimeState;
  final Acc03RuntimeState contextState;
  final List<Acc03LaunchCard> launchCards;
  final List<Acc03StartupCheck> startupChecks;
  final String? currentView;

  factory Acc03Snapshot.fromResponses({
    required Map<String, dynamic> identity,
    Map<String, dynamic>? context,
  }) {
    if (identity['ok'] != true) {
      throw const FormatException('ACC-03 identity response is not valid.');
    }
    final guardian = _asMap(identity['runtime_guardian']);
    final runtimeState = _parseState(guardian?['overall']);
    final contextMap = _asMap(context?['context']);
    final contextEnvelopeValid =
        context?['ok'] == true &&
        context?['contract'] == 'lumenis.context.v1' &&
        context?['selection_only'] == true &&
        contextMap != null;
    final contextState = contextMap == null
        ? Acc03RuntimeState.unknown
        : !contextEnvelopeValid
        ? Acc03RuntimeState.unavailable
        : switch (contextMap['mode']) {
            'GLOBAL_ALL' || 'FOCUS' => Acc03RuntimeState.connected,
            _ => Acc03RuntimeState.unavailable,
          };
    final viewName = contextEnvelopeValid
        ? _safeText(_asMap(contextMap['display_name'])?['zh']) ??
              _safeText(_asMap(contextMap['display_name'])?['en'])
        : null;

    return Acc03Snapshot(
      runtimeState: runtimeState,
      contextState: contextState,
      currentView: viewName,
      launchCards: const [
        Acc03LaunchCard(
          destination: Acc03Destination.commerce,
          title: '商业运营',
          description: '进入主体优先的运营工作区。',
          domain: 'CTH',
        ),
        Acc03LaunchCard(
          destination: Acc03Destination.brand,
          title: '品牌市场',
          description: '进入品牌与市场工作区。',
          domain: 'BMP',
        ),
        Acc03LaunchCard(
          destination: Acc03Destination.ai,
          title: '智能任务',
          description: '进入可审阅的智能任务入口。',
          domain: 'AI',
        ),
      ],
      startupChecks: [
        Acc03StartupCheck(name: '工作区入口', state: runtimeState),
        Acc03StartupCheck(name: '查看范围', state: contextState),
      ],
    );
  }
}

Acc03RuntimeState _parseState(Object? value) =>
    switch ('$value'.toLowerCase()) {
      'ok' || 'healthy' || 'available' => Acc03RuntimeState.connected,
      'degraded' || 'warning' || 'partial' => Acc03RuntimeState.degraded,
      'offline' || 'unavailable' || 'error' => Acc03RuntimeState.unavailable,
      _ => Acc03RuntimeState.unknown,
    };

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
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
