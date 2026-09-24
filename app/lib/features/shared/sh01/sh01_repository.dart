import '../../../core/lumenis_core_client.dart';
import 'sh01_snapshot.dart';

typedef Sh01CatalogReader = Future<Map<String, dynamic>> Function();

abstract interface class Sh01Repository {
  Future<Sh01Catalog> loadCatalog();
}

/// Reads only the existing safe catalog route. The SH-01 global Evidence list
/// and detail routes are deliberately outside this repository boundary.
class CoreSh01Repository implements Sh01Repository {
  const CoreSh01Repository({
    required this._client,
    this.catalogReader,
  });

  final LumenisCoreClient _client;
  final Sh01CatalogReader? catalogReader;

  @override
  Future<Sh01Catalog> loadCatalog() async {
    final reader = catalogReader ?? _client.sharedSkillsCatalog;
    return Sh01Catalog.fromResponse(await reader());
  }
}
