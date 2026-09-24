import 'dart:js_interop';

import 'package:flutter_web_plugins/url_strategy.dart';

@JS('document.documentElement.lang')
external set _documentLanguage(JSString value);

void configureLumenisUrlStrategy() {
  usePathUrlStrategy();
}

void setLumenisDocumentLanguage(String languageTag) {
  _documentLanguage = languageTag.toJS;
}
