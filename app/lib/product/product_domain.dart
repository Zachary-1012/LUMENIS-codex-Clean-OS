enum ProductDomain { cth, bmp, shared, system }

extension ProductDomainDefinition on ProductDomain {
  String get technicalId => switch (this) {
    ProductDomain.cth => 'CTH',
    ProductDomain.bmp => 'BMP',
    ProductDomain.shared => 'SHARED',
    ProductDomain.system => 'SYSTEM',
  };

  String get zhName => switch (this) {
    ProductDomain.cth => '寰意·商业运营',
    ProductDomain.bmp => '寰意·品牌市场',
    ProductDomain.shared => '共享能力',
    ProductDomain.system => '系统',
  };

  String get principle => switch (this) {
    ProductDomain.cth => 'Subject-first',
    ProductDomain.bmp => 'Brand-first / Primary Focus',
    ProductDomain.shared => 'Cross-domain capability',
    ProductDomain.system => 'Production infrastructure',
  };
}

enum CrossProductLayer { agentGroups }

extension CrossProductLayerDefinition on CrossProductLayer {
  String get principle => 'Cross-Product Execution & Collaboration';
}
