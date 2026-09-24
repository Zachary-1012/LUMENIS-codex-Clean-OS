import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import 'lumenis_copy.g.dart';

/// Runtime access to the canonical copy deltas in contracts/experience/i18n.
///
/// This class is a consumer of the existing translation contract, not a second
/// vocabulary owner. Regenerate [lumenis_copy.g.dart] with
/// `dart run tool/generate_lumenis_copy.dart` from the app directory.
class LumenisLocalizations {
  const LumenisLocalizations(this.locale);

  final Locale locale;

  static const supportedLocales = <Locale>[
    Locale('zh', 'CN'),
    Locale('en'),
    Locale('ko'),
  ];

  static const LocalizationsDelegate<LumenisLocalizations> delegate =
      _LumenisLocalizationsDelegate();

  static LumenisLocalizations of(BuildContext context) {
    final result = Localizations.of<LumenisLocalizations>(
      context,
      LumenisLocalizations,
    );
    assert(result != null, 'LumenisLocalizations is missing from the app.');
    return result!;
  }

  static Locale resolve(Locale? requested) {
    final languageCode = requested?.languageCode.toLowerCase();
    return switch (languageCode) {
      'en' => const Locale('en'),
      'ko' => const Locale('ko'),
      _ => const Locale('zh', 'CN'),
    };
  }

  String text(String key, {Map<String, Object?> values = const {}}) {
    final localeKey = _localeKey(locale);
    final template = lumenisCopy[localeKey]?[key] ?? lumenisCopy['zh-CN']?[key];
    if (template == null) {
      throw FlutterError('Missing LUMENIS copy contract key: $key');
    }
    var value = template;
    for (final entry in values.entries) {
      value = value.replaceAll('{${entry.key}}', '${entry.value}');
    }
    return value;
  }

  static String _localeKey(Locale locale) => switch (locale.languageCode) {
    'en' => 'en',
    'ko' => 'ko',
    _ => 'zh-CN',
  };
}

class _LumenisLocalizationsDelegate
    extends LocalizationsDelegate<LumenisLocalizations> {
  const _LumenisLocalizationsDelegate();

  @override
  bool isSupported(Locale locale) => LumenisLocalizations.supportedLocales.any(
    (supported) => supported.languageCode == locale.languageCode,
  );

  @override
  Future<LumenisLocalizations> load(Locale locale) =>
      SynchronousFuture<LumenisLocalizations>(
        LumenisLocalizations(LumenisLocalizations.resolve(locale)),
      );

  @override
  bool shouldReload(_LumenisLocalizationsDelegate old) => false;
}

extension LumenisLocalizationsBuildContext on BuildContext {
  LumenisLocalizations get lumenisL10n => LumenisLocalizations.of(this);
}
