import '../../../core/lumenis_core_client.dart';
import 'acc01_snapshot.dart';

abstract interface class Acc01Repository {
  Future<Acc01Snapshot> load();
}

enum Acc01IdentityMethod { email, google, apple }

enum Acc01IdentityStatus { signedIn, cancelled, linkRequired, deletionPending }

class Acc01EmailChallenge {
  const Acc01EmailChallenge({
    required this.reference,
    required this.displayEmail,
    required this.resendAt,
    required this.expiresAt,
    this.codeLength = 6,
  });

  final String reference;
  final String displayEmail;
  final DateTime resendAt;
  final DateTime expiresAt;
  final int codeLength;
}

class Acc01IdentityOutcome {
  const Acc01IdentityOutcome({
    required this.status,
    this.continuation,
    this.deletionAt,
  });

  final Acc01IdentityStatus status;
  final String? continuation;
  final DateTime? deletionAt;
}

enum Acc01IdentityFailure { unavailable, invalidCode, expiredCode, rateLimited }

class Acc01IdentityException implements Exception {
  const Acc01IdentityException(this.failure, {this.retryAt});
  final Acc01IdentityFailure failure;
  final DateTime? retryAt;
}

abstract interface class Acc01IdentityActions {
  Set<Acc01IdentityMethod> get availableMethods;
  Future<Acc01EmailChallenge> requestEmail(String email);
  Future<Acc01IdentityOutcome> verifyEmail(String reference, String code);
  Future<Acc01IdentityOutcome> signIn(Acc01IdentityMethod method);
  Future<Acc01IdentityOutcome> confirmLink(String continuation);
  Future<Acc01IdentityOutcome> restoreAccount(String continuation);
}

class CoreAcc01Repository implements Acc01Repository {
  CoreAcc01Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Acc01Snapshot> load() async {
    final response = await _client.runtimeIdentity();
    return Acc01Snapshot.fromIdentity(response);
  }
}
