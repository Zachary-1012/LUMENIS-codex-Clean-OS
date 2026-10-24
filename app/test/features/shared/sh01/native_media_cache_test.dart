import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/native_media_cache.dart';

void main() {
  late Directory sandbox;
  late Directory cacheRoot;
  late NativeMediaCache cache;
  late List<NativeMediaFileLease> leases;

  setUp(() async {
    sandbox = await Directory.systemTemp.createTemp(
      'lumenis-native-media-cache-test-',
    );
    cacheRoot = Directory('${sandbox.path}${Platform.pathSeparator}cache');
    cache = NativeMediaCache(root: cacheRoot);
    leases = <NativeMediaFileLease>[];
  });

  tearDown(() async {
    for (final lease in leases) {
      try {
        await lease.release();
      } catch (_) {
        // The sandbox below is unique to this test and owns all remaining data.
      }
    }
    if (await sandbox.exists()) await sandbox.delete(recursive: true);
  });

  test('rejects size and media types before creating the cache root', () async {
    await expectLater(
      cache.create(
        ContentProjectFile(
          bytes: Uint8List(0),
          filename: 'empty.mp4',
          mediaType: 'video/mp4',
        ),
      ),
      throwsA(
        isA<NativeMediaCacheException>().having(
          (error) => error.failure,
          'failure',
          NativeMediaCacheFailure.invalidSize,
        ),
      ),
    );
    await expectLater(
      cache.create(
        ContentProjectFile(
          bytes: Uint8List.fromList(<int>[1]),
          filename: 'image.bin',
          mediaType: 'image/png',
        ),
      ),
      throwsA(
        isA<NativeMediaCacheException>().having(
          (error) => error.failure,
          'failure',
          NativeMediaCacheFailure.unsupportedType,
        ),
      ),
    );

    final oversized = Uint8List(NativeMediaCache.maxBytes + 1);
    await expectLater(
      cache.create(
        ContentProjectFile(
          bytes: oversized,
          filename: 'oversized.mp4',
          mediaType: 'video/mp4',
        ),
      ),
      throwsA(
        isA<NativeMediaCacheException>().having(
          (error) => error.failure,
          'failure',
          NativeMediaCacheFailure.invalidSize,
        ),
      ),
    );
    expect(await cacheRoot.exists(), isFalse);
  });

  for (final item in {
    'audio/mpeg': 'mp3',
    'audio/mp4': 'm4a',
    'video/webm': 'webm',
    'video/quicktime': 'mov',
  }.entries) {
    test(
      'original ${item.value} uses an owned lease and preserves bytes',
      () async {
        final bytes = Uint8List.fromList([4, 3, 2, 1]);
        final lease = await cache.create(
          ContentProjectFile(
            bytes: bytes,
            filename: r'..\outside\untrusted.name',
            mediaType: item.key,
          ),
        );
        leases.add(lease);
        expect(lease.path, endsWith('preview.${item.value}'));
        expect(await File(lease.path).readAsBytes(), bytes);
        await cache.reclaimStale();
        expect(await File(lease.path).exists(), isTrue);
        await lease.release();
        expect(await File(lease.path).exists(), isFalse);
      },
    );
  }

  test(
    'writes generated names and release removes only its lease files',
    () async {
      final bytes = Uint8List.fromList(<int>[0, 1, 2, 3, 254, 255]);
      final lease = await cache.create(
        ContentProjectFile(
          bytes: bytes,
          filename: r'..\private\source name.mp4',
          mediaType: 'video/mp4',
        ),
      );
      leases.add(lease);

      expect(_basename(lease.path), 'preview.mp4');
      expect(lease.path, isNot(contains('source name')));
      expect(await File(lease.path).readAsBytes(), bytes);
      final leaseDirectory = Directory(FileSystemEntity.parentOf(lease.path));

      await lease.release();
      await lease.release();

      expect(await File(lease.path).exists(), isFalse);
      expect(await leaseDirectory.exists(), isFalse);
      expect(await cacheRoot.list().toList(), isEmpty);
    },
  );

  test(
    'creates a fixed WAV filename for the authorized audio MIME type',
    () async {
      final lease = await cache.create(
        ContentProjectFile(
          bytes: Uint8List.fromList(<int>[82, 73, 70, 70]),
          filename: 'voice.wav',
          mediaType: 'audio/wav',
        ),
      );
      leases.add(lease);

      expect(_basename(lease.path), 'preview.wav');
      await lease.release();
    },
  );

  // Windows locks exclude a second handle in the same process. POSIX locks
  // are process-wide; the native preview and this guarantee are Windows-only.
  test('an active lease is skipped during stale recovery', () async {
    final lease = await cache.create(
      _content(<int>[7, 8, 9], filename: 'active.mp4'),
    );
    leases.add(lease);

    await cache.reclaimStale();

    expect(await File(lease.path).exists(), isTrue);
    expect(await File(lease.path).readAsBytes(), <int>[7, 8, 9]);
  }, testOn: 'windows');

  test('reclaims a stale directory with the exact versioned marker', () async {
    await cacheRoot.create(recursive: true);
    final directory = Directory(
      '${cacheRoot.path}${Platform.pathSeparator}lease-stale-fixture',
    );
    await directory.create();
    await File(
      '${directory.path}${Platform.pathSeparator}lease-v1.json',
    ).writeAsString('{"version":1,"files":["lease-v1.json","preview.mp4"]}');
    await File(
      '${directory.path}${Platform.pathSeparator}preview.mp4',
    ).writeAsBytes(<int>[3, 2, 1]);

    await cache.reclaimStale();

    expect(await directory.exists(), isFalse);
    expect(await cacheRoot.list().toList(), isEmpty);
  });

  test('leaves unknown contents and symbolic links untouched', () async {
    await cacheRoot.create(recursive: true);

    final unknownDirectory = Directory(
      '${cacheRoot.path}${Platform.pathSeparator}lease-unknown-fixture',
    );
    await unknownDirectory.create();
    await File(
      '${unknownDirectory.path}${Platform.pathSeparator}lease-v1.json',
    ).writeAsString('{"version":1,"files":["lease-v1.json","preview.mp4"]}');
    final media = File(
      '${unknownDirectory.path}${Platform.pathSeparator}preview.mp4',
    );
    await media.writeAsBytes(<int>[1, 2, 3]);
    final unknown = File(
      '${unknownDirectory.path}${Platform.pathSeparator}keep.txt',
    );
    await unknown.writeAsString('leave this file alone');

    final linkDirectory = Directory(
      '${cacheRoot.path}${Platform.pathSeparator}lease-link-fixture',
    );
    await linkDirectory.create();
    await File(
      '${linkDirectory.path}${Platform.pathSeparator}lease-v1.json',
    ).writeAsString('{"version":1,"files":["lease-v1.json","preview.mp4"]}');
    final externalMedia = File(
      '${sandbox.path}${Platform.pathSeparator}protected-target.mp4',
    );
    await externalMedia.writeAsString('protected fixture');
    final mediaLink = Link(
      '${linkDirectory.path}${Platform.pathSeparator}preview.mp4',
    );
    await mediaLink.create(externalMedia.path);

    await cache.reclaimStale();

    expect(await unknownDirectory.exists(), isTrue);
    expect(await unknown.exists(), isTrue);
    expect(await media.exists(), isTrue);
    expect(await linkDirectory.exists(), isTrue);
    expect(
      await FileSystemEntity.type(mediaLink.path, followLinks: false),
      FileSystemEntityType.link,
    );
    expect(await externalMedia.readAsString(), 'protected fixture');
  });

  test('release can retry after an unknown file blocks safe cleanup', () async {
    final lease = await cache.create(
      _content(<int>[4, 5, 6], filename: 'retry.mp4'),
    );
    leases.add(lease);
    final directory = Directory(FileSystemEntity.parentOf(lease.path));
    final unknown = File('${directory.path}${Platform.pathSeparator}unknown');
    await unknown.writeAsString('preserve until explicitly removed');

    NativeMediaCacheException? firstFailure;
    try {
      await lease.release();
    } on NativeMediaCacheException catch (error) {
      firstFailure = error;
    }
    expect(firstFailure?.failure, NativeMediaCacheFailure.cleanupFailed);
    expect(firstFailure.toString(), isNot(contains(sandbox.path)));
    expect(await File(lease.path).exists(), isTrue);

    await unknown.delete();
    await lease.release();
    await lease.release();
    expect(await directory.exists(), isFalse);
  });

  test('an unsafe root failure does not modify an existing file', () async {
    final rootFile = File(
      '${sandbox.path}${Platform.pathSeparator}root-is-a-file',
    );
    await rootFile.writeAsString('preserve');
    final unsafeCache = NativeMediaCache(root: Directory(rootFile.path));

    NativeMediaCacheException? failure;
    try {
      await unsafeCache.create(_content(<int>[1, 2, 3], filename: 'safe.mp4'));
    } on NativeMediaCacheException catch (error) {
      failure = error;
    }

    expect(failure?.failure, NativeMediaCacheFailure.unsafeLocation);
    expect(failure.toString(), isNot(contains(sandbox.path)));
    expect(await rootFile.readAsString(), 'preserve');
  });
}

ContentProjectFile _content(
  List<int> bytes, {
  required String filename,
  String mediaType = 'video/mp4',
}) => ContentProjectFile(
  bytes: Uint8List.fromList(bytes),
  filename: filename,
  mediaType: mediaType,
);

String _basename(String path) {
  final index = path.lastIndexOf(Platform.pathSeparator);
  return index < 0 ? path : path.substring(index + 1);
}
