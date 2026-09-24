import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

Widget sharedTestApp(
  Widget child, {
  Locale locale = const Locale('zh', 'CN'),
}) => MaterialApp(
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

Map<String, dynamic> sharedRuntimeResponse(
  String screen,
  Map<String, dynamic> data, {
  Map<String, dynamic>? scope,
  Map<String, dynamic>? permission,
}) => {
  'ok': true,
  'screen': screen,
  'source': 'runtime',
  'bound': true,
  'scope': scope ?? {'mode': 'GLOBAL_ALL'},
  'permission': permission ?? {'read': true, 'decision': 'ALLOW'},
  'data': data,
};

Map<String, dynamic> sharedProjection({
  required Map<String, dynamic> scope,
  String canonicalReference = 'evidence:canonical:shared-verified',
  String assurance = 'writer-authenticated',
  String digest = '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
  int version = 2,
  bool readAllowed = true,
  int integrityVersion = 2,
  bool integrityVerified = true,
  bool lineageVerified = true,
  bool? originVerified,
}) {
  final projectionScope = Map<String, dynamic>.from(scope);
  if (projectionScope['mode'] == 'GLOBAL_ALL') {
    projectionScope
      ..remove('subject_id')
      ..remove('brand_focus_id')
      ..remove('focus_id')
      ..remove('global')
      ..['global_all_granted'] = true;
  }
  return <String, dynamic>{
    'contract': 'lumenis.shared.experience-row-projection',
    'version': version,
    'read_allowed': readAllowed,
    'scope': projectionScope,
    'evidence': <String, dynamic>{'canonical_reference': canonicalReference},
    'integrity': <String, dynamic>{
      'integrity_version': integrityVersion,
      'verified': integrityVerified,
      'lineage_verified': lineageVerified,
      'assurance': assurance,
      'algorithm': assurance == 'writer-authenticated' ? 'hmac-sha256' : 'sha256',
      'digest': digest,
    },
    'origin_verified': ?originVerified,
  };
}

Map<String, dynamic> sharedResponseWithRowScopes(
  Map<String, dynamic> base, {
  required Map<String, dynamic> pageScope,
  required Map<String, Map<String, dynamic>> rowScopes,
}) {
  final response = Map<String, dynamic>.from(base);
  response['scope'] = pageScope;
  final data = Map<String, dynamic>.from(base['data'] as Map);
  for (final entry in rowScopes.entries) {
    final rows = data[entry.key];
    if (rows is! List) continue;
    data[entry.key] = rows
        .map((item) {
          final row = Map<String, dynamic>.from(item as Map);
          final originalProjection = row['projection'] as Map?;
          row['projection'] = sharedProjection(
            scope: entry.value,
            originVerified: originalProjection?['origin_verified'] as bool?,
          );
          return row;
        })
        .toList(growable: false);
  }
  response['data'] = data;
  return response;
}

String visibleSharedCopy(WidgetTester tester) => <String>[
  ...tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.semanticsLabel ?? ''),
  ...tester
      .widgetList<Semantics>(find.byType(Semantics))
      .map((widget) => widget.properties.label ?? ''),
  ...tester
      .widgetList<SelectableText>(find.byType(SelectableText))
      .map((widget) => widget.data ?? ''),
].join('\n');

void expectNoSharedRawMarkers(WidgetTester tester) {
  final copy = visibleSharedCopy(tester);
  expect(copy, isNot(contains('<script>')));
  expect(copy, isNot(contains('raw-secret-marker')));
  expect(copy, isNot(contains('PRIVATE-ID')));
  expect(copy, isNot(contains('/private/')));
  expect(copy, isNot(contains('provider-secret')));
}
