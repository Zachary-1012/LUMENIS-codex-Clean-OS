import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';

/// Explicit user-selected local exports. Web confirms a browser handoff;
/// desktop confirms a selected destination. iOS uses the in-app copy action.
class Sh04ExportFiles {
  static const _reportTypes = XTypeGroup(
    label: 'Report',
    extensions: ['md', 'txt', 'docx', 'pdf', 'xlsx'],
  );

  bool get canSaveFile =>
      kIsWeb ||
      const {
        TargetPlatform.windows,
        TargetPlatform.macOS,
        TargetPlatform.linux,
      }.contains(defaultTargetPlatform);

  Future<bool> save(
    SavedWorkExportFile content, {
    required String suggestedName,
  }) async {
    if (!canSaveFile) {
      throw UnsupportedError('File saving is unavailable on this surface.');
    }
    if (suggestedName.isEmpty ||
        suggestedName.length > 180 ||
        RegExp(r'[\\/:\x00-\x1f]').hasMatch(suggestedName)) {
      throw const FormatException('The report filename is invalid.');
    }
    final file = XFile.fromData(
      content.bytes,
      mimeType: content.mediaType,
      name: suggestedName,
    );
    if (kIsWeb) {
      await file.saveTo(suggestedName);
      return true;
    }
    final location = await getSaveLocation(
      suggestedName: suggestedName,
      acceptedTypeGroups: const [_reportTypes],
    );
    if (location == null) return false;
    await file.saveTo(location.path);
    return true;
  }
}
