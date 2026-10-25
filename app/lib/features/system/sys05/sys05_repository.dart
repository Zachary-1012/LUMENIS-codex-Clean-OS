import '../../../core/lumenis_core_client.dart';
import 'sys05_snapshot.dart';

abstract interface class Sys05Repository {
  Future<Sys05Snapshot> load();
}

enum Sys05AccountAction {
  editProfile,
  changeEmail,
  linkIdentity,
  unlinkIdentity,
  revokeSession,
  revokeAllSessions,
  newDeviceAlerts,
  modelLearning,
  exportData,
  backupData,
  restoreData,
  deleteConversations,
  deleteAccount,
  restoreAccount,
  signOut,
}

class Sys05DeviceSession {
  const Sys05DeviceSession({
    required this.id,
    required this.name,
    required this.current,
    this.location,
    this.lastActive,
  });
  final String id;
  final String name;
  final bool current;
  final String? location;
  final DateTime? lastActive;
}

class Sys05AccountSettings {
  const Sys05AccountSettings({
    required this.signedIn,
    this.displayName,
    this.email,
    this.loginMethods = const {},
    this.availableLoginMethods = const {},
    this.sessions,
    this.newDeviceAlerts,
    this.modelLearning,
    this.deletionAt,
    this.modelCalls,
    this.collectionTasks,
    this.storageBytes,
    this.usagePeriod,
    this.allowedActions = const {},
  });
  final bool signedIn;
  final String? displayName;
  final String? email;
  final Set<String> loginMethods;
  final Set<String> availableLoginMethods;
  final List<Sys05DeviceSession>? sessions;
  final bool? newDeviceAlerts;
  final bool? modelLearning;
  final DateTime? deletionAt;
  final int? modelCalls;
  final int? collectionTasks;
  final int? storageBytes;
  final String? usagePeriod;
  final Set<Sys05AccountAction> allowedActions;
}

class Sys05SettingsRequest {
  const Sys05SettingsRequest(this.action, {this.value, this.reference});
  final Sys05AccountAction action;
  final String? value;
  final String? reference;
}

class Sys05SettingsReceipt {
  const Sys05SettingsReceipt({required this.pending});
  final bool pending;
}

abstract interface class Sys05AccountSettingsRepository {
  Future<Sys05AccountSettings> read();
  Future<Sys05SettingsReceipt> perform(Sys05SettingsRequest request);
}

class CoreSys05Repository implements Sys05Repository {
  CoreSys05Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sys05Snapshot> load() async {
    final response = await _client.screen('SYS-05');
    return Sys05Snapshot.fromResponse(response);
  }
}
