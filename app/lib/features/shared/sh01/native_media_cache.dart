import 'dart:convert';
import 'dart:io';

import '../../../core/lumenis_core_client.dart';

abstract interface class NativeMediaFileLease {
  String get path;

  Future<void> release();
}

enum NativeMediaCacheFailure {
  invalidSize,
  unsupportedType,
  unavailable,
  unsafeLocation,
  cleanupFailed,
}

class NativeMediaCacheException implements Exception {
  const NativeMediaCacheException(this.failure);

  final NativeMediaCacheFailure failure;

  String get message => switch (failure) {
    NativeMediaCacheFailure.invalidSize =>
      'The media file is empty or too large for preview.',
    NativeMediaCacheFailure.unsupportedType =>
      'This media type cannot be previewed here.',
    NativeMediaCacheFailure.unavailable =>
      'Temporary media storage is unavailable.',
    NativeMediaCacheFailure.unsafeLocation =>
      'Temporary media storage could not be verified.',
    NativeMediaCacheFailure.cleanupFailed =>
      'Temporary preview cleanup did not finish.',
  };

  @override
  String toString() => 'NativeMediaCacheException: $message';
}

class NativeMediaCache {
  NativeMediaCache({Directory? root}) : _root = root ?? _defaultRoot();

  static const int maxBytes = 512 * 1024 * 1024;
  static const String _markerName = 'lease-v1.json';
  static const String _videoName = 'preview.mp4';
  static const String _audioName = 'preview.wav';
  static const int _lockStart = 0;
  static const int _lockEnd = 1;
  static const int _maxMarkerBytes = 512;

  final Directory _root;

  Future<NativeMediaFileLease> create(ContentProjectFile file) async {
    final mediaName = switch (file.mediaType) {
      'video/mp4' => _videoName,
      'audio/wav' => _audioName,
      _ => null,
    };
    if (mediaName == null) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.unsupportedType,
      );
    }

    final byteCount = file.bytes.length;
    if (byteCount <= 0 || byteCount > maxBytes) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.invalidSize,
      );
    }

    await reclaimStale();

    Directory? leaseDirectory;
    Directory? canonicalRoot;
    File? markerFile;
    File? mediaFile;
    RandomAccessFile? markerHandle;
    RandomAccessFile? mediaHandle;
    var markerOwned = false;
    var mediaOwned = false;
    final markerContents = _markerContents(mediaName);

    try {
      canonicalRoot = await _ensureRoot();
      leaseDirectory = await canonicalRoot.createTemp('lease-');
      final verifiedDirectory = await _verifiedChild(
        canonicalRoot,
        leaseDirectory,
      );
      if (verifiedDirectory == null) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.unsafeLocation,
        );
      }
      leaseDirectory = verifiedDirectory;

      markerFile = File(_join(leaseDirectory.path, _markerName));
      if (await FileSystemEntity.type(markerFile.path, followLinks: false) !=
          FileSystemEntityType.notFound) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.unsafeLocation,
        );
      }
      markerOwned = true;
      markerHandle = await markerFile.open(mode: FileMode.append);
      await markerHandle.lock(FileLock.exclusive, _lockStart, _lockEnd);
      await _writeMarker(markerHandle, markerContents);

      mediaFile = File(_join(leaseDirectory.path, mediaName));
      if (await FileSystemEntity.type(mediaFile.path, followLinks: false) !=
          FileSystemEntityType.notFound) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.unsafeLocation,
        );
      }
      mediaOwned = true;
      mediaHandle = await mediaFile.open(mode: FileMode.writeOnly);
      await mediaHandle.writeFrom(file.bytes);
      await mediaHandle.flush();
      await mediaHandle.close();
      mediaHandle = null;

      if (!await _isRegularFileAtPath(
        canonicalRoot,
        leaseDirectory,
        mediaFile.path,
      )) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.unsafeLocation,
        );
      }

      final lease = _NativeMediaFileLease(
        root: canonicalRoot,
        directory: leaseDirectory,
        marker: markerFile,
        media: mediaFile,
        mediaName: mediaName,
        markerContents: markerContents,
        markerHandle: markerHandle,
      );
      markerHandle = null;
      return lease;
    } catch (error) {
      final cleanupSucceeded = await _cleanupFailedCreation(
        root: canonicalRoot,
        directory: leaseDirectory,
        marker: markerFile,
        media: mediaFile,
        markerHandle: markerHandle,
        mediaHandle: mediaHandle,
        markerOwned: markerOwned,
        mediaOwned: mediaOwned,
      );
      if (!cleanupSucceeded) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.cleanupFailed,
        );
      }
      if (error is NativeMediaCacheException) rethrow;
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.unavailable,
      );
    }
  }

  Future<void> reclaimStale() async {
    try {
      final root = await _existingRoot();
      if (root == null) return;

      final children = await root.list(followLinks: false).toList();
      for (final entity in children) {
        if (await FileSystemEntity.type(entity.path, followLinks: false) !=
            FileSystemEntityType.directory) {
          continue;
        }
        if (!_basename(entity.path).startsWith('lease-')) continue;

        final directory = await _verifiedChild(root, Directory(entity.path));
        if (directory == null) continue;
        await _reclaimOne(root, directory);
      }
    } on NativeMediaCacheException {
      rethrow;
    } catch (_) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.unavailable,
      );
    }
  }

  static Directory _defaultRoot() => Directory(
    _join(Directory.systemTemp.absolute.path, 'lumenis-media-preview-v1'),
  );

  Future<Directory> _ensureRoot() async {
    final absoluteRoot = _root.absolute;
    final rootType = await FileSystemEntity.type(
      absoluteRoot.path,
      followLinks: false,
    );
    if (rootType == FileSystemEntityType.directory) {
      final canonical = await absoluteRoot.resolveSymbolicLinks();
      if (!_samePath(canonical, absoluteRoot.path)) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.unsafeLocation,
        );
      }
      return Directory(canonical);
    }
    if (rootType != FileSystemEntityType.notFound) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.unsafeLocation,
      );
    }

    final parent = Directory(FileSystemEntity.parentOf(absoluteRoot.path));
    if (await FileSystemEntity.type(parent.path, followLinks: false) !=
        FileSystemEntityType.directory) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.unsafeLocation,
      );
    }
    final canonicalParent = await parent.resolveSymbolicLinks();
    if (!_samePath(canonicalParent, parent.absolute.path)) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.unsafeLocation,
      );
    }
    await absoluteRoot.create(recursive: false);
    final canonical = await absoluteRoot.resolveSymbolicLinks();
    if (!_samePath(canonical, absoluteRoot.path)) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.unsafeLocation,
      );
    }
    return Directory(canonical);
  }

  Future<Directory?> _existingRoot() async {
    final absoluteRoot = _root.absolute;
    final type = await FileSystemEntity.type(
      absoluteRoot.path,
      followLinks: false,
    );
    if (type == FileSystemEntityType.notFound) return null;
    if (type != FileSystemEntityType.directory) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.unsafeLocation,
      );
    }
    final canonical = await absoluteRoot.resolveSymbolicLinks();
    if (!_samePath(canonical, absoluteRoot.path)) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.unsafeLocation,
      );
    }
    return Directory(canonical);
  }

  Future<Directory?> _verifiedChild(Directory root, Directory candidate) async {
    try {
      if (await FileSystemEntity.type(candidate.path, followLinks: false) !=
          FileSystemEntityType.directory) {
        return null;
      }
      final canonical = await candidate.resolveSymbolicLinks();
      if (!_samePath(canonical, candidate.absolute.path) ||
          !_samePath(
            FileSystemEntity.parentOf(canonical),
            root.absolute.path,
          ) ||
          !_basename(canonical).startsWith('lease-')) {
        return null;
      }
      return Directory(canonical);
    } on FileSystemException {
      return null;
    }
  }

  Future<void> _reclaimOne(Directory root, Directory directory) async {
    final marker = File(_join(directory.path, _markerName));
    if (!await _isRegularFileAtPath(root, directory, marker.path)) return;

    RandomAccessFile? handle;
    var locked = false;
    var cleanupAttempted = false;
    String? mediaName;
    try {
      final initialNames = await _regularFileNames(root, directory);
      if (initialNames == null ||
          !initialNames.contains(_markerName) ||
          initialNames.length > 3 ||
          initialNames.any(
            (name) =>
                name != _markerName && name != _videoName && name != _audioName,
          )) {
        return;
      }

      handle = await marker.open(mode: FileMode.append);
      try {
        await handle.lock(FileLock.exclusive, _lockStart, _lockEnd);
        locked = true;
      } on FileSystemException {
        // A live preview owns the lease, or the OS cannot prove exclusivity.
        return;
      }

      if (!await _isRegularFileAtPath(root, directory, marker.path)) return;
      final contents = await _readMarker(handle);
      mediaName = _mediaNameFromMarker(contents);
      if (mediaName == null) return;

      final names = await _regularFileNames(root, directory);
      if (names == null ||
          !names.contains(_markerName) ||
          names.length > 2 ||
          names.any((name) => name != _markerName && name != mediaName)) {
        return;
      }

      final mediaPath = _join(directory.path, mediaName);
      final mediaType = await FileSystemEntity.type(
        mediaPath,
        followLinks: false,
      );
      if (mediaType == FileSystemEntityType.file) {
        if (!await _isRegularFileAtPath(root, directory, mediaPath)) return;
        cleanupAttempted = true;
        await File(mediaPath).delete();
      } else if (mediaType != FileSystemEntityType.notFound) {
        return;
      }
    } on NativeMediaCacheException {
      rethrow;
    } on FileSystemException {
      if (cleanupAttempted) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.cleanupFailed,
        );
      }
      return;
    } catch (_) {
      if (cleanupAttempted) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.cleanupFailed,
        );
      }
      return;
    } finally {
      if (handle != null) {
        if (locked) {
          try {
            await handle.unlock(_lockStart, _lockEnd);
          } catch (_) {
            // Closing below also releases the OS lease.
          }
        }
        try {
          await handle.close();
        } catch (_) {
          if (cleanupAttempted) {
            throw const NativeMediaCacheException(
              NativeMediaCacheFailure.cleanupFailed,
            );
          }
        }
      }
    }

    try {
      await _deleteRegularOwnedFile(root, directory, marker.path);
      await directory.delete(recursive: false);
    } on FileSystemException {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
  }

  Future<Set<String>?> _regularFileNames(
    Directory root,
    Directory directory,
  ) async {
    try {
      if (await _verifiedChild(root, directory) == null) return null;
      final entities = await directory.list(followLinks: false).toList();
      final names = <String>{};
      for (final entity in entities) {
        if (await FileSystemEntity.type(entity.path, followLinks: false) !=
            FileSystemEntityType.file) {
          return null;
        }
        if (!await _isRegularFileAtPath(root, directory, entity.path)) {
          return null;
        }
        names.add(_basename(entity.path));
      }
      return names;
    } on FileSystemException {
      return null;
    }
  }

  Future<bool> _isRegularFileAtPath(
    Directory root,
    Directory directory,
    String path,
  ) async {
    try {
      if (await _verifiedChild(root, directory) == null ||
          await FileSystemEntity.type(path, followLinks: false) !=
              FileSystemEntityType.file) {
        return false;
      }
      final canonical = await File(path).resolveSymbolicLinks();
      return _samePath(canonical, path) &&
          _samePath(FileSystemEntity.parentOf(canonical), directory.path);
    } on FileSystemException {
      return false;
    }
  }

  Future<void> _deleteRegularOwnedFile(
    Directory root,
    Directory directory,
    String path,
  ) async {
    final type = await FileSystemEntity.type(path, followLinks: false);
    if (type == FileSystemEntityType.notFound) return;
    if (!await _isRegularFileAtPath(root, directory, path)) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
    await File(path).delete();
  }

  Future<bool> _cleanupFailedCreation({
    required Directory? root,
    required Directory? directory,
    required File? marker,
    required File? media,
    required RandomAccessFile? markerHandle,
    required RandomAccessFile? mediaHandle,
    required bool markerOwned,
    required bool mediaOwned,
  }) async {
    var succeeded = true;
    if (mediaHandle != null) {
      try {
        await mediaHandle.close();
      } catch (_) {
        succeeded = false;
      }
    }

    if (root != null && directory != null && media != null && mediaOwned) {
      try {
        await _deleteRegularOwnedFile(root, directory, media.path);
      } catch (_) {
        succeeded = false;
      }
    }

    if (markerHandle != null) {
      try {
        await markerHandle.unlock(_lockStart, _lockEnd);
      } catch (_) {
        // Closing the handle below releases the lock where supported.
      }
      try {
        await markerHandle.close();
      } catch (_) {
        succeeded = false;
      }
    }

    if (root != null && directory != null && marker != null && markerOwned) {
      try {
        await _deleteRegularOwnedFile(root, directory, marker.path);
      } catch (_) {
        succeeded = false;
      }
    }

    if (root != null && directory != null) {
      try {
        if (await _verifiedChild(root, directory) != null) {
          await directory.delete(recursive: false);
        }
      } catch (_) {
        succeeded = false;
      }
    }
    return succeeded;
  }

  static Future<String> _readMarker(RandomAccessFile handle) async {
    await handle.setPosition(0);
    final bytes = await handle.read(_maxMarkerBytes);
    return utf8.decode(bytes);
  }

  Future<void> _writeMarker(
    RandomAccessFile handle,
    String markerContents,
  ) async {
    final bytes = utf8.encode(markerContents);
    await handle.setPosition(0);
    await handle.writeFrom(bytes);
    await handle.truncate(bytes.length);
    await handle.flush();
  }

  String _markerContents(String mediaName) =>
      '{"version":1,"files":["$_markerName","$mediaName"]}';

  String? _mediaNameFromMarker(String contents) {
    if (contents == _markerContents(_videoName)) return _videoName;
    if (contents == _markerContents(_audioName)) return _audioName;
    return null;
  }
}

class _NativeMediaFileLease implements NativeMediaFileLease {
  _NativeMediaFileLease({
    required this._root,
    required this._directory,
    required this._marker,
    required this._media,
    required this._mediaName,
    required this._markerContents,
    required RandomAccessFile this._markerHandle,
  });

  final Directory _root;
  final Directory _directory;
  final File _marker;
  final File _media;
  final String _mediaName;
  final String _markerContents;
  RandomAccessFile? _markerHandle;
  Future<void>? _releaseFuture;
  bool _released = false;

  @override
  String get path => _media.path;

  @override
  Future<void> release() {
    if (_released) return Future<void>.value();
    final pending = _releaseFuture;
    if (pending != null) return pending;

    final attempt = _release();
    _releaseFuture = attempt;
    attempt.then<void>(
      (_) {},
      onError: (Object _, StackTrace _) {
        if (identical(_releaseFuture, attempt)) _releaseFuture = null;
      },
    );
    return attempt;
  }

  Future<void> _release() async {
    try {
      final directory = await _verifiedDirectory();
      if (directory == null) {
        await _closeHandle();
        _released = true;
        return;
      }

      final handle = await _acquireLeaseHandle();
      if (await NativeMediaCache._readMarker(handle) != _markerContents) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.cleanupFailed,
        );
      }
      final names = await _regularFileNames();
      if (names == null ||
          !names.contains(NativeMediaCache._markerName) ||
          names.length > 2 ||
          names.any(
            (name) =>
                name != NativeMediaCache._markerName && name != _mediaName,
          )) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.cleanupFailed,
        );
      }

      await _deleteMediaIfPresent(directory);
      await _closeHandle();
      await _deleteMarkerIfPresent(directory);
      await directory.delete(recursive: false);
      _released = true;
    } catch (_) {
      await _closeHandle();
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
  }

  Future<Directory?> _verifiedDirectory() async {
    try {
      final type = await FileSystemEntity.type(
        _directory.path,
        followLinks: false,
      );
      if (type == FileSystemEntityType.notFound) {
        return null;
      }
      if (type != FileSystemEntityType.directory) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.cleanupFailed,
        );
      }
      final canonical = await _directory.resolveSymbolicLinks();
      if (!_samePath(canonical, _directory.path) ||
          !_samePath(FileSystemEntity.parentOf(canonical), _root.path) ||
          !_basename(canonical).startsWith('lease-')) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.cleanupFailed,
        );
      }
      return Directory(canonical);
    } on NativeMediaCacheException {
      rethrow;
    } catch (_) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
  }

  Future<RandomAccessFile> _acquireLeaseHandle() async {
    final current = _markerHandle;
    if (current != null) return current;

    final directory = await _verifiedDirectory();
    if (directory == null || !await _isRegularMarker(directory, _marker.path)) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }

    RandomAccessFile? handle;
    try {
      handle = await _marker.open(mode: FileMode.append);
      await handle.lock(
        FileLock.exclusive,
        NativeMediaCache._lockStart,
        NativeMediaCache._lockEnd,
      );
      if (await NativeMediaCache._readMarker(handle) != _markerContents ||
          !await _isRegularMarker(directory, _marker.path)) {
        throw const NativeMediaCacheException(
          NativeMediaCacheFailure.cleanupFailed,
        );
      }
      _markerHandle = handle;
      return handle;
    } catch (_) {
      if (handle != null) await _closeUnownedHandle(handle);
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
  }

  Future<bool> _isRegularMarker(Directory directory, String path) async {
    try {
      if (await FileSystemEntity.type(path, followLinks: false) !=
          FileSystemEntityType.file) {
        return false;
      }
      final canonical = await File(path).resolveSymbolicLinks();
      return _samePath(canonical, path) &&
          _samePath(FileSystemEntity.parentOf(canonical), directory.path);
    } catch (_) {
      return false;
    }
  }

  Future<void> _closeUnownedHandle(RandomAccessFile handle) async {
    try {
      await handle.unlock(
        NativeMediaCache._lockStart,
        NativeMediaCache._lockEnd,
      );
    } catch (_) {}
    try {
      await handle.close();
    } catch (_) {}
  }

  Future<Set<String>?> _regularFileNames() async {
    try {
      final directory = await _verifiedDirectory();
      if (directory == null) return null;
      final entities = await directory.list(followLinks: false).toList();
      final names = <String>{};
      for (final entity in entities) {
        if (await FileSystemEntity.type(entity.path, followLinks: false) !=
            FileSystemEntityType.file) {
          return null;
        }
        final canonical = await File(entity.path).resolveSymbolicLinks();
        if (!_samePath(canonical, entity.path) ||
            !_samePath(FileSystemEntity.parentOf(canonical), directory.path)) {
          return null;
        }
        names.add(_basename(entity.path));
      }
      return names;
    } on FileSystemException {
      return null;
    }
  }

  Future<void> _deleteMediaIfPresent(Directory directory) async {
    final type = await FileSystemEntity.type(_media.path, followLinks: false);
    if (type == FileSystemEntityType.notFound) return;
    if (type != FileSystemEntityType.file) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
    final canonical = await _media.resolveSymbolicLinks();
    if (!_samePath(canonical, _media.path) ||
        !_samePath(FileSystemEntity.parentOf(canonical), directory.path)) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
    await _media.delete();
  }

  Future<void> _deleteMarkerIfPresent(Directory directory) async {
    final type = await FileSystemEntity.type(_marker.path, followLinks: false);
    if (type == FileSystemEntityType.notFound) return;
    if (type != FileSystemEntityType.file) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
    final canonical = await _marker.resolveSymbolicLinks();
    if (!_samePath(canonical, _marker.path) ||
        !_samePath(FileSystemEntity.parentOf(canonical), directory.path)) {
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
    await _marker.delete();
  }

  Future<void> _closeHandle() async {
    final handle = _markerHandle;
    if (handle == null) return;
    try {
      await handle.unlock(
        NativeMediaCache._lockStart,
        NativeMediaCache._lockEnd,
      );
    } on FileSystemException {
      // Closing the handle below releases the OS lease where supported.
    } catch (_) {
      // Closing the handle below releases the OS lease where supported.
    }
    try {
      await handle.close();
    } catch (_) {
      _markerHandle = null;
      throw const NativeMediaCacheException(
        NativeMediaCacheFailure.cleanupFailed,
      );
    }
    _markerHandle = null;
  }
}

String _join(String parent, String child) {
  final separator = Platform.pathSeparator;
  final trimmed = parent.endsWith(separator) && parent.length > 1
      ? parent.substring(0, parent.length - 1)
      : parent;
  return '$trimmed$separator$child';
}

String _basename(String path) {
  final separatorIndex = path.lastIndexOf(Platform.pathSeparator);
  return separatorIndex < 0 ? path : path.substring(separatorIndex + 1);
}

bool _samePath(String left, String right) {
  var normalizedLeft = left.replaceAll('/', Platform.pathSeparator);
  var normalizedRight = right.replaceAll('/', Platform.pathSeparator);
  while (normalizedLeft.endsWith(Platform.pathSeparator) &&
      normalizedLeft.length > 1 &&
      !RegExp(r'^[A-Za-z]:\\$').hasMatch(normalizedLeft)) {
    normalizedLeft = normalizedLeft.substring(0, normalizedLeft.length - 1);
  }
  while (normalizedRight.endsWith(Platform.pathSeparator) &&
      normalizedRight.length > 1 &&
      !RegExp(r'^[A-Za-z]:\\$').hasMatch(normalizedRight)) {
    normalizedRight = normalizedRight.substring(0, normalizedRight.length - 1);
  }
  if (Platform.isWindows) {
    return normalizedLeft.toLowerCase() == normalizedRight.toLowerCase();
  }
  return normalizedLeft == normalizedRight;
}
