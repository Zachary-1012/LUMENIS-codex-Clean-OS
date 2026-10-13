import 'dart:convert';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';

/// Explicit user-picked local manuscript files.
///
/// These files contain editable draft text only. They are never uploaded,
/// imported as canonical facts, or treated as a backend Artifact.
class ManuscriptDraftFiles {
  static const maxBytes = 1024 * 1024;
  static const _schema = 'lumenis.manuscript-draft/v1';
  static const _fileName = 'manuscript.lumenis-document.json';
  static const _jsonType = XTypeGroup(
    label: 'LUMENIS manuscript draft',
    extensions: ['json'],
    mimeTypes: ['application/json'],
    uniformTypeIdentifiers: ['public.json'],
  );

  static const _documentKeys = {'schema', 'manuscript'};
  static const _manuscriptKeys = {
    'title',
    'summary',
    'sections',
    'language',
    'authorship',
  };
  static const _sectionKeys = {'heading', 'body'};
  static const _languages = {'zh', 'en', 'ko'};
  static const _authorshipValues = {'user_supplied', 'assisted'};
  static final _disallowedControls = RegExp(
    r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]',
  );

  bool get canSave =>
      kIsWeb ||
      const {
        TargetPlatform.windows,
        TargetPlatform.macOS,
        TargetPlatform.linux,
      }.contains(defaultTargetPlatform);

  Future<Map<String, dynamic>?> open() async {
    final file = await openFile(acceptedTypeGroups: [_jsonType]);
    if (file == null) return null;
    if (await file.length() > maxBytes) throw const FormatException();
    return decode(await file.readAsBytes());
  }

  /// On Web, `true` means the browser download was requested. The browser
  /// controls whether the user completes the final disk write.
  /// Native cancellation returns `false`.
  Future<bool> save(Map<String, dynamic> manuscript) async {
    if (!canSave) {
      throw UnsupportedError('Manuscript file saving is unavailable.');
    }

    final bytes = encode(manuscript);
    final file = XFile.fromData(
      bytes,
      mimeType: 'application/json',
      name: _fileName,
    );
    if (kIsWeb) {
      await file.saveTo(_fileName);
      return true;
    }

    final location = await getSaveLocation(suggestedName: _fileName);
    if (location == null) return false;
    await file.saveTo(location.path);
    return true;
  }

  /// Decodes the versioned document envelope and returns only its manuscript.
  static Map<String, dynamic> decode(Uint8List bytes) {
    if (bytes.length > maxBytes) throw const FormatException();

    final decoded = jsonDecode(utf8.decode(bytes));
    if (decoded is! Map || !_hasExactKeys(decoded, _documentKeys)) {
      throw const FormatException();
    }
    if (decoded['schema'] != _schema) throw const FormatException();
    return _validateManuscript(decoded['manuscript']);
  }

  /// Encodes a manuscript in the versioned local draft envelope.
  static Uint8List encode(Map<String, dynamic> manuscript) {
    final normalized = _validateManuscript(manuscript);
    final bytes = Uint8List.fromList(
      utf8.encode(jsonEncode({'schema': _schema, 'manuscript': normalized})),
    );
    if (bytes.length > maxBytes) throw const FormatException();
    return bytes;
  }

  static Map<String, dynamic> _validateManuscript(Object? value) {
    if (value is! Map || !_hasExactKeys(value, _manuscriptKeys)) {
      throw const FormatException();
    }

    final title = _text(value['title']);
    final summary = _text(value['summary']);
    if (title.runes.length > 300) throw const FormatException();

    final rawSections = value['sections'];
    if (rawSections is! List ||
        rawSections.isEmpty ||
        rawSections.length > 64) {
      throw const FormatException();
    }

    final sections = <Map<String, dynamic>>[];
    for (final rawSection in rawSections) {
      if (rawSection is! Map || !_hasExactKeys(rawSection, _sectionKeys)) {
        throw const FormatException();
      }
      sections.add({
        'heading': _text(rawSection['heading']),
        'body': _text(rawSection['body']),
      });
    }

    final language = value['language'];
    if (language is! String || !_languages.contains(language)) {
      throw const FormatException();
    }
    final authorship = value['authorship'];
    if (authorship is! String || !_authorshipValues.contains(authorship)) {
      throw const FormatException();
    }

    return {
      'title': title,
      'summary': summary,
      'sections': sections,
      'language': language,
      'authorship': authorship,
    };
  }

  static String _text(Object? value) {
    if (value is! String || _disallowedControls.hasMatch(value)) {
      throw const FormatException();
    }
    return value;
  }

  static bool _hasExactKeys(Map value, Set<String> expected) =>
      value.length == expected.length &&
      value.keys.every((key) => key is String && expected.contains(key));
}
