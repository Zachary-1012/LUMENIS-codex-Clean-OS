import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/bmp01/bmp01_repository.dart';
import 'package:lumenis_app/features/bmp01/bmp01_snapshot.dart';
import 'package:lumenis_app/features/bmp01/bmp01_view_model.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_repository.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_snapshot.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_view_model.dart';

void main() {
  for (final entry in <String, _ReadProbe Function()>{
    'BMP-01': _bmpProbe,
    'SH-01': _sharedProbe,
  }.entries) {
    group(entry.key, () {
      for (final fails in [false, true]) {
        test(
          'leaving during a read ignores late ${fails ? 'failure' : 'success'}',
          () async {
            final probe = entry.value();
            var notifications = 0;
            probe.model.addListener(() => notifications++);
            final pending = probe.refresh();
            expect(probe.requests, hasLength(1));
            probe.model.dispose();
            if (fails) {
              probe.requests.single.completeError(Exception('HTTP 403'));
            } else {
              probe.requests.single.complete('late result');
            }
            await pending;
            expect(notifications, 1);
            expect(probe.result(), isNull);
            await probe.refresh();
            expect(probe.requests, hasLength(1));
          },
        );
      }

      test('an older failure cannot replace the most recent result', () async {
        final probe = entry.value();
        addTearDown(probe.model.dispose);
        final oldRead = probe.refresh();
        final latestRead = probe.refresh();
        probe.requests[1].complete('latest result');
        await latestRead;
        probe.requests[0].completeError(Exception('HTTP 401'));
        await oldRead;
        expect(probe.result(), 'latest result');
        expect(probe.failed(), isFalse);
      });

      test(
        'an older result cannot reopen data after the latest denial',
        () async {
          final probe = entry.value();
          addTearDown(probe.model.dispose);
          final oldRead = probe.refresh();
          final latestRead = probe.refresh();
          probe.requests[1].completeError(Exception('HTTP 403'));
          await latestRead;
          probe.requests[0].complete('old result');
          await oldRead;
          expect(probe.result(), isNull);
          expect(probe.failed(), isTrue);
        },
      );
    });
  }
}

class _ReadProbe {
  _ReadProbe({
    required this.model,
    required this.refresh,
    required this.result,
    required this.failed,
    required this.requests,
  });

  final ChangeNotifier model;
  final Future<void> Function() refresh;
  final String? Function() result;
  final bool Function() failed;
  final List<Completer<String>> requests;
}

_ReadProbe _bmpProbe() {
  final repository = _BmpRepository();
  final model = Bmp01ViewModel(repository: repository);
  return _ReadProbe(
    model: model,
    refresh: model.refresh,
    result: () => model.snapshot?.generatedAt,
    failed: () => model.phase == Bmp01LoadPhase.failed,
    requests: repository.requests,
  );
}

class _BmpRepository implements Bmp01Repository {
  final requests = <Completer<String>>[];

  @override
  Future<Bmp01Snapshot> load() async {
    final request = Completer<String>();
    requests.add(request);
    return Bmp01Snapshot.fromResponse({
      'ok': true,
      'screen': 'BMP-01',
      'generated_at': await request.future,
    });
  }
}

_ReadProbe _sharedProbe() {
  final repository = _SharedRepository();
  final model = Sh01ViewModel(repository: repository);
  return _ReadProbe(
    model: model,
    refresh: model.refresh,
    result: () => model.catalog?.capability,
    failed: () => model.phase == Sh01LoadPhase.failed,
    requests: repository.requests,
  );
}

class _SharedRepository implements Sh01Repository {
  final requests = <Completer<String>>[];

  @override
  Future<Sh01Catalog> loadCatalog() async {
    final request = Completer<String>();
    requests.add(request);
    return Sh01Catalog(
      capability: await request.future,
      consumers: const [],
      skills: const [],
    );
  }
}
