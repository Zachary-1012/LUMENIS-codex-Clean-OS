# LUMENIS App

Canonical user-facing application for 序境 / LUMENIS.

Targets: Windows, macOS, Linux, Android, iOS.

The app consumes LUMENIS Product Core and must not create a second Evidence, Canonical Data, Permission, Runtime or API truth.

Current bootstrap contracts:
- GET /api/experience/runtime/identity
- GET /api/experience/subjects
- GET /api/experience/screen/<screen_id>

Default Core URL: http://127.0.0.1:8201
Override per authorized device/build with:
--dart-define=LUMENIS_CORE_URL=<authorized-core-url>

Do not copy historical web UI into this app.
