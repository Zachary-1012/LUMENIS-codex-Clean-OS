# Cross-module verification

Repository integrity tests live here for the specification baseline. Product
implementation adds affected unit/integration and cross-module user-work checks;
module-specific tests stay with their code. Fixtures are not user acceptance.

All persistence tests use an explicit isolated data root. Never use user databases,
platform accounts, personal browser state or paid services as implicit test fixtures.
