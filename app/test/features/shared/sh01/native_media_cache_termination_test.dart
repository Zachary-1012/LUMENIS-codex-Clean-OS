import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/shared/sh01/native_media_cache.dart';

void main() {
  test(
    'skips a live child lease and reclaims it after abrupt child exit',
    () async {
      final sandbox = await Directory.systemTemp.createTemp(
        'lumenis-native-media-termination-test-',
      );
      final cacheRoot = Directory(
        '${sandbox.path}${Platform.pathSeparator}cache',
      );
      await cacheRoot.create();
      final cache = NativeMediaCache(root: cacheRoot);
      final nonce =
          '${Random.secure().nextInt(1 << 32).toRadixString(16)}-'
          '${DateTime.now().microsecondsSinceEpoch.toRadixString(16)}';
      final helper = await _findChildHelper();
      final dart = await _findDartExecutable();
      final child = await Process.start(
        dart.path,
        <String>[helper.path, '--hold-lease', cacheRoot.path, nonce],
        runInShell: false,
        workingDirectory: Directory.current.path,
      );
      final childExit = child.exitCode;
      final stderr = child.stderr.transform(utf8.decoder).join();
      final stdoutLines = StreamIterator<String>(
        child.stdout.transform(utf8.decoder).transform(const LineSplitter()),
      );
      var childExited = false;
      final childDirectory = Directory(
        '${cacheRoot.path}${Platform.pathSeparator}lease-$nonce',
      );

      try {
        expect(
          await stdoutLines.moveNext().timeout(const Duration(seconds: 15)),
          isTrue,
          reason: 'The isolated Dart helper must report its held lease.',
        );
        final ready = Map<String, dynamic>.from(
          jsonDecode(stdoutLines.current) as Map,
        );
        expect(ready['state'], 'locked');
        expect(ready['nonce'], nonce);
        expect(
          _samePath(ready['directory'] as String, childDirectory.path),
          isTrue,
        );
        expect(
          await File(
            '${childDirectory.path}${Platform.pathSeparator}lease-v1.json',
          ).exists(),
          isTrue,
        );
        expect(
          await File(
            '${childDirectory.path}${Platform.pathSeparator}preview.mp4',
          ).readAsBytes(),
          <int>[11, 22, 33, 44],
        );

        final beforeReclaim = await Future.any<String>(<Future<String>>[
          childExit.then((_) => 'exited'),
          Future<void>.delayed(
            const Duration(milliseconds: 300),
          ).then((_) => 'still-running'),
        ]);
        expect(beforeReclaim, 'still-running');

        await cache.reclaimStale();
        expect(await childDirectory.exists(), isTrue);
        expect(
          await File(
            '${childDirectory.path}${Platform.pathSeparator}preview.mp4',
          ).exists(),
          isTrue,
        );

        child.stdin.writeln('exit-with-73');
        await child.stdin.flush();
        final exitCode = await childExit.timeout(const Duration(seconds: 15));
        childExited = true;
        expect(exitCode, 73);
        expect(await stderr.timeout(const Duration(seconds: 5)), isEmpty);

        await cache.reclaimStale();
        expect(await childDirectory.exists(), isFalse);
        expect(await cacheRoot.list().toList(), isEmpty);
      } finally {
        if (!childExited) {
          try {
            child.stdin.writeln('exit-with-73');
            await child.stdin.flush();
            await childExit.timeout(const Duration(seconds: 10));
            childExited = true;
          } catch (_) {
            // The helper is isolated to this test root; no product process is
            // signaled or terminated here.
          }
        }
        await stdoutLines.cancel();
        try {
          await child.stdin.close();
        } catch (_) {}
        if (childExited) {
          await cache.reclaimStale();
        }
        if (await sandbox.exists()) await sandbox.delete(recursive: true);
      }
    },
    testOn: 'windows',
  );
}

Future<File> _findDartExecutable() async {
  final flutterRoot = Platform.environment['FLUTTER_ROOT'];
  if (flutterRoot != null && flutterRoot.isNotEmpty) {
    final candidate = File(
      _joinParts(<String>[
        flutterRoot,
        'bin',
        'cache',
        'dart-sdk',
        'bin',
        'dart.exe',
      ]),
    );
    if (await candidate.exists()) return candidate.absolute;
  }

  final executable = File(Platform.resolvedExecutable).absolute;
  if (_basename(executable.path).toLowerCase() == 'dart.exe' &&
      await executable.exists()) {
    return executable;
  }

  var directory = executable.parent;
  for (var depth = 0; depth < 12; depth++) {
    final candidate = File(
      _joinParts(<String>[
        directory.path,
        'bin',
        'cache',
        'dart-sdk',
        'bin',
        'dart.exe',
      ]),
    );
    if (await candidate.exists()) return candidate.absolute;
    final parent = directory.parent;
    if (_samePath(parent.path, directory.path)) break;
    directory = parent;
  }
  throw StateError('The Flutter SDK Dart executable could not be located.');
}

Future<File> _findChildHelper() async {
  const helperName = 'native_media_lease_child.dart';
  var directory = Directory.current.absolute;
  for (var depth = 0; depth < 10; depth++) {
    for (final parts in <List<String>>[
      <String>['test', 'fixtures', helperName],
      <String>['app', 'test', 'fixtures', helperName],
    ]) {
      final candidate = File(_joinParts(<String>[directory.path, ...parts]));
      if (await candidate.exists()) return candidate.absolute;
    }
    final parent = directory.parent;
    if (_samePath(parent.path, directory.path)) break;
    directory = parent;
  }
  throw StateError('The isolated Dart lease helper could not be located.');
}

String _joinParts(List<String> parts) {
  var result = parts.first;
  for (final part in parts.skip(1)) {
    if (result.endsWith(Platform.pathSeparator)) {
      result += part;
    } else {
      result += Platform.pathSeparator + part;
    }
  }
  return result;
}

String _basename(String path) {
  final index = path.lastIndexOf(Platform.pathSeparator);
  return index < 0 ? path : path.substring(index + 1);
}

bool _samePath(String left, String right) {
  final normalizedLeft = left.replaceAll('/', Platform.pathSeparator);
  final normalizedRight = right.replaceAll('/', Platform.pathSeparator);
  if (Platform.isWindows) {
    return normalizedLeft.toLowerCase() == normalizedRight.toLowerCase();
  }
  return normalizedLeft == normalizedRight;
}
