import '../../../core/lumenis_core_client.dart';

class Cth02SubjectMetadata {
  const Cth02SubjectMetadata({
    required this.id,
    required this.name,
    required this.type,
    required this.industry,
  });

  final String id;
  final String name;
  final String type;
  final String industry;
}

class Cth02Directory {
  Cth02Directory(List<Cth02SubjectMetadata> subjects)
    : subjects = List.unmodifiable(subjects);

  final List<Cth02SubjectMetadata> subjects;

  factory Cth02Directory.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['source'] != 'lumenis_subject_registry' ||
        response['selection_only'] != true) {
      throw const FormatException(
        'Subject Registry selection contract required.',
      );
    }

    final domains = response['domains'];
    final hasCthReadScope =
        domains is List &&
        domains.any((domain) {
          return domain is Map &&
              domain['id'] == 'CTH' &&
              domain['product'] == 'CTH';
        });
    if (!hasCthReadScope) {
      throw const FormatException(
        'CTH Subject Registry scope was not returned.',
      );
    }

    final rawSubjects = response['subjects'];
    if (rawSubjects is! List) {
      throw const FormatException('Subject Registry did not return a list.');
    }

    final subjects = <Cth02SubjectMetadata>[];
    for (final rawSubject in rawSubjects) {
      if (rawSubject is! Map || rawSubject['domain_id'] != 'CTH') {
        throw const FormatException(
          'Subject Registry returned an invalid CTH row.',
        );
      }
      final id = _text(rawSubject['subject_id']);
      final name = _text(rawSubject['name_zh']).isNotEmpty
          ? _text(rawSubject['name_zh'])
          : _text(rawSubject['name_en']);
      if (id.isEmpty || name.isEmpty) {
        throw const FormatException(
          'Subject Registry row is missing identity.',
        );
      }

      subjects.add(
        Cth02SubjectMetadata(
          id: id,
          name: name,
          type: _text(rawSubject['subject_type_name']),
          industry: _text(rawSubject['industry']),
        ),
      );
    }
    return Cth02Directory(subjects);
  }

  static String _text(Object? value) => value is String ? value.trim() : '';
}

abstract interface class Cth02Repository {
  Future<Cth02Directory> loadDirectory();
}

class CoreCth02Repository implements Cth02Repository {
  CoreCth02Repository({required LumenisCoreClient client}) : _client = client;

  final LumenisCoreClient _client;

  @override
  Future<Cth02Directory> loadDirectory() async =>
      Cth02Directory.fromResponse(await _client.settingsSubjects());
}
