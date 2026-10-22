import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/shared/sh01/manuscript_draft_files.dart';

void main() {
  group('ManuscriptDraftFiles', () {
    test('round-trips Unicode, multiline and incomplete manuscript text', () {
      final manuscript = <String, dynamic>{
        'title': '春季企划 🌱',
        'summary': '第一行\n第二行',
        'sections': [
          {'heading': 'Opening', 'body': 'line one\nline two'},
          {'heading': '', 'body': ''},
        ],
        'language': 'zh',
        'authorship': 'user_supplied',
      };

      final bytes = ManuscriptDraftFiles.encode(manuscript);
      final document = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;

      expect(document.keys.toSet(), {'schema', 'manuscript'});
      expect(document['schema'], 'lumenis.manuscript-draft/v1');
      expect(document['manuscript'], manuscript);
      expect(ManuscriptDraftFiles.decode(bytes), manuscript);
    });

    test('accepts a title with 300 Unicode code points', () {
      final manuscript = _validManuscript()..['title'] = '😀' * 300;

      expect(
        ManuscriptDraftFiles.decode(ManuscriptDraftFiles.encode(manuscript)),
        manuscript,
      );
    });

    test('allows empty text and the maximum section count', () {
      final manuscript = _validManuscript()
        ..['title'] = ''
        ..['sections'] = List.generate(
          64,
          (_) => <String, String>{'heading': '', 'body': ''},
        );

      expect(
        ManuscriptDraftFiles.decode(ManuscriptDraftFiles.encode(manuscript)),
        manuscript,
      );
    });

    test('rejects the wrong schema, malformed UTF-8 and invalid JSON', () {
      expect(
        () => ManuscriptDraftFiles.decode(_bytes(_document(schema: 'v2'))),
        throwsFormatException,
      );
      expect(
        () => ManuscriptDraftFiles.decode(Uint8List.fromList([0xC3, 0x28])),
        throwsFormatException,
      );
      expect(
        () => ManuscriptDraftFiles.decode(Uint8List.fromList(utf8.encode('{'))),
        throwsFormatException,
      );
    });

    test('rejects unknown document and manuscript fields', () {
      final extraDocumentField = _document()..['actor'] = 'user-1';
      expect(
        () => ManuscriptDraftFiles.decode(_bytes(extraDocumentField)),
        throwsFormatException,
      );

      final manuscript = _validManuscript()..['task_ref'] = 'task-1';
      expect(
        () => ManuscriptDraftFiles.decode(
          _bytes(_document(manuscript: manuscript)),
        ),
        throwsFormatException,
      );

      final section = <String, dynamic>{
        'heading': 'H',
        'body': 'B',
        'scope': 'BMP',
      };
      final sectionRef = _validManuscript()..['sections'] = [section];
      expect(
        () => ManuscriptDraftFiles.encode(sectionRef),
        throwsFormatException,
      );
    });

    test('rejects invalid types, enum values, section counts and controls', () {
      final nonStringTitle = _validManuscript()..['title'] = 42;
      expect(
        () => ManuscriptDraftFiles.encode(nonStringTitle),
        throwsFormatException,
      );

      final invalidLanguage = _validManuscript()..['language'] = 'fr';
      expect(
        () => ManuscriptDraftFiles.encode(invalidLanguage),
        throwsFormatException,
      );

      final noSections = _validManuscript()..['sections'] = <Object>[];
      expect(
        () => ManuscriptDraftFiles.encode(noSections),
        throwsFormatException,
      );

      final tooManySections = _validManuscript()
        ..['sections'] = List.generate(
          65,
          (_) => <String, String>{'heading': '', 'body': ''},
        );
      expect(
        () => ManuscriptDraftFiles.encode(tooManySections),
        throwsFormatException,
      );

      final controlCharacter = _validManuscript()
        ..['summary'] = 'bad\u0007text';
      expect(
        () => ManuscriptDraftFiles.encode(controlCharacter),
        throwsFormatException,
      );
    });

    test('rejects overlong titles and oversized UTF-8 documents', () {
      final overlongTitle = _validManuscript()..['title'] = '字' * 301;
      expect(
        () => ManuscriptDraftFiles.encode(overlongTitle),
        throwsFormatException,
      );

      expect(
        () => ManuscriptDraftFiles.decode(
          Uint8List(ManuscriptDraftFiles.maxBytes + 1),
        ),
        throwsFormatException,
      );

      final oversizedBody = _validManuscript()
        ..['sections'] = [
          {'heading': '', 'body': 'x' * ManuscriptDraftFiles.maxBytes},
        ];
      expect(
        () => ManuscriptDraftFiles.encode(oversizedBody),
        throwsFormatException,
      );
    });
  });
}

Map<String, dynamic> _validManuscript() => {
  'title': 'A draft',
  'summary': '',
  'sections': [
    {'heading': '', 'body': ''},
  ],
  'language': 'en',
  'authorship': 'assisted',
};

Map<String, dynamic> _document({
  String schema = 'lumenis.manuscript-draft/v1',
  Map<String, dynamic>? manuscript,
}) => {'schema': schema, 'manuscript': manuscript ?? _validManuscript()};

Uint8List _bytes(Object value) =>
    Uint8List.fromList(utf8.encode(jsonEncode(value)));
