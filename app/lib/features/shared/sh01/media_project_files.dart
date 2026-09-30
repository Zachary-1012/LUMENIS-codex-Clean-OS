import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';

/// User-picked files and explicit downloads. No automatic filesystem scan,
/// source deletion, or claim that a browser completed its final disk write.
class MediaProjectFiles {
  static const maxImportBytes = 128 * 1024 * 1024;
  static const _media = XTypeGroup(
    label: 'Video / audio',
    extensions: [
      'mp4',
      'mov',
      'webm',
      'mkv',
      'avi',
      'wav',
      'mp3',
      'm4a',
      'flac',
      'ogg',
      'aac',
      'aiff',
    ],
    mimeTypes: ['video/*', 'audio/*'],
    uniformTypeIdentifiers: ['public.movie', 'public.audio'],
  );

  Future<List<XFile>> choose() => openFiles(acceptedTypeGroups: [_media]);

  bool get canSave =>
      kIsWeb ||
      const {
        TargetPlatform.windows,
        TargetPlatform.macOS,
        TargetPlatform.linux,
      }.contains(defaultTargetPlatform);

  Future<bool> save(ContentProjectFile content) async {
    if (!canSave) {
      throw UnsupportedError('File saving is not connected on this surface.');
    }
    final file = XFile.fromData(
      content.bytes,
      mimeType: content.mediaType,
      name: content.filename,
    );
    if (kIsWeb) {
      await file.saveTo(content.filename);
      return true;
    }
    final location = await getSaveLocation(suggestedName: content.filename);
    if (location == null) return false;
    await file.saveTo(location.path);
    return true;
  }
}
