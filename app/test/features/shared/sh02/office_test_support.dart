import 'dart:typed_data';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_files.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_office_controller.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_repository.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_snapshot.dart';

const officeWorkId = 'WORK-000000000000000000000001';
String officeId(int version) =>
    'ART-${version.toRadixString(16).padLeft(16, '0')}';
String officeObjectId(int number) =>
    'office-${number.toRadixString(16).padLeft(32, '0')}';
String _hash(int version, [int salt = 0]) =>
    (version + salt).toRadixString(16).padLeft(64, '0');

Map<String, dynamic> officeObject(
  int index, {
  String kind = 'text_run',
  String? value,
  Map<String, dynamic> location = const {},
}) => {
  'object_id': officeObjectId(index),
  'kind': kind,
  'value': value ?? 'Original writing $index',
  'editable': true,
  'part_sha256': 'a' * 64,
  'locator': {
    'part': 'word/document.xml',
    'node_path': '/w:document/w:body/w:p[$index]/w:r/w:t',
    'paragraph_index': index,
    ...location,
  },
};

Map<String, dynamic> officeSavedRaw(
  int version, {
  String requestId = 'request-office-original',
  String format = 'docx',
}) {
  final attachment = version == 1
      ? 'source-original.$format'
      : 'edited-version-$version.$format';
  final payload = <String, dynamic>{
    'source_material': {
      'origin': version == 1 ? 'user-upload' : 'user-edited-original-version',
      'original_filename': 'original.$format',
      'attachment_name': attachment,
      'sha256': _hash(version, 20),
      'size_bytes': 20,
      'allowed_use': 'private_custody_and_analysis',
    },
    'parsed_source': {'text': 'Source'},
    'basic_analysis': {
      'character_count': 6,
      'table_count': 0,
      'source_excerpts': [],
      'limitations': [],
    },
    if (version > 1)
      'office_edit': {
        'schema': 'lumenis.office-edit/v1',
        'package_sha256': _hash(version, 20),
        'parent_package_sha256': _hash(version - 1, 20),
        'result_attachment_name': attachment,
        'source_artifact_id': officeId(version - 1),
        'source_artifact_sha256': _hash(version - 1),
        'original_retained_in_parent_version': true,
      },
  };
  return {
    'artifact': {
      'artifact_id': officeId(version),
      'sha256': _hash(version),
      'created_at': '2026-10-24T12:00:00Z',
    },
    'document': {
      'kind': 'research',
      'request_id': requestId,
      'work_id': officeWorkId,
      'version': version,
      'parent_artifact_id': version == 1 ? null : officeId(version - 1),
      'parent_sha256': version == 1 ? null : _hash(version - 1),
      'payload': payload,
    },
    'office_attachment': {
      'artifact_id': officeId(version),
      'name': attachment,
      'sha256': _hash(version, 20),
      'media_type': 'application/octet-stream',
      'size_bytes': 20,
    },
  };
}

class OfficeTestRepository implements Sh02OfficeRepository, Sh02Repository {
  OfficeTestRepository({int count = 2, this.format = 'docx'}) {
    materials[1] = Sh02ImportedMaterial.tryParse(
      officeSavedRaw(1, format: format),
    )!;
    values[1] = [
      for (var index = 1; index <= count; index++) officeObject(index),
    ];
  }
  final String format;
  final Map<int, Sh02ImportedMaterial> materials = {};
  final Map<int, List<Map<String, dynamic>>> values = {};
  final requests = <List<Map<String, dynamic>>>[];
  final readOffsets = <int>[];
  final downloaded = <String>[];
  bool signed = false, active = false, loseAcknowledgement = false;
  bool invalidateSignature = false;
  int get latest => materials.keys.reduce((a, b) => a > b ? a : b);
  Sh02ImportedMaterial get original => materials[1]!;
  Sh02OfficePage project(Sh02ImportedMaterial source, int offset) {
    final objects = values[source.version]!;
    return Sh02OfficePage.fromJson(
      {
        'schema': 'lumenis.office-objects/v1',
        'source_artifact_id': source.artifactId,
        'source_artifact_sha256': source.artifactSha256,
        'package_sha256': source.sourceSha256,
        'work_id': officeWorkId,
        'version': source.version,
        'current_version': source.version == latest,
        'format': format,
        'attachment_name': source.version == 1
            ? 'source-original.$format'
            : 'edited-version-${source.version}.$format',
        'objects': objects.skip(offset).take(100).toList(),
        'object_count': objects.length,
        'has_more': offset + 100 < objects.length,
        'next_offset': offset + 100 < objects.length ? offset + 100 : null,
        'signature_parts': signed ? ['_xmlsignatures/sig1.xml'] : [],
        'active_content_parts': active ? ['vbaProject.bin'] : [],
        'unsupported_objects': [],
        'formula_evaluation': 'NOT_RUN',
      },
      source,
      offset,
      100,
    );
  }

  @override
  Future<Sh02OfficePage> read(
    Sh02ImportedMaterial source, {
    int offset = 0,
  }) async {
    readOffsets.add(offset);
    return project(source, offset);
  }

  @override
  Future<Sh02OfficeSaved> save(
    Sh02OfficePage parent, {
    required String requestId,
    required String reason,
    required List<Map<String, dynamic>> commands,
    required bool invalidateSignature,
  }) async {
    requests.add(commands);
    if (parent.version != latest) {
      throw const LumenisCoreException('Revision conflict', statusCode: 409);
    }
    this.invalidateSignature = invalidateSignature;
    final version = latest + 1;
    final rows = values[parent.version]!
        .map((row) => Map<String, dynamic>.from(row))
        .toList();
    for (final command in commands) {
      final row = rows.singleWhere(
        (row) => row['object_id'] == command['object_id'],
      );
      row['value'] = command['value'] is bool
          ? command['value'] == true
                ? '1'
                : '0'
          : command['value'];
    }
    final raw = officeSavedRaw(version, requestId: requestId, format: format);
    materials[version] = Sh02ImportedMaterial.tryParse(raw)!;
    values[version] = rows;
    if (loseAcknowledgement) {
      throw const LumenisCoreException('Response lost', statusCode: 503);
    }
    return Sh02OfficeSaved.fromJson(raw, parent, requestId);
  }

  void externalRevision(String value) {
    final version = latest + 1;
    materials[version] = Sh02ImportedMaterial.tryParse(
      officeSavedRaw(
        version,
        requestId: 'external-office-$version',
        format: format,
      ),
    )!;
    values[version] = values[version - 1]!.map((row) => {...row}).toList();
    values[version]!.first['value'] = value;
  }

  @override
  Future<Sh02ImportedMaterial> reopen(String artifactId) async =>
      materials.values.singleWhere((item) => item.artifactId == artifactId);
  @override
  Future<Sh02OfficeHistoryPage> history(
    String workId, {
    String? cursor,
  }) async => Sh02OfficeHistoryPage(materials.values.toList(), null, true);
  @override
  Future<SavedWorkExportFile> download(Sh02OfficePage page) async {
    downloaded.add('${page.artifactId}/${page.attachment}');
    return SavedWorkExportFile(
      bytes: Uint8List.fromList([80, 75, page.version]),
      filename: 'original.$format',
      mediaType: 'application/octet-stream',
    );
  }

  @override
  Future<Sh02Snapshot> loadLibrary() async => throw const LumenisCoreException(
    'Source library unavailable',
    statusCode: 503,
  );
  @override
  Future<Sh02ImportPage> loadRecentImports({String? cursor}) async =>
      Sh02ImportPage(
        items: [materials[latest]!],
        hasMore: false,
        verificationComplete: true,
        unverifiedCandidates: 0,
      );
  @override
  Future<Sh02ImportedMaterial> importDocument({
    required String filename,
    required Uint8List bytes,
    required String requestId,
  }) => throw UnsupportedError('Not used');
  @override
  Future<Sh02ImportedMaterial> reopenImport(String artifactId) =>
      reopen(artifactId);
  @override
  Future<Sh02SourcePage> readSourceRows(
    Sh02ImportedMaterial item,
    int offset,
  ) async =>
      const Sh02SourcePage(offset: 0, total: 0, hasMore: false, rows: []);
}

class OfficeTestFiles extends MediaProjectFiles {
  ContentProjectFile? saved;
  @override
  bool get canSave => true;
  @override
  Future<bool> save(ContentProjectFile content) async {
    saved = content;
    return true;
  }
}
