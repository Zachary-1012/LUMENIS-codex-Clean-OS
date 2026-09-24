import '../sys02/sys_system_foundation.dart';

class Sys05Snapshot {
  const Sys05Snapshot({
    required this.dataSource,
    required this.backendRequired,
    required this.fields,
  });

  final String dataSource;
  final bool backendRequired;
  final List<String> fields;

  factory Sys05Snapshot.fromResponse(Map<String, dynamic> response) {
    _validateEnvelope(response);
    final truth = sysMap(response['truth']);
    final sections = sysMapList(response['sections']);
    final fields = <String>[];
    for (final section in sections) {
      for (final field in sysMapList(section['fields'])) {
        final label = sysString(field['label'] ?? field['name']);
        if (label != null) fields.add(label);
      }
    }
    return Sys05Snapshot(
      dataSource: sysSafeDisplay(truth['data_source'], fallback: 'local'),
      backendRequired: truth['backend_required'] == true,
      fields: fields,
    );
  }
}

class Sys05Preferences {
  const Sys05Preferences({
    this.theme = 'system',
    this.optical = 'balanced',
    this.density = 'comfortable',
    this.reducedMotion = 'system',
    this.locale = 'zh-CN',
  });

  final String theme;
  final String optical;
  final String density;
  final String reducedMotion;
  final String locale;

  Sys05Preferences copyWith({
    String? theme,
    String? optical,
    String? density,
    String? reducedMotion,
    String? locale,
  }) {
    return Sys05Preferences(
      theme: theme ?? this.theme,
      optical: optical ?? this.optical,
      density: density ?? this.density,
      reducedMotion: reducedMotion ?? this.reducedMotion,
      locale: locale ?? this.locale,
    );
  }

  @override
  bool operator ==(Object other) =>
      other is Sys05Preferences &&
      other.theme == theme &&
      other.optical == optical &&
      other.density == density &&
      other.reducedMotion == reducedMotion &&
      other.locale == locale;

  @override
  int get hashCode =>
      Object.hash(theme, optical, density, reducedMotion, locale);
}

void _validateEnvelope(Map<String, dynamic> response) {
  if (response['ok'] != true ||
      response['screen'] != 'SYS-05' ||
      response['bound'] != true ||
      response['source'] != 'runtime') {
    throw const FormatException(
      'SYS-05 settings response identity is invalid.',
    );
  }
}
