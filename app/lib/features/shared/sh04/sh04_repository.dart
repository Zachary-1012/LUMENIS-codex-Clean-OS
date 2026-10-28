import '../../../core/lumenis_core_client.dart';
import 'sh04_snapshot.dart';

abstract interface class Sh04Repository {
  Future<Sh04Snapshot> loadExports({String? cursor});

  Future<Sh04Export> saveReport({
    required String title,
    required String markdown,
    required String requestId,
  });

  Future<Sh04Export> reopen(String artifactId);

  Future<Sh04Export> reviseReport({
    required Sh04Export parent,
    required String title,
    required String markdown,
    required String reason,
    required String requestId,
  });

  Future<SavedWorkExportFile> export({
    required String artifactId,
    required String format,
    String purpose = 'delivery',
  });
}

class CoreSh04Repository implements Sh04Repository {
  const CoreSh04Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sh04Snapshot> loadExports({String? cursor}) async =>
      Sh04Snapshot.fromResponse(
        await _client.listSharedSavedWork(cursor: cursor, kind: 'report'),
      );

  @override
  Future<Sh04Export> saveReport({
    required String title,
    required String markdown,
    required String requestId,
  }) async => Sh04Export.fromResponse(
    await _client.saveSharedReport(
      title: title,
      markdown: markdown,
      requestId: requestId,
    ),
  );

  @override
  Future<Sh04Export> reopen(String artifactId) async =>
      Sh04Export.fromResponse(await _client.reopenSharedSavedWork(artifactId));

  @override
  Future<Sh04Export> reviseReport({
    required Sh04Export parent,
    required String title,
    required String markdown,
    required String reason,
    required String requestId,
  }) async => Sh04Export.fromResponse(
    await _client.reviseSharedReport(
      artifactId: parent.internalId,
      requestId: requestId,
      expectedSha256: parent.sha256,
      reason: reason,
      expectedTitle: parent.title,
      title: title,
      expectedMarkdown: parent.markdown,
      markdown: markdown,
      continueAsReport: parent.isLegacyVisualReport,
    ),
  );

  @override
  Future<SavedWorkExportFile> export({
    required String artifactId,
    required String format,
    String purpose = 'delivery',
  }) => _client.exportSharedSavedWork(
    artifactId: artifactId,
    format: format,
    purpose: purpose,
  );
}
