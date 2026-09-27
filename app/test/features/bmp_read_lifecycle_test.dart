import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/bmp02/bmp02_repository.dart';
import 'package:lumenis_app/features/bmp02/bmp02_snapshot.dart';
import 'package:lumenis_app/features/bmp02/bmp02_view_model.dart';
import 'package:lumenis_app/features/bmp03/bmp03_repository.dart';
import 'package:lumenis_app/features/bmp03/bmp03_snapshot.dart';
import 'package:lumenis_app/features/bmp03/bmp03_view_model.dart';
import 'package:lumenis_app/features/bmp04/bmp04_repository.dart';
import 'package:lumenis_app/features/bmp04/bmp04_snapshot.dart';
import 'package:lumenis_app/features/bmp04/bmp04_view_model.dart';
import 'package:lumenis_app/features/bmp05/bmp05_repository.dart';
import 'package:lumenis_app/features/bmp05/bmp05_snapshot.dart';
import 'package:lumenis_app/features/bmp05/bmp05_view_model.dart';
import 'package:lumenis_app/features/bmp06/bmp06_repository.dart';
import 'package:lumenis_app/features/bmp06/bmp06_snapshot.dart';
import 'package:lumenis_app/features/bmp06/bmp06_view_model.dart';
import 'package:lumenis_app/features/bmp07/bmp07_repository.dart';
import 'package:lumenis_app/features/bmp07/bmp07_snapshot.dart';
import 'package:lumenis_app/features/bmp07/bmp07_view_model.dart';
import 'package:lumenis_app/features/bmp08/bmp08_repository.dart';
import 'package:lumenis_app/features/bmp08/bmp08_snapshot.dart';
import 'package:lumenis_app/features/bmp08/bmp08_view_model.dart';
import 'package:lumenis_app/features/bmp09/bmp09_repository.dart';
import 'package:lumenis_app/features/bmp09/bmp09_snapshot.dart';
import 'package:lumenis_app/features/bmp09/bmp09_view_model.dart';
import 'package:lumenis_app/features/bmp10/bmp10_repository.dart';
import 'package:lumenis_app/features/bmp10/bmp10_snapshot.dart';
import 'package:lumenis_app/features/bmp10/bmp10_view_model.dart';
import 'package:lumenis_app/features/bmp11/bmp11_repository.dart';
import 'package:lumenis_app/features/bmp11/bmp11_snapshot.dart';
import 'package:lumenis_app/features/bmp11/bmp11_view_model.dart';

import 'shared/bmp_scope_test_support.dart';

void main() {
  final cases = <_LifecycleCaseFactory>[
    _LifecycleCaseFactory('BMP-02', _bmp02Case),
    _LifecycleCaseFactory('BMP-03', _bmp03Case),
    _LifecycleCaseFactory('BMP-04', _bmp04Case),
    _LifecycleCaseFactory('BMP-05', _bmp05Case),
    _LifecycleCaseFactory('BMP-06', _bmp06Case),
    _LifecycleCaseFactory('BMP-07', _bmp07Case),
    _LifecycleCaseFactory('BMP-08', _bmp08Case),
    _LifecycleCaseFactory('BMP-09', _bmp09Case),
    _LifecycleCaseFactory('BMP-10', _bmp10Case),
    _LifecycleCaseFactory('BMP-11', _bmp11Case),
  ];

  for (final testCase in cases) {
    _registerLifecycleTests(testCase);
  }
}

void _registerLifecycleTests(_LifecycleCaseFactory factory) {
  group(factory.name, () {
    test('ignores a late successful read after disposal', () async {
      final fixture = factory.create();
      var notifications = 0;
      fixture.viewModel.addListener(() => notifications++);

      final refresh = fixture.refresh();
      expect(fixture.readCount(), 1);
      expect(notifications, 1);

      fixture.viewModel.dispose();
      fixture.completeSuccess();
      await expectLater(refresh, completes);

      expect(notifications, 1);
      expect(fixture.stateUnchanged(), isTrue);
    });

    test('ignores a late failed read after disposal', () async {
      final fixture = factory.create();
      var notifications = 0;
      fixture.viewModel.addListener(() => notifications++);

      final refresh = fixture.refresh();
      expect(fixture.readCount(), 1);
      expect(notifications, 1);

      fixture.viewModel.dispose();
      fixture.completeFailure();
      await expectLater(refresh, completes);

      expect(notifications, 1);
      expect(fixture.stateUnchanged(), isTrue);
    });

    test('does not start a read when refreshed after disposal', () async {
      final fixture = factory.create();
      fixture.viewModel.dispose();

      await expectLater(fixture.refresh(), completes);

      expect(fixture.readCount(), 0);
      expect(fixture.stateUnchanged(), isTrue);
    });
  });
}

class _LifecycleCaseFactory {
  const _LifecycleCaseFactory(this.name, this.create);

  final String name;
  final _LifecycleCase Function() create;
}

class _LifecycleCase {
  const _LifecycleCase({
    required this.viewModel,
    required this.refresh,
    required this.readCount,
    required this.completeSuccess,
    required this.completeFailure,
    required this.stateUnchanged,
  });

  final ChangeNotifier viewModel;
  final Future<void> Function() refresh;
  final int Function() readCount;
  final VoidCallback completeSuccess;
  final VoidCallback completeFailure;
  final bool Function() stateUnchanged;
}

class _PendingRepository<T> {
  _PendingRepository(this.completer);

  final Completer<T> completer;
  int loadCount = 0;

  Future<T> read() {
    loadCount++;
    return completer.future;
  }
}

class _Bmp02PendingRepository extends _PendingRepository<Bmp02Snapshot>
    implements Bmp02Repository {
  _Bmp02PendingRepository(super.completer);

  @override
  Future<Bmp02Snapshot> load() => read();
}

class _Bmp03PendingRepository extends _PendingRepository<Bmp03Snapshot>
    implements Bmp03Repository {
  _Bmp03PendingRepository(super.completer);

  @override
  Future<Bmp03Snapshot> load() => read();
}

class _Bmp04PendingRepository extends _PendingRepository<Bmp04Snapshot>
    implements Bmp04Repository {
  _Bmp04PendingRepository(super.completer);

  @override
  Future<Bmp04Snapshot> load() => read();
}

class _Bmp05PendingRepository extends _PendingRepository<Bmp05Snapshot>
    implements Bmp05Repository {
  _Bmp05PendingRepository(super.completer);

  @override
  Future<Bmp05Snapshot> load() => read();
}

class _Bmp06PendingRepository extends _PendingRepository<Bmp06Snapshot>
    implements Bmp06Repository {
  _Bmp06PendingRepository(super.completer);

  @override
  Future<Bmp06Snapshot> load() => read();
}

class _Bmp07PendingRepository extends _PendingRepository<Bmp07Snapshot>
    implements Bmp07Repository {
  _Bmp07PendingRepository(super.completer);

  @override
  Future<Bmp07Snapshot> load() => read();
}

class _Bmp08PendingRepository extends _PendingRepository<Bmp08Snapshot>
    implements Bmp08Repository {
  _Bmp08PendingRepository(super.completer);

  @override
  Future<Bmp08Snapshot> load() => read();
}

class _Bmp09PendingRepository extends _PendingRepository<Bmp09Snapshot>
    implements Bmp09Repository {
  _Bmp09PendingRepository(super.completer);

  @override
  Future<Bmp09Snapshot> load() => read();
}

class _Bmp10PendingRepository extends _PendingRepository<Bmp10Snapshot>
    implements Bmp10Repository {
  _Bmp10PendingRepository(super.completer);

  @override
  Future<Bmp10Snapshot> load() => read();
}

class _Bmp11PendingRepository extends _PendingRepository<Bmp11Snapshot>
    implements Bmp11Repository {
  _Bmp11PendingRepository(super.completer);

  @override
  Future<Bmp11Snapshot> load() => read();
}

_LifecycleCase _bmp02Case() {
  final completer = Completer<Bmp02Snapshot>();
  final repository = _Bmp02PendingRepository(completer);
  final viewModel = Bmp02ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot02()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp02LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

_LifecycleCase _bmp03Case() {
  final completer = Completer<Bmp03Snapshot>();
  final repository = _Bmp03PendingRepository(completer);
  final viewModel = Bmp03ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot03()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp03LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

_LifecycleCase _bmp04Case() {
  final completer = Completer<Bmp04Snapshot>();
  final repository = _Bmp04PendingRepository(completer);
  final viewModel = Bmp04ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot04()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp04LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

_LifecycleCase _bmp05Case() {
  final completer = Completer<Bmp05Snapshot>();
  final repository = _Bmp05PendingRepository(completer);
  final viewModel = Bmp05ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot05()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp05LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

_LifecycleCase _bmp06Case() {
  final completer = Completer<Bmp06Snapshot>();
  final repository = _Bmp06PendingRepository(completer);
  final viewModel = Bmp06ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot06()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp06LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

_LifecycleCase _bmp07Case() {
  final completer = Completer<Bmp07Snapshot>();
  final repository = _Bmp07PendingRepository(completer);
  final viewModel = Bmp07ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot07()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp07LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

_LifecycleCase _bmp08Case() {
  final completer = Completer<Bmp08Snapshot>();
  final repository = _Bmp08PendingRepository(completer);
  final viewModel = Bmp08ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot08()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp08LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

_LifecycleCase _bmp09Case() {
  final completer = Completer<Bmp09Snapshot>();
  final repository = _Bmp09PendingRepository(completer);
  final viewModel = Bmp09ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot09()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp09LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

_LifecycleCase _bmp10Case() {
  final completer = Completer<Bmp10Snapshot>();
  final repository = _Bmp10PendingRepository(completer);
  final viewModel = Bmp10ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot10()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp10LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

_LifecycleCase _bmp11Case() {
  final completer = Completer<Bmp11Snapshot>();
  final repository = _Bmp11PendingRepository(completer);
  final viewModel = Bmp11ViewModel(repository: repository);
  return _LifecycleCase(
    viewModel: viewModel,
    refresh: viewModel.refresh,
    readCount: () => repository.loadCount,
    completeSuccess: () => completer.complete(_snapshot11()),
    completeFailure: () => completer.completeError(StateError('late read')),
    stateUnchanged: () =>
        viewModel.phase == Bmp11LoadPhase.loading &&
        viewModel.failureKind == null &&
        viewModel.snapshot == null,
  );
}

Bmp02Snapshot _snapshot02() =>
    Bmp02Snapshot.fromResponse(_snapshotResponse('BMP-02'));
Bmp03Snapshot _snapshot03() =>
    Bmp03Snapshot.fromResponse(_snapshotResponse('BMP-03'));
Bmp04Snapshot _snapshot04() =>
    Bmp04Snapshot.fromResponse(_snapshotResponse('BMP-04'));
Bmp05Snapshot _snapshot05() =>
    Bmp05Snapshot.fromResponse(_snapshotResponse('BMP-05'));
Bmp06Snapshot _snapshot06() =>
    Bmp06Snapshot.fromResponse(_snapshotResponse('BMP-06'));
Bmp07Snapshot _snapshot07() =>
    Bmp07Snapshot.fromResponse(_snapshotResponse('BMP-07'));
Bmp08Snapshot _snapshot08() =>
    Bmp08Snapshot.fromResponse(_snapshotResponse('BMP-08'));
Bmp09Snapshot _snapshot09() =>
    Bmp09Snapshot.fromResponse(_snapshotResponse('BMP-09'));
Bmp10Snapshot _snapshot10() =>
    Bmp10Snapshot.fromResponse(_snapshotResponse('BMP-10'));
Bmp11Snapshot _snapshot11() =>
    Bmp11Snapshot.fromResponse(_snapshotResponse('BMP-11'));

Map<String, dynamic> _snapshotResponse(String screen) {
  final scope = {
    ...bmpFocusScope(),
    'brand_id': 'BRAND-ONE',
    'display_name': const {
      'zh-CN': '主品牌',
      'en': 'Primary',
      'ko': '주요 브랜드',
    },
  };
  return {
    'ok': true,
    'screen': screen,
    'source': 'runtime',
    'bound': true,
    'truth': {
      'product_id': 'ZBMP',
      'domain_id': 'zbmp',
      'data_state': 'READY',
    },
    'focus_context': scope,
    'scope': scope,
    'focus_binding': bmpFocusBinding(),
    'binding': {
      'scope_read_evidence_version': 'v2',
      'evidence_lineage_version': 'v2',
      'scope_mode': 'FOCUS',
      'brand_id': 'BRAND-ONE',
      'read_access': 'ALLOWED',
      'granted_permissions': <String>[],
    },
    'sections': <Map<String, dynamic>>[],
    'assets': <Map<String, dynamic>>[],
    'materials': <Map<String, dynamic>>[],
    'outline': <Map<String, dynamic>>[],
    'channels': <Map<String, dynamic>>[],
    'campaigns': <Map<String, dynamic>>[],
    'risks': <Map<String, dynamic>>[],
    'dimensions': <Map<String, dynamic>>[],
    'incidents': <Map<String, dynamic>>[],
    'benchmarks': <Map<String, dynamic>>[],
  };
}
