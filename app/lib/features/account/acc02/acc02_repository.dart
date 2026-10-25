import '../../../core/lumenis_core_client.dart';
import 'acc02_snapshot.dart';

abstract interface class Acc02Repository {
  Future<Acc02Snapshot> load();

  Future<void> selectSubject(Acc02Subject subject);
}

class CoreAcc02Repository implements Acc02Repository {
  CoreAcc02Repository({required this._client});

  final LumenisCoreClient _client;
  String domainId = 'CTH';

  @override
  Future<Acc02Snapshot> load() async {
    Map<String, dynamic>? contextResponse;
    Map<String, dynamic>? subjectsResponse;
    Object? contextError;
    Object? subjectsError;

    try {
      contextResponse = await _client.settingsContext();
    } catch (error) {
      contextError = error;
    }
    try {
      subjectsResponse = await _client.settingsSubjects(domainId: domainId);
    } catch (error) {
      subjectsError = error;
    }

    if (contextResponse == null && subjectsResponse == null) {
      throw contextError ??
          subjectsError ??
          const FormatException('ACC-02 unavailable.');
    }
    return Acc02Snapshot.fromResponses(
      contextResponse: contextResponse,
      subjectsResponse: subjectsResponse,
      contextError: contextError,
      subjectsError: subjectsError,
    );
  }

  @override
  Future<void> selectSubject(Acc02Subject subject) async {
    await _client.selectContext(
      domainId: subject.domainId,
      subjectId: subject.id,
    );
  }
}
