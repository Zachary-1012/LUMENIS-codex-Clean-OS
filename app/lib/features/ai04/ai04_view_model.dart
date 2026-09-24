import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'ai04_repository.dart';
import 'ai04_snapshot.dart';

enum Ai04LoadPhase { loading, ready, failed }

enum Ai04FailureKind { authentication, permissionDenied, offline, server }

class Ai04ViewModel extends ChangeNotifier {
  Ai04ViewModel({required this._repository});

  final Ai04Repository _repository;
  Ai04LoadPhase _phase = Ai04LoadPhase.loading;
  Ai04FailureKind? _failureKind;
  Ai04Snapshot? _snapshot;
  String _filter = '';
  String? _selectedSkillId;

  Ai04LoadPhase get phase => _phase;
  Ai04FailureKind? get failureKind => _failureKind;
  Ai04Snapshot? get snapshot => _snapshot;
  String get filter => _filter;
  String? get selectedSkillId => _selectedSkillId;

  List<Ai04SkillCapability> get filteredSkills {
    final skills = _snapshot?.skills ?? const <Ai04SkillCapability>[];
    final query = _filter.trim().toLowerCase();
    if (query.isEmpty) return skills;
    return skills
        .where(
          (skill) =>
              skill.name.toLowerCase().contains(query) ||
              skill.description.toLowerCase().contains(query) ||
              skill.category.toLowerCase().contains(query) ||
              skill.skillId.toLowerCase().contains(query),
        )
        .toList(growable: false);
  }

  Ai04SkillCapability? get selectedSkill {
    final id = _selectedSkillId;
    if (id == null) return null;
    for (final skill in _snapshot?.skills ?? const <Ai04SkillCapability>[]) {
      if (skill.skillId == id) return skill;
    }
    return null;
  }

  Future<void> refresh() async {
    _phase = Ai04LoadPhase.loading;
    _failureKind = null;
    _selectedSkillId = null;
    notifyListeners();
    try {
      _snapshot = await _repository.load();
      _phase = Ai04LoadPhase.ready;
    } catch (error) {
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _phase = Ai04LoadPhase.failed;
    }
    notifyListeners();
  }

  void updateFilter(String value) {
    if (value == _filter) return;
    _filter = value;
    notifyListeners();
  }

  void selectSkill(Ai04SkillCapability skill) {
    _selectedSkillId = skill.skillId;
    notifyListeners();
  }

  static Ai04FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Ai04FailureKind.authentication;
    }
    if (message.contains('http 403') || message.contains('permission')) {
      return Ai04FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('timed out')) {
      return Ai04FailureKind.offline;
    }
    return Ai04FailureKind.server;
  }
}
