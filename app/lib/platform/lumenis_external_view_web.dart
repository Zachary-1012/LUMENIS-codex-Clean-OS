import 'dart:js_interop';

@JS('window.open')
external JSAny? _windowOpen(JSString url, JSString target, JSString features);

/// Optional user-chosen "view original" jump in a new browser tab.
/// It only displays a public http(s) page; collection never runs here.
Future<bool> openLumenisExternalView(Uri url) async {
  if (url.scheme != 'https' && url.scheme != 'http') return false;
  _windowOpen(url.toString().toJS, '_blank'.toJS, 'noopener,noreferrer'.toJS);
  return true;
}
