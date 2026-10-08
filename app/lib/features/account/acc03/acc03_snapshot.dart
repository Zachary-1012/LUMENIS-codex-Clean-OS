enum Acc03RuntimeState { connected, degraded, unavailable, unknown, restricted }

enum Acc03Destination { commerce, brand, research, creation, ai }

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

const acc03HomeDestinations = <Acc03LaunchCard>[
  Acc03LaunchCard(
    destination: Acc03Destination.commerce,
    title: '商业运营',
    description: '查看运营脉络与经营工作。',
    domain: 'CTH',
  ),
  Acc03LaunchCard(
    destination: Acc03Destination.brand,
    title: '品牌市场',
    description: '从品牌与市场视角开展工作。',
    domain: 'BMP',
  ),
  Acc03LaunchCard(
    destination: Acc03Destination.research,
    title: '研究与资料',
    description: '查看研究输入与可引用材料。',
    domain: 'SH',
  ),
  Acc03LaunchCard(
    destination: Acc03Destination.creation,
    title: '内容创作',
    description: '进入现有内容与交付工作。',
    domain: 'SH',
  ),
];

class Acc03Snapshot {
  const Acc03Snapshot({
    required this.runtimeState,
    required this.contextState,
    required this.launchCards,
    required this.startupChecks,
    this.currentView,
    this.currentViewNames = const {},
  });

  final Acc03RuntimeState runtimeState;
  final Acc03RuntimeState contextState;
  final List<Acc03LaunchCard> launchCards;
  final List<Acc03StartupCheck> startupChecks;
  final String? currentView;
  final Map<String, String> currentViewNames;

  factory Acc03Snapshot.fromResponses({
    required Map<String, dynamic> identity,
    Map<String, dynamic>? context,
    Acc03RuntimeState? contextFailure,
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
    final contextState =
        contextFailure ??
        (contextMap == null
            ? Acc03RuntimeState.unknown
            : !contextEnvelopeValid
            ? Acc03RuntimeState.unavailable
            : switch (contextMap['mode']) {
                'GLOBAL_ALL' || 'FOCUS' => Acc03RuntimeState.connected,
                _ => Acc03RuntimeState.unavailable,
              });
    final viewNames = contextState == Acc03RuntimeState.connected
        ? _safeDisplayNames(contextMap?['display_name'])
        : const <String, String>{};
    final viewName =
        viewNames['zh-CN'] ??
        viewNames['zh'] ??
        viewNames['en'] ??
        viewNames['ko'];

    return Acc03Snapshot(
      runtimeState: runtimeState,
      contextState: contextState,
      currentView: viewName,
      currentViewNames: viewNames,
      launchCards: acc03HomeDestinations,
      startupChecks: [
        Acc03StartupCheck(name: '工作区入口', state: runtimeState),
        Acc03StartupCheck(name: '查看范围', state: contextState),
      ],
    );
  }
}

Map<String, String> _safeDisplayNames(Object? value) {
  if (value is! Map) return const {};
  final names = <String, String>{};
  for (final locale in const ['zh-CN', 'zh', 'en', 'ko']) {
    final name = _safeText(value[locale]);
    if (name != null) names[locale] = name;
  }
  return Map.unmodifiable(names);
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
