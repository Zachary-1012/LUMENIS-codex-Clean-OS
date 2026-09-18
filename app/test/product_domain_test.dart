import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/product/product_domain.dart';

void main() {
  test('canonical product domains remain stable', () {
    expect(ProductDomain.values.length, 4);
    expect(ProductDomain.cth.technicalId, 'CTH');
    expect(ProductDomain.cth.principle, 'Subject-first');
    expect(ProductDomain.bmp.technicalId, 'BMP');
    expect(ProductDomain.bmp.principle, 'Brand-first / Primary Focus');
    expect(
      CrossProductLayer.agentGroups.principle,
      'Cross-Product Execution & Collaboration',
    );
  });
}
