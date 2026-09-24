import 'dart:convert';
import 'dart:io';

const _locales = <String>['zh-CN', 'en', 'ko'];

Future<void> main() async {
  final appRoot = Directory.current;
  final contractRoot = Directory.fromUri(
    appRoot.uri.resolve('../contracts/experience/i18n/'),
  );
  final translations = <String, Map<String, String>>{};

  for (final locale in _locales) {
    final file = File.fromUri(contractRoot.uri.resolve('$locale.delta.json'));
    if (!await file.exists()) {
      stderr.writeln('Missing canonical copy contract: ${file.path}');
      exitCode = 1;
      return;
    }
    final decoded = jsonDecode(await file.readAsString());
    if (decoded is! Map<String, dynamic> || decoded['locale'] != locale) {
      stderr.writeln('Invalid locale contract: ${file.path}');
      exitCode = 1;
      return;
    }
    final delta = decoded['delta'];
    if (delta is! Map<String, dynamic> ||
        delta.values.any((value) => value is! String)) {
      stderr.writeln('Invalid copy delta: ${file.path}');
      exitCode = 1;
      return;
    }
    translations[locale] = delta.cast<String, String>();
  }

  final canonicalKeys = translations.values.first.keys.toSet();
  for (final entry in translations.entries.skip(1)) {
    if (!canonicalKeys.containsAll(entry.value.keys) ||
        !entry.value.keys.toSet().containsAll(canonicalKeys)) {
      stderr.writeln('Copy keys differ for locale ${entry.key}.');
      exitCode = 1;
      return;
    }
  }

  final output = StringBuffer()
    ..writeln('// GENERATED FILE. Do not edit directly.')
    ..writeln('// Source: contracts/experience/i18n/{zh-CN,en,ko}.delta.json')
    ..writeln('const Map<String, Map<String, String>> lumenisCopy = {');
  for (final locale in _locales) {
    output.writeln('  ${_dartString(locale)}: {');
    for (final entry in translations[locale]!.entries) {
      output.writeln(
        '    ${_dartString(entry.key)}: ${_dartString(entry.value)},',
      );
    }
    output.writeln('  },');
  }
  output.writeln('};');

  final destination = File.fromUri(
    appRoot.uri.resolve('lib/l10n/lumenis_copy.g.dart'),
  );
  await destination.parent.create(recursive: true);
  await destination.writeAsString(output.toString());
  stdout.writeln(
    'Generated ${destination.path} from the three copy contracts.',
  );
}

String _dartString(String value) => jsonEncode(value).replaceAll(r'$', r'\$');
