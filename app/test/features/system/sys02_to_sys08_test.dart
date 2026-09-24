import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/system/sys02/sys02_repository.dart';
import 'package:lumenis_app/features/system/sys02/sys02_screen.dart';
import 'package:lumenis_app/features/system/sys02/sys02_snapshot.dart';
import 'package:lumenis_app/features/system/sys03/sys03_repository.dart';
import 'package:lumenis_app/features/system/sys03/sys03_screen.dart';
import 'package:lumenis_app/features/system/sys03/sys03_snapshot.dart';
import 'package:lumenis_app/features/system/sys04/sys04_repository.dart';
import 'package:lumenis_app/features/system/sys04/sys04_screen.dart';
import 'package:lumenis_app/features/system/sys04/sys04_snapshot.dart';
import 'package:lumenis_app/features/system/sys05/sys05_repository.dart';
import 'package:lumenis_app/features/system/sys05/sys05_screen.dart';
import 'package:lumenis_app/features/system/sys05/sys05_snapshot.dart';
import 'package:lumenis_app/features/system/sys05/sys05_view_model.dart';
import 'package:lumenis_app/features/system/sys06/sys06_repository.dart';
import 'package:lumenis_app/features/system/sys06/sys06_screen.dart';
import 'package:lumenis_app/features/system/sys06/sys06_snapshot.dart';
import 'package:lumenis_app/features/system/sys07/sys07_repository.dart';
import 'package:lumenis_app/features/system/sys07/sys07_screen.dart';
import 'package:lumenis_app/features/system/sys07/sys07_snapshot.dart';
import 'package:lumenis_app/features/system/sys08/sys08_repository.dart';
import 'package:lumenis_app/features/system/sys08/sys08_screen.dart';
import 'package:lumenis_app/features/system/sys08/sys08_snapshot.dart';

void main() {
  test('SYS-02 keeps unavailable metrics unavailable', () {
    final snapshot = Sys02Snapshot.fromResponse(
      _envelope(
        'SYS-02',
        sections: [
          {
            'type': 'kpis',
            'items': [
              {
                'id': 'sys02.active',
                'title': 'Active',
                'value': 0,
                'state': 'offline',
              },
            ],
          },
          {
            'type': 'table',
            'rows': [
              {
                '平台': 'Source A',
                '状态': 'MISSING',
                '解析记录': null,
                '说明': 'not collected',
              },
            ],
          },
        ],
      ),
    );

    expect(snapshot.metrics.single.value, isNull);
    expect(snapshot.collectors.single.parsedRecords, isNull);
    expect(snapshot.collectors.single.status, 'MISSING');
  });

  testWidgets(
    'SYS-02 recomposes for mobile and keeps the ingestion boundary visible',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        _host(
          Sys02Screen(
            client: LumenisCoreClient(),
            repository: _Sys02Repo(_sys02Snapshot()),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const ValueKey('sys02/layout-mobile')), findsOneWidget);
      expect(find.text('入链边界'), findsOneWidget);
      expect(find.text('MISSING'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  test(
    'SYS-03 separates schema version from readability and chain evidence',
    () {
      final snapshot = Sys03Snapshot.fromResponse(
        _envelope(
          'SYS-03',
          sections: [
            {
              'type': 'kpis',
              'items': [
                {'id': 'sys03.schema_versions', 'value': 0, 'state': 'offline'},
              ],
            },
            {
              'type': 'table',
              'rows': [
                {'检查项': 'foreign keys', '结果': 'UNKNOWN', 'state': 'unknown'},
              ],
            },
          ],
          truth: const {},
        ),
      );

      expect(snapshot.schemaVersions, isNull);
      expect(snapshot.readabilityState, 'notreturned');
      expect(snapshot.integrityState, 'unknown');
      expect(snapshot.checks.single.state, 'unknown');
      expect(snapshot.truthStages, isEmpty);
    },
  );

  test(
    'SYS-03 requires canonical verification and an Evidence reference for ready integrity',
    () {
      final snapshot = Sys03Snapshot.fromResponse(
        _envelope(
          'SYS-03',
          sections: [
            {
              'type': 'table',
              'rows': [
                {
                  '检查项': 'foreign keys',
                  '结果': 'PASS',
                  'state': 'pass',
                  'canonical_verified': true,
                  'evidence_ref': 'EV:db-foreign-keys',
                },
              ],
            },
          ],
        ),
      );

      expect(snapshot.integrityState, 'ready');
      expect(snapshot.checks.single.state, 'ready');
    },
  );

  test('SYS-03 rejects ready-looking checks without Evidence', () {
    final snapshot = Sys03Snapshot.fromResponse(
      _envelope(
        'SYS-03',
        sections: [
          {
            'type': 'table',
            'rows': [
              {
                '检查项': 'foreign keys',
                '结果': 'PASS',
                'state': 'ready',
                'canonical_verified': true,
              },
            ],
          },
        ],
      ),
    );

    expect(snapshot.integrityState, 'unknown');
    expect(snapshot.checks.single.state, 'unknown');
  });

  test('SYS-03 keeps malformed state fields unknown', () {
    final snapshot = Sys03Snapshot.fromResponse(
      _envelope(
        'SYS-03',
        sections: [
          {
            'type': 'table',
            'rows': [
              {
                '检查项': 'foreign keys',
                '结果': 'PASS',
                'state': {'value': 'ready'},
                'canonical_verified': true,
                'evidence_ref': 'EV:db-foreign-keys',
              },
            ],
          },
        ],
      ),
    );

    expect(snapshot.integrityState, 'unknown');
    expect(snapshot.checks.single.state, 'unknown');
  });

  testWidgets('SYS-03 keeps the validation spine readable on tablet', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _host(
        Sys03Screen(
          client: LumenisCoreClient(),
          repository: _Sys03Repo(_sys03Snapshot()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('sys03/layout-tablet')), findsOneWidget);
    expect(find.text('验证脊柱'), findsOneWidget);
    expect(find.text('状态未确认'), findsOneWidget);
    expect(find.text('当前接口未返回'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  test(
    'SYS-04 exposes only safe permission levels and never raw operation material',
    () {
      final snapshot = Sys04Snapshot.fromResponse(
        _envelope(
          'SYS-04',
          sections: [
            {
              'type': 'table',
              'rows': [
                {
                  '权限级别': 'READ',
                  '范围': 'subject:secret-token',
                  'state': 'ready',
                },
                {
                  '权限级别': 'ROOT_POLICY_INTERNAL',
                  '范围': 'secret',
                  'state': 'ready',
                },
              ],
            },
          ],
          truth: {
            'operation_types': ['write', 'secret-effect'],
            'audit_available': false,
          },
        ),
      );

      expect(snapshot.rows.map((row) => row.level), ['READ', 'UNKNOWN']);
      expect(snapshot.rows.map((row) => row.scope), ['UNKNOWN', 'UNKNOWN']);
      expect(snapshot.operationCount, 2);
    },
  );

  testWidgets(
    'SYS-04 renders a read-only security posture without policy leakage',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        _host(
          Sys04Screen(
            client: LumenisCoreClient(),
            repository: _Sys04Repo(_sys04Snapshot()),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('sys04/layout-desktop')),
        findsOneWidget,
      );
      expect(find.text('读取'), findsOneWidget);
      expect(find.text('secret-token'), findsNothing);
      expect(find.text('ROOT_POLICY_INTERNAL'), findsNothing);
      expect(find.text('当前没有可显示的审计决定。'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  test('SYS-05 local preference changes stay session-scoped', () async {
    final viewModel = Sys05ViewModel(repository: _Sys05Repo(_sys05Snapshot()));
    addTearDown(viewModel.dispose);
    await viewModel.refresh();

    viewModel.update(theme: 'light', locale: 'en');
    expect(viewModel.hasUnsavedChanges, isTrue);
    expect(viewModel.savedInSession, isFalse);
    viewModel.saveLocal();
    expect(viewModel.savedInSession, isTrue);
    expect(viewModel.preferences.theme, 'light');
    viewModel.restoreDefaults();
    expect(viewModel.preferences, const Sys05Preferences());
    expect(viewModel.savedInSession, isFalse);
  });

  testWidgets('SYS-05 exposes local-only settings on mobile', (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _host(
        Sys05Screen(
          client: LumenisCoreClient(),
          repository: _Sys05Repo(_sys05Snapshot()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('sys05/layout-mobile')), findsOneWidget);
    expect(find.textContaining('本地工作区'), findsOneWidget);
    expect(find.text('保存本地偏好'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test(
    'SYS-06 filters account, port, profile and session fields before the UI model',
    () {
      final snapshot = Sys06Snapshot.fromResponse(
        _envelope(
          'SYS-06',
          sections: [
            {
              'type': 'kpis',
              'items': [
                {'id': 'sys06.instances', 'value': 1, 'state': 'ready'},
                {'id': 'sys06.online', 'value': 0, 'state': 'ready'},
                {'id': 'sys06.capabilities', 'value': 2, 'state': 'ready'},
              ],
            },
            {
              'type': 'table',
              'rows': [
                {
                  'account': 'private-profile',
                  'port': 9222,
                  'profile': 'C:\\private',
                  'session': 'secret-session',
                  'state': 'offline',
                },
              ],
            },
          ],
        ),
      );

      expect(snapshot.instances, 1);
      expect(snapshot.onlineCount, 0);
      expect(snapshot.instanceStates.single.state, 'offline');
    },
  );

  testWidgets('SYS-06 never renders sensitive browser identity fields', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _host(
        Sys06Screen(
          client: LumenisCoreClient(),
          repository: _Sys06Repo(_sys06Snapshot()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('sys06/layout-desktop')), findsOneWidget);
    for (final forbidden in [
      'private-profile',
      '9222',
      'C:\\private',
      'secret-session',
    ]) {
      expect(find.textContaining(forbidden), findsNothing);
    }
    expect(find.text('身份材料已隐藏'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test(
    'SYS-07 leaves acceptance UNKNOWN when no evidence-backed gates exist',
    () {
      final snapshot = Sys07Snapshot.fromResponse(
        _envelope(
          'SYS-07',
          sections: [
            {
              'type': 'kpis',
              'items': [
                {'id': 'sys07.owasp_checks', 'value': 5, 'state': 'ready'},
                {'id': 'sys07.skills', 'value': 0, 'state': 'empty'},
              ],
            },
            {
              'type': 'table',
              'rows': [
                {'防护项': 'LLM01', '参考': 'IC-035'},
              ],
            },
          ],
          truth: {'ic_reference': 'IC-035'},
        ),
      );

      expect(snapshot.hasReturnedChecks, isTrue);
      expect(snapshot.hasCompleteGateEvidence, isFalse);
      expect(snapshot.checks.single.state, 'unknown');
      expect(snapshot.skillCount, isNull);
    },
  );

  test(
    'SYS-07 rejects bare, legacy, incomplete, and tampered gate Evidence',
    () {
      final cases = [
        {'state': 'pass', 'evidence': 'EV:bare-id'},
        {
          'state': 'pass',
          'evidence': {
            'version': 'v1',
            'type': 'canonical_evidence',
            'evidence_id': 'EV:v1',
          },
        },
        {
          'state': 'ready',
          'evidence': _validSys07Evidence(integrityStatus: null),
        },
        {'state': 'pass', 'evidence': _validSys07Evidence(tampered: true)},
      ];

      for (final item in cases) {
        final snapshot = Sys07Snapshot.fromResponse(
          _envelope(
            'SYS-07',
            sections: [
              {
                'type': 'gates',
                'rows': [
                  {'name': 'Gate', ...item},
                ],
              },
            ],
          ),
        );

        expect(snapshot.hasCompleteGateEvidence, isFalse);
        expect(snapshot.gates.single.evidenceValid, isFalse);
        expect(snapshot.gates.single.state, 'unknown');
      }
    },
  );

  test('SYS-07 accepts only a server-provided canonical Evidence v2 gate', () {
    final snapshot = Sys07Snapshot.fromResponse(
      _envelope(
        'SYS-07',
        sections: [
          {
            'type': 'gates',
            'rows': [
              {
                'name': 'Gate',
                'state': 'pass',
                'evidence': _validSys07Evidence(),
              },
            ],
          },
        ],
      ),
    );

    expect(snapshot.hasCompleteGateEvidence, isTrue);
    expect(snapshot.gates.single.evidenceValid, isTrue);
    expect(snapshot.gates.single.evidence, 'EV:sys07-001');
  });

  testWidgets('SYS-07 keeps missing production acceptance evidence visible', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _host(
        Sys07Screen(
          client: LumenisCoreClient(),
          repository: _Sys07Repo(_sys07Snapshot()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('sys07/layout-tablet')), findsOneWidget);
    expect(find.text('生产验收状态未由当前接口返回'), findsOneWidget);
    expect(find.text('当前接口没有返回带证据的生产验收 Gate。'), findsOneWidget);
    expect(find.text('未形成 PASS 结论'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('SYS-08 redacts path-like filenames and preserves missing metrics', () {
    final snapshot = Sys08Snapshot.fromResponse(
      _envelope(
        'SYS-08',
        sections: [
          {
            'type': 'kpis',
            'items': [
              {'id': 'sys08.files', 'value': 0, 'state': 'offline'},
              {'id': 'sys08.size_mb', 'value': null, 'state': 'offline'},
            ],
          },
          {
            'type': 'table',
            'rows': [
              {'文件': 'C:\\private\\lumenis.log', '大小MB': null, '修改': 'unknown'},
            ],
          },
        ],
      ),
    );

    expect(snapshot.totalFiles, isNull);
    expect(snapshot.totalSizeMb, isNull);
    expect(snapshot.files.single.name, '—');
    expect(snapshot.files.single.modified, 'unknown');
  });

  testWidgets(
    'SYS-08 shows the honest no-trace state instead of inventing a chart',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        _host(
          Sys08Screen(
            client: LumenisCoreClient(),
            repository: _Sys08Repo(_sys08Snapshot()),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const ValueKey('sys08/layout-mobile')), findsOneWidget);
      expect(find.text('当前接口没有返回 Trace waterfall 或关联记录。'), findsOneWidget);
      expect(find.text('当前没有可展示的结构化日志。'), findsWidgets);
      expect(tester.takeException(), isNull);
    },
  );
}

Widget _host(Widget child, {Locale locale = const Locale('zh', 'CN')}) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    locale: locale,
    supportedLocales: const [Locale('zh', 'CN'), Locale('en'), Locale('ko')],
    localizationsDelegates: const [
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(body: child),
  );
}

Map<String, dynamic> _envelope(
  String screen, {
  List<Map<String, dynamic>> sections = const [],
  Map<String, dynamic> truth = const {},
}) => {
  'ok': true,
  'screen': screen,
  'source': 'runtime',
  'bound': true,
  'truth': truth,
  'sections': sections,
};

Sys02Snapshot _sys02Snapshot() => Sys02Snapshot.fromResponse(
  _envelope(
    'SYS-02',
    sections: [
      {
        'type': 'kpis',
        'items': [
          {
            'id': 'sys02.active',
            'title': 'active',
            'value': 1,
            'state': 'ready',
          },
          {
            'id': 'sys02.partial',
            'title': 'partial',
            'value': 0,
            'state': 'ready',
          },
          {
            'id': 'sys02.missing',
            'title': 'missing',
            'value': 1,
            'state': 'ready',
          },
          {
            'id': 'sys02.blocked',
            'title': 'blocked',
            'value': 0,
            'state': 'ready',
          },
        ],
      },
      {
        'type': 'table',
        'rows': [
          {
            '平台': 'Source A',
            '状态': 'MISSING',
            '解析记录': null,
            '说明': 'not collected',
          },
        ],
      },
      {'type': 'note', 'text': 'read-only'},
    ],
  ),
);

Sys03Snapshot _sys03Snapshot() => Sys03Snapshot.fromResponse(
  _envelope(
    'SYS-03',
    sections: [
      {
        'type': 'kpis',
        'items': [
          {'id': 'sys03.schema_versions', 'value': null, 'state': 'offline'},
        ],
      },
      {
        'type': 'table',
        'rows': [
          {'检查项': 'foreign keys', '结果': 'UNKNOWN', 'state': 'unknown'},
        ],
      },
    ],
  ),
);

Sys04Snapshot _sys04Snapshot() => Sys04Snapshot.fromResponse(
  _envelope(
    'SYS-04',
    sections: [
      {
        'type': 'table',
        'rows': [
          {'权限级别': 'READ', '范围': 'CONTROLLED', 'state': 'ready'},
          {'权限级别': 'ROOT_POLICY_INTERNAL', '范围': 'secret', 'state': 'ready'},
        ],
      },
    ],
    truth: {
      'operation_types': ['read'],
      'audit_available': false,
    },
  ),
);

Sys05Snapshot _sys05Snapshot() => Sys05Snapshot.fromResponse(
  _envelope(
    'SYS-05',
    sections: [
      {
        'type': 'form',
        'fields': [
          {'label': 'Theme'},
          {'label': 'Locale'},
        ],
      },
    ],
    truth: {'data_source': 'localStorage', 'backend_required': false},
  ),
);

Sys06Snapshot _sys06Snapshot() => Sys06Snapshot.fromResponse(
  _envelope(
    'SYS-06',
    sections: [
      {
        'type': 'kpis',
        'items': [
          {'id': 'sys06.instances', 'value': 1, 'state': 'ready'},
          {'id': 'sys06.online', 'value': 0, 'state': 'ready'},
          {'id': 'sys06.capabilities', 'value': 2, 'state': 'ready'},
        ],
      },
      {
        'type': 'table',
        'rows': [
          {
            'account': 'private-profile',
            'port': 9222,
            'profile': 'C:\\private',
            'session': 'secret-session',
            'state': 'offline',
          },
        ],
      },
    ],
  ),
);

Sys07Snapshot _sys07Snapshot() => Sys07Snapshot.fromResponse(
  _envelope(
    'SYS-07',
    sections: [
      {
        'type': 'kpis',
        'items': [
          {'id': 'sys07.owasp_checks', 'value': 5, 'state': 'ready'},
          {'id': 'sys07.skills', 'value': null, 'state': 'empty'},
        ],
      },
      {
        'type': 'table',
        'rows': [
          {'防护项': 'LLM01', '参考': 'IC-035'},
        ],
      },
    ],
    truth: {'ic_reference': 'IC-035'},
  ),
);

Map<String, dynamic> _validSys07Evidence({
  String? integrityStatus = 'verified',
  bool tampered = false,
}) => {
  'version': 'v2',
  'type': 'canonical_evidence',
  'evidence_id': 'EV:sys07-001',
  'integrity': {
    'integrity_version': 2,
    'algorithm': 'sha256',
    'digest':
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
    'status': integrityStatus,
    'verified': integrityStatus != null,
    'tampered': tampered,
    'match': !tampered,
  },
  'lineage': {
    'verified': true,
    'lineage_id': 'LIN:sys07-001',
    'source_id': 'SRC:sys07-001',
    'canonical_id': 'CAN:sys07-001',
    'path': ['SRC:sys07-001', 'EV:sys07-001', 'CAN:sys07-001'],
  },
  'verification': {'state': 'verified', 'verified': true},
  'read_policy': {
    'allowed': true,
    'mode': 'read',
    'scope': 'system-evaluation-read',
  },
};

Sys08Snapshot _sys08Snapshot() => Sys08Snapshot.fromResponse(
  _envelope(
    'SYS-08',
    sections: [
      {
        'type': 'kpis',
        'items': [
          {'id': 'sys08.files', 'value': null, 'state': 'empty'},
          {'id': 'sys08.size_mb', 'value': null, 'state': 'empty'},
        ],
      },
      {'type': 'table', 'rows': const []},
    ],
  ),
);

class _Sys02Repo implements Sys02Repository {
  const _Sys02Repo(this.snapshot);
  final Sys02Snapshot snapshot;
  @override
  Future<Sys02Snapshot> load() async => snapshot;
}

class _Sys03Repo implements Sys03Repository {
  const _Sys03Repo(this.snapshot);
  final Sys03Snapshot snapshot;
  @override
  Future<Sys03Snapshot> load() async => snapshot;
}

class _Sys04Repo implements Sys04Repository {
  const _Sys04Repo(this.snapshot);
  final Sys04Snapshot snapshot;
  @override
  Future<Sys04Snapshot> load() async => snapshot;
}

class _Sys05Repo implements Sys05Repository {
  const _Sys05Repo(this.snapshot);
  final Sys05Snapshot snapshot;
  @override
  Future<Sys05Snapshot> load() async => snapshot;
}

class _Sys06Repo implements Sys06Repository {
  const _Sys06Repo(this.snapshot);
  final Sys06Snapshot snapshot;
  @override
  Future<Sys06Snapshot> load() async => snapshot;
}

class _Sys07Repo implements Sys07Repository {
  const _Sys07Repo(this.snapshot);
  final Sys07Snapshot snapshot;
  @override
  Future<Sys07Snapshot> load() async => snapshot;
}

class _Sys08Repo implements Sys08Repository {
  const _Sys08Repo(this.snapshot);
  final Sys08Snapshot snapshot;
  @override
  Future<Sys08Snapshot> load() async => snapshot;
}
