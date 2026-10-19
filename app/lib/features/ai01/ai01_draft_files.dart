import 'dart:convert';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

/// User-selected, unsent text only. This never imports business records or
/// establishes account, context, Permission, or Evidence.
class Ai01DraftFiles {
  static const maxBytes = 64 * 1024;
  static const maxCharacters = 4000;
  static const _textType = XTypeGroup(
    label: 'Text',
    extensions: ['txt'],
    mimeTypes: ['text/plain'],
    uniformTypeIdentifiers: ['public.plain-text'],
  );

  bool get canSave =>
      kIsWeb ||
      const {
        TargetPlatform.windows,
        TargetPlatform.macOS,
        TargetPlatform.linux,
      }.contains(defaultTargetPlatform);

  Future<String?> open() async {
    final file = await openFile(acceptedTypeGroups: [_textType]);
    if (file == null) return null;
    if (await file.length() > maxBytes) throw const FormatException();
    return decode(await file.readAsBytes());
  }

  static String decode(Uint8List bytes) {
    if (bytes.length > maxBytes) throw const FormatException();
    var text = utf8.decode(bytes);
    if (text.startsWith('\uFEFF')) text = text.substring(1);
    if (text.characters.length > maxCharacters ||
        RegExp(r'[\x00-\x08\x0B\x0C\x0E-\x1F]').hasMatch(text)) {
      throw const FormatException();
    }
    return text;
  }

  /// On Web the download is handed to the browser, whose final disk write is
  /// outside the app's observation. Native cancellation returns false.
  Future<bool> save(String text) async {
    if (!canSave) throw UnsupportedError('File saving is unavailable.');
    final bytes = Uint8List.fromList(utf8.encode(text));
    decode(bytes);
    final fileName =
        'oevira-task-draft-${DateTime.now().millisecondsSinceEpoch}.txt';
    final file = XFile.fromData(bytes, mimeType: 'text/plain', name: fileName);
    if (kIsWeb) {
      await file.saveTo(fileName);
      return true;
    }
    final location = await getSaveLocation(
      suggestedName: fileName,
      acceptedTypeGroups: [_textType],
    );
    if (location == null) return false;
    await file.saveTo(location.path);
    return true;
  }
}
