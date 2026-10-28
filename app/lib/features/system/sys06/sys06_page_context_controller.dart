import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';

enum Sys06PageContextFailure {
  pageRequired,
  pageChanged,
  humanVerificationRequired,
  unavailable,
}

/// Keeps page-read state and response identity checks outside the retired
/// dialog/widget renderer. The supplied reader remains the existing browser
/// owner and is responsible for permission and current-page binding.
class Sys06PageContextController extends ChangeNotifier {
  Sys06PageContextController({required this._readPage, this._pageIdentity});

  final Future<Map<String, dynamic>> Function(String question) _readPage;
  bool _disposed = false;
  bool _busy = false;
  int _generation = 0;
  String? _pageIdentity;
  String _question = '';
  Map<String, dynamic>? _result;
  Sys06PageContextFailure? _failure;

  bool get busy => _busy;
  String get question => _question;
  String? get pageIdentity => _pageIdentity;
  Map<String, dynamic>? get result =>
      _result == null ? null : Map<String, dynamic>.from(_result!);
  Sys06PageContextFailure? get failure => _failure;

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void updateQuestion(String value) {
    _question = value;
    _notify();
  }

  /// A new page invalidates the previous excerpt and any in-flight response,
  /// while leaving the user's question available for a deliberate reread.
  void bindPageIdentity(String? identity) {
    if (identity == _pageIdentity) return;
    _pageIdentity = identity;
    _generation++;
    _result = null;
    _failure = null;
    _busy = false;
    _notify();
  }

  Future<bool> read() async {
    final question = _question.trim();
    if (_busy || question.isEmpty) return false;
    final generation = ++_generation;
    _busy = true;
    _failure = null;
    _result = null;
    _notify();
    try {
      final result = await _readPage(question);
      if (_disposed || generation != _generation) return false;
      final page = result['page_context'];
      final metadata = result['metadata'];
      final formats = result['formats'];
      final body = formats is Map ? formats['text'] : null;
      if (result['ok'] != true ||
          page is! Map ||
          page['question'] != question ||
          page['excerpt'] is! String ||
          page['answer_state'] != 'NOT_GENERATED' ||
          page['content_kind'] != 'SOURCE_EXCERPT' ||
          metadata is! Map ||
          metadata['url'] is! String ||
          metadata['title'] is! String ||
          DateTime.tryParse('${metadata['captured_at']}') == null ||
          body is! Map ||
          body['success'] != true ||
          body['data'] is! String) {
        throw const FormatException('Page context is unavailable.');
      }
      _result = Map<String, dynamic>.from(result);
      _notify();
      return true;
    } catch (error) {
      if (_disposed || generation != _generation) return false;
      final code = error is LumenisCoreException ? error.errorCode : null;
      _failure = switch (code) {
        'BROWSER_CONTEXT_PAGE_REQUIRED' => Sys06PageContextFailure.pageRequired,
        'BROWSER_EXTRACTION_PAGE_CHANGED' =>
          Sys06PageContextFailure.pageChanged,
        'BROWSER_EXTRACTION_HUMAN_REQUIRED' =>
          Sys06PageContextFailure.humanVerificationRequired,
        _ => Sys06PageContextFailure.unavailable,
      };
      _notify();
      return false;
    } finally {
      if (!_disposed && generation == _generation) {
        _busy = false;
        _notify();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
