import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/system/sys05/sys05_appearance_controller.dart';
import 'package:lumenis_app/features/system/sys05/sys05_appearance_editor.dart';
import 'package:lumenis_app/features/system/sys05/sys05_repository.dart';
import 'package:lumenis_app/features/system/sys05/sys05_screen.dart';
import 'package:lumenis_app/features/system/sys05/sys05_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  for (final locale in LumenisLocalizations.supportedLocales) {
    testWidgets('device settings opens existing directory in $locale', (
      tester,
    ) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final appearance = Sys05AppearanceController()..loaded = true;
      addTearDown(appearance.dispose);
      final repository = _PendingSettings();
      var opened = 0;
      await tester.pumpWidget(
        _host(
          Sys05AppearanceScope(
            controller: appearance,
            child: Sys05Screen(
              client: LumenisCoreClient(),
              repository: repository,
              onOpenSubjects: () => opened++,
            ),
          ),
          locale,
        ),
      );
      await tester.pumpAndSettle();

      final directory = find.byKey(
        const ValueKey('sys05/open-subject-directory'),
      );
      expect(
        find.descendant(
          of: directory,
          matching: find.text(
            LumenisLocalizations(locale).text('shell.open_subject_directory'),
          ),
        ),
        findsOneWidget,
      );
      await tester.tap(directory);
      expect(opened, 1);
      expect(repository.loads, 0);
      expect(find.byType(Sys05AppearanceEditor), findsOneWidget);
      expect(appearance.saving, isFalse);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('directory stays available when remote appearance fails', (
    tester,
  ) async {
    final repository = _PendingSettings();
    var opened = 0;
    await tester.pumpWidget(
      _host(
        Sys05Screen(
          client: LumenisCoreClient(),
          repository: repository,
          onOpenSubjects: () => opened++,
        ),
        const Locale('zh', 'CN'),
      ),
    );
    await tester.pump();
    final directory = find.byKey(
      const ValueKey('sys05/open-subject-directory'),
    );
    await tester.tap(directory);
    expect(opened, 1);
    repository.result.completeError(
      const LumenisCoreException('Settings unavailable', statusCode: 503),
    );
    await tester.pumpAndSettle();
    await tester.tap(directory);
    expect(opened, 2);
    expect(repository.loads, 1);
    expect(tester.takeException(), isNull);
  });
}

Widget _host(Widget child, Locale locale) => MaterialApp(
  theme: LumenisTheme.dark,
  locale: locale,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: Scaffold(body: child),
);

class _PendingSettings implements Sys05Repository {
  int loads = 0;
  final result = Completer<Sys05Snapshot>();

  @override
  Future<Sys05Snapshot> load() {
    loads++;
    return result.future;
  }
}
