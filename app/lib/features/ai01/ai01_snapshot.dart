class Ai01Snapshot {
  const Ai01Snapshot({
    required this.isBound,
    required this.generatedAt,
    required this.providers,
    required this.suggestions,
    required this.unavailableFields,
  });

  final bool isBound;
  final String? generatedAt;
  final List<Ai01ProviderState> providers;
  final List<Ai01Suggestion> suggestions;
  final List<String> unavailableFields;

  factory Ai01Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'AI-01') {
      throw const FormatException('AI-01 runtime response is not valid.');
    }

    final binding = _asMap(response['binding']);
    final sections = _asMapList(response['sections']);
    final split = sections.where((section) => section['type'] == 'split');

    final sideSections = split.expand((section) => _asMapList(section['side']));
    Map<String, Object?>? findSection(
      Iterable<Map<String, Object?>> candidates,
      String type,
    ) {
      for (final section in candidates) {
        if (section['type'] == type) return section;
      }
      return null;
    }

    final providerSection = findSection(sideSections, 'runtime');
    final cardsSection = findSection(sections, 'cards');

    final rawProviders = _asMapList(providerSection?['items']);
    final rawSuggestions = _asMapList(cardsSection?['items']);

    return Ai01Snapshot(
      isBound: response['bound'] == true && response['source'] == 'runtime',
      generatedAt: _asString(response['generated_at']),
      providers: rawProviders
          .where((provider) => provider['kind'] == 'provider')
          .map(Ai01ProviderState.fromJson)
          .toList(growable: false),
      suggestions: rawSuggestions.map(Ai01Suggestion.fromJson).toList(),
      unavailableFields: _asStringList(binding?['unavailable']),
    );
  }
}

class Ai01ProviderState {
  const Ai01ProviderState({
    required this.name,
    required this.state,
    required this.detail,
  });

  final String name;
  final String state;
  final String detail;

  factory Ai01ProviderState.fromJson(Map<String, Object?> json) {
    return Ai01ProviderState(
      name: _asString(json['name']) ?? 'Provider',
      state: _asString(json['state']) ?? 'unknown',
      detail: _asString(json['detail']) ?? '',
    );
  }
}

class Ai01Suggestion {
  const Ai01Suggestion({
    required this.title,
    required this.description,
    required this.intent,
  });

  final String title;
  final String description;
  final String? intent;

  factory Ai01Suggestion.fromJson(Map<String, Object?> json) {
    final action = _asMap(json['action']);
    return Ai01Suggestion(
      title: _asString(json['title']) ?? '',
      description: _asString(json['desc']) ?? '',
      intent: _asString(action?['intent']),
    );
  }
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

List<Map<String, Object?>> _asMapList(Object? value) {
  if (value is! List) return const [];
  return value.map(_asMap).whereType<Map<String, Object?>>().toList();
}

List<String> _asStringList(Object? value) {
  if (value is! List) return const [];
  return value.whereType<String>().toList(growable: false);
}

String? _asString(Object? value) {
  if (value is! String || value.isEmpty) return null;
  return value;
}
