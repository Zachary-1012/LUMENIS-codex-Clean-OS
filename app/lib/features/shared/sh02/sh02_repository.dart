import 'dart:typed_data';

import 'package:file_selector/file_selector.dart';

import '../../../core/lumenis_core_client.dart';
import 'sh02_snapshot.dart';

typedef Sh02ScreenReader = Future<Map<String, dynamic>> Function();

class Sh02PickedDocument {
  const Sh02PickedDocument({required this.filename, required this.bytes});

  final String filename;
  final Uint8List bytes;
}

abstract interface class Sh02DocumentPicker {
  Future<Sh02PickedDocument?> pick();
}

class PlatformSh02DocumentPicker implements Sh02DocumentPicker {
  static const _types = XTypeGroup(
    label: 'Documents',
    extensions: [
      'docx',
      'xlsx',
      'pptx',
      'pdf',
      'txt',
      'csv',
      'json',
      'xml',
      'xbrl',
      'html',
      'htm',
      'doc',
      'xls',
    ],
  );

  @override
  Future<Sh02PickedDocument?> pick() async {
    final file = await openFile(acceptedTypeGroups: [_types]);
    if (file == null) return null;
    final size = await file.length();
    if (size <= 0 || size > 8 * 1024 * 1024) {
      throw const FormatException('Shared document size is invalid.');
    }
    return Sh02PickedDocument(
      filename: file.name,
      bytes: await file.readAsBytes(),
    );
  }
}

class Sh02ImportPage {
  const Sh02ImportPage({
    required this.items,
    required this.hasMore,
    required this.verificationComplete,
    required this.unverifiedCandidates,
    this.nextCursor,
    this.malformedItems = 0,
  });

  factory Sh02ImportPage.fromResponse(Map<String, dynamic> result) {
    final rawItems = result['items'];
    final verificationComplete = result['verification_complete'];
    final unverifiedCandidates = result['unverified_candidates'];
    final hasMore = result['has_more'];
    final rawCursor = result['next_cursor'];
    if (rawItems is! List ||
        verificationComplete is! bool ||
        unverifiedCandidates is! int ||
        unverifiedCandidates < 0 ||
        verificationComplete != (unverifiedCandidates == 0) ||
        hasMore is! bool ||
        (hasMore && (rawCursor is! String || rawCursor.trim().isEmpty))) {
      throw const FormatException('Recent import verification is unavailable.');
    }

    final items = <Sh02ImportedMaterial>[];
    var malformedItems = 0;
    for (final rawItem in rawItems) {
      final item = Sh02ImportedMaterial.tryParse(rawItem);
      if (item == null) {
        malformedItems += 1;
      } else {
        items.add(item);
      }
    }

    return Sh02ImportPage(
      items: List<Sh02ImportedMaterial>.unmodifiable(items),
      hasMore: hasMore,
      verificationComplete: verificationComplete && malformedItems == 0,
      unverifiedCandidates: unverifiedCandidates,
      nextCursor: hasMore ? rawCursor as String : null,
      malformedItems: malformedItems,
    );
  }

  final List<Sh02ImportedMaterial> items;
  final bool hasMore;
  final bool verificationComplete;
  final int unverifiedCandidates;
  final String? nextCursor;
  final int malformedItems;
}

abstract interface class Sh02Repository {
  Future<Sh02Snapshot> loadLibrary();
  Future<Sh02ImportPage> loadRecentImports({String? cursor});
  Future<Sh02ImportedMaterial> importDocument({
    required String filename,
    required Uint8List bytes,
    required String requestId,
  });
  Future<Sh02ImportedMaterial> reopenImport(String artifactId);
  Future<Sh02SourcePage> readSourceRows(Sh02ImportedMaterial item, int offset);
}

class CoreSh02Repository implements Sh02Repository {
  const CoreSh02Repository({required this._client, this.screenReader});

  final LumenisCoreClient _client;
  final Sh02ScreenReader? screenReader;

  @override
  Future<Sh02Snapshot> loadLibrary() async {
    final reader = screenReader ?? () => _client.screen('SH-02');
    return Sh02Snapshot.fromResponse(await reader());
  }

  @override
  Future<Sh02ImportPage> loadRecentImports({String? cursor}) async {
    final response = await _client.listSharedDocumentImports(cursor: cursor);
    final result = _result(response);
    return Sh02ImportPage.fromResponse(result);
  }

  @override
  Future<Sh02ImportedMaterial> importDocument({
    required String filename,
    required Uint8List bytes,
    required String requestId,
  }) async {
    final response = await _client.importSharedDocument(
      filename: filename,
      bytes: bytes,
      requestId: requestId,
    );
    final item = Sh02ImportedMaterial.tryParse(_result(response));
    if (item == null || item.requestId != requestId) {
      throw const FormatException('Imported document receipt is invalid.');
    }
    return item;
  }

  @override
  Future<Sh02ImportedMaterial> reopenImport(String artifactId) async {
    final response = await _client.reopenSharedSavedWork(artifactId);
    final item = Sh02ImportedMaterial.tryParse(_result(response));
    if (item == null || item.artifactId != artifactId) {
      throw const FormatException('Reopened document is invalid.');
    }
    return item;
  }

  static Map<String, dynamic> _result(Map<String, dynamic> response) {
    if (response['ok'] != true || response['result'] is! Map) {
      throw const FormatException('Shared document response is invalid.');
    }
    return (response['result'] as Map).map(
      (key, value) => MapEntry('$key', value),
    );
  }

  @override
  Future<Sh02SourcePage> readSourceRows(
    Sh02ImportedMaterial item,
    int offset,
  ) async => Sh02SourcePage.fromResponse(
    _result(
      await _client.sharedDocumentRows(
        artifactId: item.artifactId,
        sourceSha256: item.sourceSha256,
        offset: offset,
      ),
    ),
    item,
    offset,
  );
}
