import 'dart:ui' show Tristate;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_icon.dart';
import 'package:lumenis_app/core/lumenis_icon_geometry.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';

void main() {
  testWidgets(
    'disclosure glyph follows tap and controller with reduced motion',
    (tester) async {
      final controller = ExpansibleController();
      addTearDown(controller.dispose);
      await tester.pumpWidget(
        MaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(disableAnimations: true),
            child: Scaffold(
              body: ExpansionTile(
                controller: controller,
                title: const Text('Source details'),
                trailing: const LumenisExpansionIndicator(),
                children: const [Text('Original source')],
              ),
            ),
          ),
        ),
      );
      final rotation = find.descendant(
        of: find.byType(LumenisExpansionIndicator),
        matching: find.byType(AnimatedRotation),
      );
      expect(tester.widget<AnimatedRotation>(rotation).turns, 0);
      expect(tester.widget<AnimatedRotation>(rotation).duration, Duration.zero);
      await tester.tap(find.text('Source details'));
      await tester.pumpAndSettle();
      expect(controller.isExpanded, isTrue);
      expect(tester.widget<AnimatedRotation>(rotation).turns, .5);
      expect(find.text('Original source'), findsOneWidget);
      controller.collapse();
      await tester.pumpAndSettle();
      expect(tester.widget<AnimatedRotation>(rotation).turns, 0);
      expect(find.text('Original source'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  group('LumenisIcon geometry coverage', () {
    test(
      'maps every current Material symbol to nonempty reviewed geometry',
      () {
        expect(lumenisIconGeometry, hasLength(lumenisIconGeometryCount));
        expect(LumenisIcon.supportedSymbols, hasLength(lumenisIconSymbolCount));
        expect(
          LumenisIcon.supportedIcons.keys,
          unorderedEquals(LumenisIcon.supportedSymbols.keys),
        );

        for (final geometry in lumenisIconGeometry.values) {
          expect(geometry.isNotEmpty, isTrue);
        }

        for (final entry in LumenisIcon.supportedSymbols.entries) {
          final iconData = LumenisIcon.supportedIcons[entry.key];
          expect(iconData, isNotNull, reason: entry.key);
          expect(
            LumenisIcon.glyphNameFor(iconData),
            entry.value,
            reason: entry.key,
          );
          expect(
            LumenisIcon.geometryForSymbol(entry.key)?.isNotEmpty,
            isTrue,
            reason: entry.key,
          );
        }
      },
    );

    test('unknown symbols do not enter the reviewed alias map', () {
      const unknown = IconData(0xe000, fontFamily: 'MaterialIcons');
      expect(LumenisIcon.glyphNameFor(unknown), isNull);
      expect(LumenisIcon.geometryForSymbol('futureMaterialSymbol'), isNull);
    });
  });

  testWidgets('unknown symbols and unsupported font effects use native Icon', (
    tester,
  ) async {
    const unknown = IconData(0xe000, fontFamily: 'MaterialIcons');
    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.ltr,
        child: Row(
          children: [LumenisIcon(unknown), LumenisIcon(Icons.add, fill: 1)],
        ),
      ),
    );

    expect(find.byType(CustomPaint), findsNothing);
    expect(find.byType(RichText), findsNWidgets(2));
  });

  testWidgets(
    'inherits IconTheme size, color, and opacity while retaining identity',
    (tester) async {
      await tester.pumpWidget(
        IconTheme(
          data: const IconThemeData(
            color: Colors.blue,
            size: 19,
            opacity: 0.25,
          ),
          child: const Directionality(
            textDirection: TextDirection.ltr,
            child: LumenisIcon(Icons.add),
          ),
        ),
      );

      expect(find.byIcon(Icons.add), findsOneWidget);
      final customPaint = tester.widget<CustomPaint>(find.byType(CustomPaint));
      expect(tester.getSize(find.byType(CustomPaint)), const Size(19, 19));
      expect(
        (customPaint.painter! as LumenisIconPainter).color,
        Colors.blue.withValues(alpha: 0.25),
      );
    },
  );

  testWidgets('explicit color and size override the theme before opacity', (
    tester,
  ) async {
    await tester.pumpWidget(
      IconTheme(
        data: const IconThemeData(color: Colors.blue, size: 19, opacity: 0.5),
        child: const Directionality(
          textDirection: TextDirection.ltr,
          child: LumenisIcon(Icons.add, size: 21, color: Colors.red),
        ),
      ),
    );

    final customPaint = tester.widget<CustomPaint>(find.byType(CustomPaint));
    expect(tester.getSize(find.byType(CustomPaint)), const Size(21, 21));
    expect(
      (customPaint.painter! as LumenisIconPainter).color,
      Colors.red.withValues(alpha: 0.5),
    );
  });

  testWidgets(
    'null icon preserves its semantic label and requested footprint',
    (tester) async {
      await withSemanticsEnabled(tester, () async {
        await tester.pumpWidget(
          const Directionality(
            textDirection: TextDirection.ltr,
            child: LumenisIcon(
              null,
              size: 23,
              semanticLabel: 'No icon artwork',
            ),
          ),
        );

        expect(find.byType(CustomPaint), findsNothing);
        expect(find.bySemanticsLabel('No icon artwork'), findsOneWidget);
        expect(
          find.byWidgetPredicate(
            (widget) =>
                widget is SizedBox && widget.width == 23 && widget.height == 23,
          ),
          findsOneWidget,
        );
      });
    },
  );

  testWidgets('semantic label remains outside excluded artwork semantics', (
    tester,
  ) async {
    await withSemanticsEnabled(tester, () async {
      await tester.pumpWidget(
        const Directionality(
          textDirection: TextDirection.ltr,
          child: LumenisIcon(
            Icons.play_arrow_rounded,
            semanticLabel: 'Play preview',
          ),
        ),
      );

      expect(find.byType(ExcludeSemantics), findsOneWidget);
      expect(find.bySemanticsLabel('Play preview'), findsOneWidget);
    });
  });

  testWidgets('mirrors only symbols marked for text direction', (tester) async {
    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.rtl,
        child: LumenisIcon(Icons.arrow_back),
      ),
    );
    expect(find.byType(Transform), findsOneWidget);
    expect(
      tester.widget<Transform>(find.byType(Transform)).transform.storage[0],
      -1,
    );

    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.ltr,
        child: LumenisIcon(Icons.arrow_back),
      ),
    );
    expect(find.byType(Transform), findsNothing);

    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.rtl,
        child: LumenisIcon(Icons.play_arrow_rounded),
      ),
    );
    expect(find.byType(Transform), findsNothing);
  });

  testWidgets('supports opt-in MediaQuery text scaling', (tester) async {
    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(textScaler: TextScaler.linear(2)),
        child: const Directionality(
          textDirection: TextDirection.ltr,
          child: LumenisIcon(Icons.search, size: 16, applyTextScaling: true),
        ),
      ),
    );

    expect(tester.getSize(find.byType(CustomPaint)), const Size(32, 32));
  });

  testWidgets(
    'native IconButton keeps its accessible target and disabled state',
    (tester) async {
      var pressed = false;

      await withSemanticsEnabled(tester, () async {
        await tester.pumpWidget(
          MaterialApp(
            theme: LumenisTheme.light,
            home: Scaffold(
              body: Center(
                child: IconButton(
                  tooltip: 'Pause preview',
                  onPressed: null,
                  icon: const LumenisIcon(
                    Icons.pause_rounded,
                    semanticLabel: 'Pause preview',
                  ),
                ),
              ),
            ),
          ),
        );

        final targetSize = tester.getSize(find.byType(IconButton));
        expect(targetSize.width, greaterThanOrEqualTo(48));
        expect(targetSize.height, greaterThanOrEqualTo(48));
        expect(find.byIcon(Icons.pause_rounded), findsOneWidget);
        expect(
          find.byWidgetPredicate(
            (widget) =>
                widget is CustomPaint && widget.painter is LumenisIconPainter,
          ),
          findsOneWidget,
        );
        final actionFinder = find.bySemanticsLabel('Pause preview');
        expect(actionFinder, findsOneWidget);
        final data = tester.getSemantics(actionFinder).getSemanticsData();
        expect(data.flagsCollection.isButton, isTrue);
        expect(data.flagsCollection.isEnabled, Tristate.isFalse);

        await tester.tap(find.byType(IconButton));
        expect(pressed, isFalse);
      });
    },
  );
}

Future<void> withSemanticsEnabled(
  WidgetTester tester,
  Future<void> Function() body,
) async {
  final handle = tester.ensureSemantics();
  var disposed = false;
  void dispose() {
    if (!disposed) {
      handle.dispose();
      disposed = true;
    }
  }

  addTearDown(dispose);
  try {
    await body();
  } finally {
    dispose();
  }
}
