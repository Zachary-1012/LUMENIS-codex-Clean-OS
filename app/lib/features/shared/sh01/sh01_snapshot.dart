class Sh01Capability {
  const Sh01Capability({
    required this.id,
    required this.name,
    required this.description,
    required this.owner,
    required this.consumers,
    required this.category,
    required this.version,
    required this.permission,
    required this.risk,
    required this.executionPolicy,
    required this.evaluationStatus,
    required this.implementationState,
  });

  final String id;
  final String name;
  final String description;
  final String owner;
  final List<String> consumers;
  final String category;
  final String version;
  final String permission;
  final String risk;
  final String executionPolicy;
  final String evaluationStatus;
  final String implementationState;

  static Sh01Capability? tryParse(Object? value) {
    final record = _asMap(value);
    if (record == null) return null;
    final id = _string(record['id']);
    final name = _string(record['name']);
    if (id.isEmpty || name.isEmpty) return null;
    return Sh01Capability(
      id: id,
      name: name,
      description: _string(record['description']),
      owner: _string(record['owner']),
      consumers: _strings(record['consumers']),
      category: _string(record['category']),
      version: _string(record['version']),
      permission: _string(record['permission']),
      risk: _string(record['risk']),
      executionPolicy: _string(record['execution_policy']),
      evaluationStatus: _string(record['evaluation_status']),
      implementationState: _string(record['implementation_state']),
    );
  }
}

class Sh01Catalog {
  const Sh01Catalog({
    required this.capability,
    required this.consumers,
    required this.skills,
  });

  final String capability;
  final List<String> consumers;
  final List<Sh01Capability> skills;

  static Sh01Catalog fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['product'] != 'LUMENIS') {
      throw const FormatException('Shared capability catalog is invalid');
    }
    final rawSkills = response['skills'];
    if (rawSkills is! List) {
      throw const FormatException(
        'Shared capability catalog has no skills list',
      );
    }
    return Sh01Catalog(
      capability: _string(response['capability']),
      consumers: _strings(response['consumers']),
      skills: rawSkills
          .map(Sh01Capability.tryParse)
          .whereType<Sh01Capability>()
          .toList(growable: false),
    );
  }
}

Map<String, dynamic>? _asMap(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

List<String> _strings(Object? value) => value is List
    ? value
          .whereType<String>()
          .map((item) => item.trim())
          .toList(growable: false)
    : const [];

String _string(Object? value) => value is String ? value.trim() : '';
