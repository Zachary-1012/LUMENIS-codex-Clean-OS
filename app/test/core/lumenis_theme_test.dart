import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:lumenis_app/core/lumenis_theme.dart';

void main() {
  test('light and dark palette build distinct Material themes', () {
    expect(LumenisTheme.light.brightness, Brightness.light);
    expect(LumenisTheme.dark.brightness, Brightness.dark);
    expect(LumenisTheme.light.extension<LumenisPalette>()?.canvas, isNotNull);
    expect(
      LumenisTheme.light.extension<LumenisPalette>()?.canvas,
      isNot(LumenisTheme.dark.extension<LumenisPalette>()?.canvas),
    );
  });

  test('semantic colors preserve light tones and meet dark text contrast', () {
    const lightSemantic = <Color>[
      LumenisTheme.cth,
      LumenisTheme.bmp,
      LumenisTheme.ai,
      LumenisTheme.shared,
      LumenisTheme.system,
      LumenisTheme.positive,
      LumenisTheme.caution,
      LumenisTheme.danger,
    ];
    final lightPalette = LumenisTheme.lightPalette;
    final darkPalette = LumenisTheme.darkPalette;
    final lightResolved = <Color>[
      lightPalette.cth,
      lightPalette.bmp,
      lightPalette.ai,
      lightPalette.shared,
      lightPalette.system,
      lightPalette.positive,
      lightPalette.caution,
      lightPalette.danger,
    ];
    final darkResolved = <Color>[
      darkPalette.cth,
      darkPalette.bmp,
      darkPalette.ai,
      darkPalette.shared,
      darkPalette.system,
      darkPalette.positive,
      darkPalette.caution,
      darkPalette.danger,
    ];

    expect(lightResolved, lightSemantic);
    for (final color in darkResolved) {
      expect(
        _contrastRatio(color, darkPalette.surface),
        greaterThanOrEqualTo(4.5),
      );
      expect(
        _contrastRatio(color, darkPalette.surfaceRaised),
        greaterThanOrEqualTo(4.5),
      );
    }

    final darkScheme = LumenisTheme.dark.colorScheme;
    expect(darkScheme.secondary, darkPalette.bmp);
    expect(darkScheme.error, darkPalette.danger);
  });

  testWidgets('changing palette preserves an active editable draft', (
    tester,
  ) async {
    final controller = TextEditingController();
    var dark = false;
    late StateSetter setTheme;

    await tester.pumpWidget(
      StatefulBuilder(
        builder: (context, update) {
          setTheme = update;
          return MaterialApp(
            theme: LumenisTheme.forPalette(
              dark ? LumenisTheme.darkPalette : LumenisTheme.lightPalette,
            ),
            home: Scaffold(
              body: TextField(
                key: const ValueKey('theme-switch-input'),
                controller: controller,
              ),
            ),
          );
        },
      ),
    );

    final input = find.byKey(const ValueKey('theme-switch-input'));
    await tester.enterText(input, 'draft survives the switch');
    expect(controller.text, 'draft survives the switch');
    expect(Theme.of(tester.element(input)).brightness, Brightness.light);
    expect(FocusManager.instance.primaryFocus?.hasFocus, isTrue);

    setTheme(() => dark = true);
    await tester.pumpAndSettle();

    expect(controller.text, 'draft survives the switch');
    expect(Theme.of(tester.element(input)).brightness, Brightness.dark);
    expect(
      LumenisTheme.of(tester.element(input)).canvas,
      LumenisTheme.darkPalette.canvas,
    );
    expect(FocusManager.instance.primaryFocus?.hasFocus, isTrue);

    await tester.pumpWidget(const SizedBox.shrink());
    controller.dispose();
  });
}

double _contrastRatio(Color foreground, Color background) {
  final foregroundLuminance = foreground.computeLuminance();
  final backgroundLuminance = background.computeLuminance();
  final lighter = foregroundLuminance > backgroundLuminance
      ? foregroundLuminance
      : backgroundLuminance;
  final darker = foregroundLuminance > backgroundLuminance
      ? backgroundLuminance
      : foregroundLuminance;
  return (lighter + 0.05) / (darker + 0.05);
}
