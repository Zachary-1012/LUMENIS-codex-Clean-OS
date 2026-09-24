import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/l10n/lumenis_copy.g.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  test('Chinese, English and Korean use the same semantic copy keys', () {
    final locales = lumenisCopy.keys.toList()..sort();
    expect(locales, ['en', 'ko', 'zh-CN']);

    final canonicalKeys = lumenisCopy['zh-CN']!.keys.toSet();
    for (final locale in locales) {
      expect(lumenisCopy[locale]!.keys.toSet(), canonicalKeys);
      final contract =
          jsonDecode(
                File(
                  '../contracts/experience/i18n/$locale.delta.json',
                ).readAsStringSync(),
              )
              as Map<String, dynamic>;
      expect(lumenisCopy[locale], contract['delta']);
    }
    final registry =
        jsonDecode(
              File(
                '../contracts/experience/i18n/copy-registry.json',
              ).readAsStringSync(),
            )
            as Map<String, dynamic>;
    for (final locale in locales) {
      expect(
        lumenisCopy[locale]!.length,
        registry['locales'][locale]['key_count'],
      );
    }
  });

  test('device locales resolve to the supported product languages', () {
    expect(
      LumenisLocalizations.resolve(const Locale('en', 'GB')),
      const Locale('en'),
    );
    expect(
      LumenisLocalizations.resolve(const Locale('ko', 'KR')),
      const Locale('ko'),
    );
    expect(
      LumenisLocalizations.resolve(const Locale('zh', 'TW')),
      const Locale('zh', 'CN'),
    );
    expect(LumenisLocalizations.resolve(null), const Locale('zh', 'CN'));
  });

  test(
    'copy values interpolate user-visible quantities without leaking keys',
    () {
      final english = LumenisLocalizations(const Locale('en'));
      expect(
        english.text('shell.subjects.heading', values: {'count': 12}),
        'Available business subjects · 12',
      );
      expect(english.text('context.mode.global_all'), 'All accessible scope');
    },
  );
}
