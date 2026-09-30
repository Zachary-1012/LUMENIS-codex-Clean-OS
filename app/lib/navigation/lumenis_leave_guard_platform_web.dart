import 'dart:js_interop';

import 'package:web/web.dart' as web;

class BrowserLeaveProtection {
  bool _attached = false;
  final JSFunction _listener = ((web.BeforeUnloadEvent event) {
    event.preventDefault();
    event.returnValue = '';
  }).toJS;

  void setProtected(bool value) {
    if (value == _attached) return;
    _attached = value;
    if (value) {
      web.window.addEventListener('beforeunload', _listener);
    } else {
      web.window.removeEventListener('beforeunload', _listener);
    }
  }

  void dispose() => setProtected(false);
}
