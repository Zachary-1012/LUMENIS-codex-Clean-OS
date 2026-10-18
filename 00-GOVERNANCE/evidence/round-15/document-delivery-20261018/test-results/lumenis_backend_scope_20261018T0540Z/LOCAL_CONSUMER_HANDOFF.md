# BMP read-contract consumption and frontend integration

## Current authority and version

Frontend construction, Dart/model/parser integration and frontend tests require separate implementation and acceptance. This candidate contains only backend source plus backend tests. It does not adopt or recommend automatic merging of the paused Dart/UI changes. Those partial changes remain separately preserved in the development workspace; they are not in this source snapshot.

Baseline: complete 2248 source, manifest 6eadb7d8217016205966c418bf52b42473009b45cc5b3daf74ad53814dc05b41. Backend candidate manifest: 5dec07f048bfa3c4569838e82413f4f48c8dcdb7e918572cc8d648d756b20789. No GitHub or local computer modified.

## Actual server contract

The existing BMP overview admission returns the same scope/read contract, with the following additive field only for the original local-workspace-read-v1 branch:

read_transport = {contract: lumenis.local-read-transport.v1, module: brand_market_overview, action: read, verified: true}

This field is built from the original module-specific local_workspace_read_allowed result. It is not copied from request headers. The original wrapper rechecks the full binding after reading, and only equal current admission allows release. Permission implementation and its Host/Origin/loopback/Forwarded/Authorization/session-cookie guards are byte-identical to the baseline.

Local overview keeps actor_scope=anonymous_read, actor_id absent/null, and global_all_granted=false even for GLOBAL_ALL. No principal_kind/principal_ref or account role is invented by this projection. Authenticated account bindings never receive read_transport. Context metadata is not a new permission grant.

BMP03 consumes source_read_binding and source_context (mode key). BMP04/BMP10 consume observation_read_binding and observation_context (canonical_scope key). BMP09 consumes report_screen_binding in addition to the independent report_authorization from reports/read. Report context has either a positive integer actor_id or exactly the original sealed local principal_kind=local_workspace/principal_ref=workspace:local fields. These identity shapes must not be mixed. Overview transport alone never establishes report read authorization.

## Local implementation and acceptance still required

- Centralize strict count parsing in the existing Flutter core; only int>=0, not double 1.0, string, bool, null or negative values. Preserve unknown/null separately from genuine zero. BMP04 source_count currently has the known numeric-equality hole.
- Validate exact BMP/ZBMP context, complete required keys, GLOBAL null identifiers, and valid distinct FOCUS subject/brand IDs. Do not normalize malformed scopes into valid authorization or accept another module's binding.
- Account and local identity/transport branches must be mutually exclusive; reject malformed descriptor shape, wrong module/action/contract, actor strings/doubles, extra/mixed identity metadata, and missing current read flags.
- BMP09 independently requires the existing reports/read context and exact report scope. Bind account identity to the overview binding when present; local overview transport is not interchangeable with reports principal or Evidence.
- Retain SavedWork and SourceBrief as separate resource types, artifact/version hashes, actual evaluation state and rejected/partial/pagination semantics. Storage is not an effectiveness result; recorded evaluations are not automatically PASS.
- Strictly validate date representation and calendar components before accepting DateTime parsing; impossible days, invalid time/offset and whitespace are not factual dates. BMP09 DateTime.tryParse normalization remains a known baseline defect. BMP10 has stricter existing checks that should be reused rather than weakened.
- Run original Dart regressions plus actual same-version HTTP payloads from results/loopback-warm.json, loopback-cold.json and sourcebrief-prepare/cold.json. Cover all four local/account successes, fresh-process reopening, revocation/recovery, wrong module/scope/domain, mixed identities, forged labels, count types and impossible dates. Backend test payloads are synthetic engineering inputs, not production/user acceptance.
- Finish real UI binding and four-surface acceptance separately. Existing BMP03/04 private named _client constructor mismatch was observed by the paused UI owner; it is not repaired here.

## Boundaries retained

Original 19 pending items, 195 G requirements, R01–R15/J1–J8/U01–U25, all approved surfaces and research obligations remain open at their original scope. This transport projection does not complete four-screen parsing, UI, the full product, live acquisition, model/training, deployment or release.
