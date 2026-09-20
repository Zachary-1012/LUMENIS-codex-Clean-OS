class Bmp01Snapshot {
  const Bmp01Snapshot({
    required this.contractBound,
    required this.source,
    required this.productId,
    required this.domainId,
    required this.dataState,
    required this.blockedFields,
    required this.generatedAt,
  });

  final bool contractBound;
  final String? source;
  final String? productId;
  final String? domainId;
  final String dataState;
  final List<Bmp01BlockedField> blockedFields;
  final String? generatedAt;

  bool get isBmpOwner => productId == 'ZBMP' && domainId == 'zbmp';
  bool get isNotCollected => dataState == 'NOT_COLLECTED';

  factory Bmp01Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-01') {
      throw const FormatException('BMP-01 runtime response is not valid.');
    }

    final truth = _asMap(response['truth']);
    final binding = _asMap(response['binding']);
    final blocked = _asMapList(
      binding?['blocked'],
    ).map(Bmp01BlockedField.fromJson).toList(growable: false);

    return Bmp01Snapshot(
      contractBound:
          response['bound'] == true && response['source'] == 'runtime',
      source: _asString(response['source']),
      productId: _asString(truth?['product_id']),
      domainId: _asString(truth?['domain_id']),
      dataState: (_asString(truth?['data_state']) ?? 'UNKNOWN').toUpperCase(),
      blockedFields: blocked,
      generatedAt: _asString(response['generated_at']),
    );
  }
}

class Bmp01BlockedField {
  const Bmp01BlockedField({
    required this.field,
    required this.reason,
    required this.required,
  });

  final String field;
  final String reason;
  final String required;

  factory Bmp01BlockedField.fromJson(Map<String, Object?> json) {
    return Bmp01BlockedField(
      field: _asString(json['field']) ?? '未知字段',
      reason: _asString(json['reason']) ?? '当前没有可验证的来源说明。',
      required: _asString(json['required']) ?? '',
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

String? _asString(Object? value) {
  if (value is! String || value.isEmpty) return null;
  return value;
}
