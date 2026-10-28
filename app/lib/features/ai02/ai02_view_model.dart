import 'dart:math';
import 'package:flutter/foundation.dart';
import '../../core/lumenis_core_client.dart';
import '../../core/transport/lumenis_http_transport.dart';
import 'ai02_repository.dart';
import 'ai02_snapshot.dart';

enum Ai02LoadPhase { loading, ready, failed }

enum Ai02FailureKind {
  authentication,
  permissionDenied,
  offline,
  server,
  unknownEffect,
}

class Ai02ViewModel extends ChangeNotifier {
  Ai02ViewModel({required this.repository});
  final Ai02Repository repository;
  Ai02LoadPhase phase = Ai02LoadPhase.loading;
  Ai02FailureKind? failureKind;
  Ai02Snapshot? snapshot;
  Ai02Task? selected;
  bool busy = false, reading = false, _disposed = false;
  int _generation = 0, _selectionGeneration = 0;
  String? _pendingRequest, _uncertainTaskId;
  bool _requestLoaded = false;
  bool get canStart =>
      !busy &&
      !reading &&
      _requestLoaded &&
      _pendingRequest == null &&
      _uncertainTaskId == null &&
      phase == Ai02LoadPhase.ready;
  bool get creationUncertain => _pendingRequest != null;
  bool get canRetrySubmission =>
      !busy &&
      !reading &&
      _requestLoaded &&
      _pendingRequest != null &&
      phase == Ai02LoadPhase.ready;

  Future<void> refresh({bool more = false}) async {
    if (_disposed || busy) return;
    final offset = more ? snapshot?.nextOffset : 0;
    if (offset == null) return;
    final generation = ++_generation;
    reading = true;
    failureKind = null;
    _notify();
    try {
      if (!_requestLoaded || _pendingRequest == null) {
        final pending = await repository.pendingRequest();
        if (_disposed || generation != _generation) return;
        _pendingRequest = pending;
        _requestLoaded = true;
      }
      final result = await repository.load(offset: offset);
      if (_disposed || generation != _generation) return;
      final rows = <String, Ai02Task>{
        if (more)
          for (final task in snapshot?.tasks ?? <Ai02Task>[]) task.id: task,
        for (final task in result.tasks) task.id: task,
      };
      snapshot = Ai02Snapshot(
        tasks: rows.values.toList(),
        nextOffset: result.nextOffset,
      );
      phase = Ai02LoadPhase.ready;
      if (_pendingRequest case final requestId?) {
        final recovered = await repository.readRequest(requestId);
        if (_disposed || generation != _generation) return;
        if (recovered == null) {
          failureKind = Ai02FailureKind.unknownEffect;
        } else {
          if (recovered.requestId != requestId) {
            throw const FormatException('Task request identity changed.');
          }
          selected = recovered;
          _updateRow(recovered);
          await repository.forgetRequest(requestId);
          final remaining = await repository.pendingRequest();
          if (_disposed || generation != _generation) return;
          _pendingRequest = remaining;
          if (remaining != null) failureKind = Ai02FailureKind.unknownEffect;
        }
      }
      if (_uncertainTaskId case final id?) await select(id);
    } catch (error) {
      if (_disposed || generation != _generation) return;
      _fail(error);
      if (snapshot == null) phase = Ai02LoadPhase.failed;
    } finally {
      if (!_disposed && generation == _generation) {
        reading = false;
        _notify();
      }
    }
  }

  Future<void> select(String id, {bool background = false}) async {
    if (_disposed || busy) return;
    final generation = ++_selectionGeneration;
    if (!background) {
      selected = null;
      reading = true;
      failureKind = null;
      _notify();
    }
    try {
      final row = await repository.read(id);
      if (_disposed || generation != _selectionGeneration) return;
      if (row.id != id) throw const FormatException('Task identity changed.');
      selected = row;
      if (_uncertainTaskId == id) _uncertainTaskId = null;
      _updateRow(row);
    } catch (error) {
      if (!_disposed && generation == _selectionGeneration) {
        selected = null;
        _fail(error);
      }
    } finally {
      if (!_disposed && generation == _selectionGeneration) {
        reading = false;
        _notify();
      }
    }
  }

  void newTask() {
    if (_disposed || busy) return;
    _selectionGeneration++;
    selected = null;
    _notify();
  }

  Future<bool> start(String input, {bool retryUnconfirmed = false}) async {
    if (_disposed ||
        input.trim().isEmpty ||
        (retryUnconfirmed ? !canRetrySubmission : !canStart)) {
      return false;
    }
    _generation++;
    _selectionGeneration++;
    busy = true;
    failureKind = null;
    _notify();
    try {
      final random = Random.secure();
      final requestId =
          _pendingRequest ??
          List.generate(
            16,
            (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
          ).join();
      _pendingRequest = requestId;
      await repository.retainRequest(requestId);
      if (_disposed) return false;
      final row = await repository.start(input.trim(), requestId: requestId);
      if (_disposed) return false;
      if (row.requestId != requestId) {
        throw const FormatException('Task request identity changed.');
      }
      selected = row;
      _updateRow(row);
      await repository.forgetRequest(requestId);
      final remaining = await repository.pendingRequest();
      if (_disposed) return false;
      _pendingRequest = remaining;
      if (remaining != null) failureKind = Ai02FailureKind.unknownEffect;
      return true;
    } catch (error) {
      if (!_disposed) {
        _fail(error);
        if (error is! LumenisCoreException ||
            error.statusCode == null ||
            error.statusCode! >= 500) {
          failureKind = Ai02FailureKind.unknownEffect;
        }
      }
      return false;
    } finally {
      if (!_disposed) {
        busy = false;
        _notify();
      }
    }
  }

  Future<void> act(String action) async {
    final before = selected;
    if (_disposed ||
        busy ||
        before == null ||
        (action == 'cancel'
            ? !before.canCancel
            : action != 'run' || !before.canResume)) {
      return;
    }
    _generation++;
    _selectionGeneration++;
    busy = true;
    failureKind = null;
    _notify();
    try {
      final row = await repository.act(before.id, action);
      if (_disposed) return;
      selected = row;
      _updateRow(row);
    } catch (error) {
      if (!_disposed) {
        _fail(error);
        if (failureKind == Ai02FailureKind.offline ||
            failureKind == Ai02FailureKind.server) {
          _uncertainTaskId = before.id;
          selected = null;
          failureKind = Ai02FailureKind.unknownEffect;
        }
      }
    } finally {
      if (!_disposed) {
        busy = false;
        _notify();
      }
    }
  }

  void _updateRow(Ai02Task row) {
    snapshot = Ai02Snapshot(
      tasks: [row, ...?snapshot?.tasks.where((item) => item.id != row.id)],
      nextOffset: snapshot?.nextOffset,
    );
  }

  void _fail(Object error) {
    failureKind = switch (error) {
      LumenisCoreException(statusCode: 401) => Ai02FailureKind.authentication,
      LumenisCoreException(statusCode: 403 || 404) =>
        Ai02FailureKind.permissionDenied,
      _ =>
        isLumenisConnectionError(error)
            ? Ai02FailureKind.offline
            : Ai02FailureKind.server,
    };
    if (failureKind == Ai02FailureKind.authentication ||
        failureKind == Ai02FailureKind.permissionDenied) {
      snapshot = null;
      selected = null;
      phase = Ai02LoadPhase.failed;
    }
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    _selectionGeneration++;
    super.dispose();
  }
}
