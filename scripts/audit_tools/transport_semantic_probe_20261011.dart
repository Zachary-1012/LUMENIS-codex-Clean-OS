import 'dart:async';
import 'dart:convert';
import 'dart:io';
import '../../source/app/lib/core/transport/lumenis_http_transport_io.dart' as native;
import '../../source/app/lib/core/transport/lumenis_http_transport_web.dart' as webFunction;
import '../../source/app/lib/core/transport/lumenis_http_transport_types.dart';

// Copied to parser/bin by audit workflow. Executes only frozen transport functions,
// with a disposable loopback server. No product Core, credentials or DB is started.
Future<Map<String, Object?>> probe(String name, bool binary, bool web) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  var completed = false;
  final served = Completer<void>();
  final sub = server.listen((req) async {
    try {
      req.response.statusCode = 200;
      req.response.headers.contentType = ContentType.json;
      req.response.write('{');
      await req.response.flush();
      await Future<void>.delayed(const Duration(milliseconds: 400));
      req.response.write('"ok":true}');
      await req.response.close();
    } catch (_) {
      // A properly timed-out client may close the disposable connection.
    } finally {
      if (!served.isCompleted) served.complete();
    }
  });
  final request = LumenisTransportRequest(method: 'GET',
    uri: Uri.parse('http://127.0.0.1:${server.port}/synthetic-only'),
    headers: const {}, connectionTimeout: const Duration(milliseconds: 80),
    followRedirects: false);
  final clock = Stopwatch()..start();
  String? errorType;
  try {
    if (binary) {
      if (web) {
        await webFunction.sendLumenisBinaryRequest(request, maxBytes: 1024);
      } else {
        await native.sendLumenisBinaryRequest(request, maxBytes: 1024);
      }
    } else {
      if (web) {
        await webFunction.sendLumenisHttpRequest(request);
      } else {
        await native.sendLumenisHttpRequest(request);
      }
    }
    completed = true;
  } catch (error) {
    errorType = error.runtimeType.toString();
  } finally {
    clock.stop();
    await served.future.timeout(const Duration(seconds: 2), onTimeout: () {});
    await sub.cancel();
    await server.close(force: true);
  }
  return {'name': name, 'configured_timeout_ms': 80,
    'server_body_delay_ms': 400, 'elapsed_ms': clock.elapsedMilliseconds,
    'completed': completed, 'error_type': errorType,
    'runtime_boundary': web ? 'WEB_FUNCTION_ON_VM_HTTP_CLIENT_NOT_BROWSER_E2E' : 'ACTUAL_IO_TRANSPORT_LOOPBACK'};
}
Future<void> main(List<String> args) async {
  final results = <Map<String, Object?>>[];
  for (final web in [false, true]) {
    results.add(await probe(web ? 'web_function_text_body' : 'native_text_body', false, web));
    results.add(await probe(web ? 'web_function_binary_body' : 'native_binary_body', true, web));
  }
  final output = {'baseline': '01588e9fd9568e3fcaf1e6c3d957bc498436fa48',
    'observed_at': DateTime.now().toUtc().toIso8601String(), 'results': results,
    'external_network': false, 'production_database': false, 'product_core_started': false};
  File(args.single).writeAsStringSync(jsonEncode(output));
  print(jsonEncode(output));
}
