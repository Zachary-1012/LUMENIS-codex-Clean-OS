import 'read_aloud_contract.dart';
import 'read_aloud_backend_stub.dart'
    if (dart.library.io) 'read_aloud_backend_io.dart'
    if (dart.library.js_interop) 'read_aloud_backend_web.dart'
    as implementation;

ReadAloudPlatform createReadAloudPlatform() =>
    implementation.createReadAloudPlatform();
