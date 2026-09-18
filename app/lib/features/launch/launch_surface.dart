import 'package:flutter/widgets.dart';

import '../../core/lumenis_core_client.dart';
import '../../product/product_domain.dart';

class LaunchSurface extends StatefulWidget {
  const LaunchSurface({required this.client, super.key});

  final LumenisCoreClient client;

  @override
  State<LaunchSurface> createState() => _LaunchSurfaceState();
}

class _LaunchSurfaceState extends State<LaunchSurface> {
  late Future<_LaunchState> _future = _load();

  Future<_LaunchState> _load() async {
    final runtime = await widget.client.runtimeIdentity();
    final subjects = await widget.client.subjects();
    return _LaunchState(runtime: runtime, subjects: subjects);
  }

  void _retry() {
    setState(() {
      _future = _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: const Color(0xFF0D0E10),
      child: SafeArea(
        child: FutureBuilder<_LaunchState>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const _Status(
                title: '序境',
                detail: '正在连接 LUMENIS Production Core…',
              );
            }
            if (snapshot.hasError) {
              return _Failure(error: snapshot.error.toString(), onRetry: _retry);
            }
            return _Ready(state: snapshot.requireData);
          },
        ),
      ),
    );
  }
}

class _Ready extends StatelessWidget {
  const _Ready({required this.state});

  final _LaunchState state;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final inset = constraints.maxWidth >= 900 ? 72.0 : 24.0;
        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(inset, 40, inset, 48),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1080),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '序境',
                  style: TextStyle(
                    color: Color(0xFFF6F6F4),
                    fontSize: 34,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.8,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  _runtimeLabel(state.runtime),
                  style: const TextStyle(color: Color(0xFF9EA3AA)),
                ),
                const SizedBox(height: 44),
                const Text(
                  '当前工作主体',
                  style: TextStyle(
                    color: Color(0xFFF2F3F4),
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  '选择主体只改变工作上下文，不改写 Evidence、Canonical Data、历史事件或确认结果的原始归属。',
                  style: TextStyle(color: Color(0xFFAEB3BA)),
                ),
                const SizedBox(height: 20),
                if (state.subjects.isEmpty)
                  const Text(
                    '当前没有可用 Subject。保持 EMPTY / NOT_COLLECTED，不伪造默认主体。',
                    style: TextStyle(color: Color(0xFFB7BBC1)),
                  )
                else
                  ...state.subjects.map(_SubjectLine.new),
                const SizedBox(height: 46),
                const Text(
                  '产品领域',
                  style: TextStyle(
                    color: Color(0xFFF2F3F4),
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 14),
                ...ProductDomain.values.map(_DomainLine.new),
                const SizedBox(height: 24),
                const Text(
                  'Agent Groups · Cross-Product Execution & Collaboration',
                  style: TextStyle(color: Color(0xFF8F949B)),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  static String _runtimeLabel(Map<String, dynamic> runtime) {
    final app = runtime['app'] ?? 'LUMENIS';
    final api = runtime['api'] ?? 'runtime';
    return '$app · $api';
  }
}

class _SubjectLine extends StatelessWidget {
  const _SubjectLine(this.subject);

  final Map<String, dynamic> subject;

  @override
  Widget build(BuildContext context) {
    final name = subject['name'] ??
        subject['display_name'] ??
        subject['subject_name'] ??
        subject['id'] ??
        'Unnamed Subject';
    final id = subject['id'] ?? subject['subject_id'];

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('→ ', style: TextStyle(color: Color(0xFF747B84))),
          Expanded(
            child: Text(
              id == null || '$id'.isEmpty ? '$name' : '$name · $id',
              style: const TextStyle(
                color: Color(0xFFE3E5E7),
                fontSize: 16,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DomainLine extends StatelessWidget {
  const _DomainLine(this.domain);

  final ProductDomain domain;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Text(
        domain.technicalId +
            ' · ' +
            domain.zhName +
            ' · ' +
            domain.principle,
        style: const TextStyle(color: Color(0xFFC8CCD1)),
      ),
    );
  }
}

class _Failure extends StatelessWidget {
  const _Failure({required this.error, required this.onRetry});

  final String error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 680),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'LUMENIS Core 未连接',
                style: TextStyle(
                  color: Color(0xFFF2F3F4),
                  fontSize: 24,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              Text(error, style: const TextStyle(color: Color(0xFFB4B8BE))),
              const SizedBox(height: 22),
              GestureDetector(
                onTap: onRetry,
                child: const Text(
                  '重新连接',
                  style: TextStyle(
                    color: Color(0xFFF2F3F4),
                    decoration: TextDecoration.underline,
                    decorationColor: Color(0xFFF2F3F4),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Status extends StatelessWidget {
  const _Status({required this.title, required this.detail});

  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              title,
              style: const TextStyle(
                color: Color(0xFFF4F4F2),
                fontSize: 30,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 10),
            Text(detail, style: const TextStyle(color: Color(0xFFA9AEB5))),
          ],
        ),
      ),
    );
  }
}

class _LaunchState {
  const _LaunchState({required this.runtime, required this.subjects});

  final Map<String, dynamic> runtime;
  final List<Map<String, dynamic>> subjects;
}
