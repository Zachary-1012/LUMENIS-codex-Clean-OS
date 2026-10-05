abstract final class LumenisWorkspaceRoutes {
  static const root = '/workspace/CTH-01';
  static const rootScreenId = 'CTH-01';
  static const cth01 = '/workspace/CTH-01';

  /// Kept for links issued before the complete workspace navigation shipped.
  static const cth02 = '/workspace/CTH-01/CTH-02';
  static const bmp01 = '/workspace/BMP-01';
  static const ai01 = '/workspace/AI-01';
  static const sh01 = '/workspace/SH-01';
  static const sys01 = '/workspace/SYS-01';

  /// Task navigation; legacy screen IDs remain compatible API/deep-link inputs.
  /// These groups organize work without changing data or domain ownership.
  static const workflowsByGroup = <String, Map<String, List<String>>>{
    'CTH': {
      'workflow.observe': ['CTH-01', 'CTH-03', 'CTH-07'],
      'workflow.resolve': ['CTH-04', 'CTH-06', 'CTH-08', 'CTH-09'],
      'workflow.plan': ['CTH-05', 'CTH-10'],
      'workflow.context': ['CTH-02'],
    },
    'BMP': {
      'workflow.research': [
        'BMP-01',
        'BMP-02',
        'BMP-03',
        'BMP-04',
        'BMP-05',
        'BMP-11',
      ],
      'workflow.create': ['BMP-06', 'BMP-08', 'BMP-07'],
      'workflow.review': ['BMP-09', 'BMP-10'],
    },
    'AI': {
      'workflow.assist': ['AI-01', 'AI-02', 'AI-03'],
      'workflow.assist_tools': ['AI-04', 'AI-05'],
    },
    'SH': {
      'workflow.resources': ['SH-01', 'SH-02', 'SH-03'],
      'workflow.deliverables': ['SH-04', 'SH-05', 'SH-06'],
    },
    'SYS': {
      'workflow.operations': ['SYS-01', 'SYS-02', 'SYS-06', 'SYS-08'],
      'workflow.settings': ['SYS-05', 'SYS-03', 'SYS-04', 'SYS-07'],
    },
    'ACC': {
      'workflow.account': ['ACC-01', 'ACC-02', 'ACC-03', 'ACC-04'],
    },
  };

  static String workflowForScreen(String screenId) =>
      workflowsByGroup[groupForScreen(screenId)]!.entries
          .firstWhere((entry) => entry.value.contains(screenId))
          .key;

  static const screenIdsByGroup = <String, List<String>>{
    'ACC': ['ACC-01', 'ACC-02', 'ACC-03', 'ACC-04'],
    'AI': ['AI-01', 'AI-02', 'AI-03', 'AI-04', 'AI-05'],
    'CTH': [
      'CTH-01',
      'CTH-02',
      'CTH-03',
      'CTH-04',
      'CTH-05',
      'CTH-06',
      'CTH-07',
      'CTH-08',
      'CTH-09',
      'CTH-10',
    ],
    'BMP': [
      'BMP-01',
      'BMP-02',
      'BMP-03',
      'BMP-04',
      'BMP-05',
      'BMP-06',
      'BMP-07',
      'BMP-08',
      'BMP-09',
      'BMP-10',
      'BMP-11',
    ],
    'SH': ['SH-01', 'SH-02', 'SH-03', 'SH-04', 'SH-05', 'SH-06'],
    'SYS': [
      'SYS-01',
      'SYS-02',
      'SYS-03',
      'SYS-04',
      'SYS-05',
      'SYS-06',
      'SYS-07',
      'SYS-08',
    ],
  };

  static final Set<String> screenIds = Set.unmodifiable(
    screenIdsByGroup.values.expand((screenIds) => screenIds),
  );

  /// Every canonical screen currently has a workspace implementation.  A
  /// particular capability can still return a truthful unavailable state at
  /// runtime, but navigation must not replace a real product surface with a
  /// permanent route boundary.
  static const unavailableScreenIds = <String>{};

  /// A controlled reader is opened above the originating task so browser Back
  /// can return to its exact task context.  This is a navigation behavior, not
  /// an availability boundary.
  static const focusedReturnScreenIds = <String>{'SYS-06'};

  static final Set<String> workspaceScreenIds = Set.unmodifiable(
    screenIds.difference(unavailableScreenIds),
  );

  static String pathForScreen(String screenId) {
    if (!screenIds.contains(screenId)) {
      throw ArgumentError.value(screenId, 'screenId', 'Unknown Screen ID');
    }
    return screenId == 'CTH-02' ? cth02 : '/workspace/$screenId';
  }

  static bool supportsScreen(String screenId) => screenIds.contains(screenId);

  static bool supportsWorkspaceScreen(String screenId) =>
      workspaceScreenIds.contains(screenId);

  static String groupForScreen(String screenId) {
    if (!screenIds.contains(screenId)) {
      throw ArgumentError.value(screenId, 'screenId', 'Unknown Screen ID');
    }
    return screenId.split('-').first;
  }
}
