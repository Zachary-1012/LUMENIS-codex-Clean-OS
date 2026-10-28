import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_screen.dart';
import 'package:lumenis_app/navigation/lumenis_leave_guard.dart';
import '../shared_test_support.dart';
import 'office_test_support.dart';

void main() {
  testWidgets(
    'the existing imported reader edits, saves, reads back and downloads the same Office work',
    (tester) async {
      final repo = OfficeTestRepository();
      final files = OfficeTestFiles();
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        sharedTestApp(
          Sh02Screen(
            client: LumenisCoreClient(),
            repository: repo,
            officeRepository: repo,
            officeFiles: files,
            initialArtifactId: officeId(1),
            initialWorkKind: 'material',
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('sh02-office-mode')));
      await tester.tap(find.byKey(const Key('sh02-office-mode')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(
        find.byKey(ValueKey('sh02-office-object-${officeObjectId(1)}')),
      );
      await tester.tap(
        find.byKey(ValueKey('sh02-office-object-${officeObjectId(1)}')),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('sh02-office-value')),
        'My revised original writing',
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('sh02-office-reason')));
      await tester.enterText(
        find.byKey(const Key('sh02-office-reason')),
        'Correct this passage',
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('sh02-office-save')));
      await tester.tap(find.byKey(const Key('sh02-office-save')));
      await tester.pumpAndSettle();
      expect(repo.latest, 2);
      expect(
        repo.requests.single.single['value'],
        'My revised original writing',
      );
      expect(find.text('第 2 版已保存并读回'), findsOneWidget);
      expect(find.text('My revised original writing'), findsWidgets);
      await tester.ensureVisible(find.byKey(const Key('sh02-office-download')));
      await tester.tap(find.byKey(const Key('sh02-office-download')));
      await tester.pumpAndSettle();
      expect(repo.downloaded.single, '${officeId(2)}/edited-version-2.docx');
      expect(files.saved!.bytes, [80, 75, 2]);
      expect(repo.values[1]!.first['value'], 'Original writing 1');
      expect(tester.takeException(), isNull);
    },
  );

  for (final locale in const [Locale('zh', 'CN'), Locale('en'), Locale('ko')]) {
    testWidgets(
      'narrow ${locale.languageCode} keeps typed changes when leaving is cancelled',
      (tester) async {
        final repo = OfficeTestRepository();
        final guard = LumenisLeaveGuard();
        addTearDown(guard.dispose);
        await tester.binding.setSurfaceSize(const Size(390, 844));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        await tester.pumpWidget(
          sharedTestApp(
            LumenisLeaveScope(
              guard: guard,
              child: Sh02Screen(
                client: LumenisCoreClient(),
                repository: repo,
                officeRepository: repo,
                initialArtifactId: officeId(1),
                initialWorkKind: 'material',
              ),
            ),
            locale: locale,
          ),
        );
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.byKey(const Key('sh02-office-mode')));
        await tester.tap(find.byKey(const Key('sh02-office-mode')));
        await tester.pumpAndSettle();
        final object = find.byKey(
          ValueKey('sh02-office-object-${officeObjectId(1)}'),
        );
        await tester.ensureVisible(object);
        await tester.tap(object);
        await tester.pumpAndSettle();
        final field = find.byKey(const Key('sh02-office-value'));
        await tester.ensureVisible(field);
        await tester.enterText(field, 'Preserved draft');
        await tester.pump();
        expect(guard.needsProtection, isTrue);
        final leaving = guard.requestLeave();
        await tester.pumpAndSettle();
        final keep = switch (locale.languageCode) {
          'en' => 'Keep editing',
          'ko' => '계속 편집',
          _ => '继续编辑',
        };
        await tester.tap(find.text(keep));
        await tester.pumpAndSettle();
        expect(await leaving, isFalse);
        expect(
          tester.widget<TextField>(field).controller!.text,
          'Preserved draft',
        );
        expect(repo.requests, isEmpty);
        expect(tester.takeException(), isNull);
      },
    );
  }
}
