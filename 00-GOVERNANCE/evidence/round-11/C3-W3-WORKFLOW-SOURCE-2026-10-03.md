# C3 / W3 — bounded workflow source integration

M decision: SOURCE_ACCEPTED. Full C3 NOT_ACCEPTED. W6 integration base:
`09b3bbb461e6f338251a4b1b3c6a45e4a2664fdb`; Cloud fixed source:
`d92cbb7dca4a4da3dfda501a5e1c1bac841348c7`.

The publication dependency closure contains the existing four-layer workflow,
its Case source binding, and the final-read repair. It is not a two-line patch
against bare main. Exact LF source bytes are recorded in
[source-evidence.json](c3-workflow-source-20261003/source-evidence.json).

| Path | LF SHA256 |
|---|---|
| api_dual_domain.py | 97ddddcd86032907bf2ceb34a7294440de61dbc4340c23aa434731a8e40dc12f |
| cth_cases.py | d19651824377ce4e56a646a61b8f37043a1a304a30fd7c911d1622048d39c000 |
| tests/test_cth_case_routes.py | 2375dc81e5ebe353f98556a5cddc9271d8effd31ac117dd0cc29d4aebd226b5c |
| tests/test_business_decision_workflow.py | 57b4c95572ea6bf95f685d94b62158b25f97426b2b5785b306d64dcf100c955d |

The received delta is4594B/SHA
`4214231a7d45a19afefa1b024a53b7d3778d9c49dd03c6f589b7e08d9b091f85`.
Its preimages are the already-composed four-layer API/test LF hashes c9030f44…
and8a5ff093…, not bare d92/main. All16 input artifact sizes/hashes were read back.
The new API change is confined to BusinessDecisionWorkflow.reopen: after
rendering, the existing authorizer rechecks the same actor, exact scope and read
operation before returning. Revocation or mismatched authorization returns no
rendered payload. Unbound owned analysis reports UNAVAILABLE/
OWNED_RUNTIME_NOT_BOUND. This boundary does not establish atomic authorization
across all possible concurrent changes or complete per-source use authorization.

The preserved Case source dependency re-verifies its original SourceBrief
report/hash and selected source references. It is included unchanged from its
protected layer postimage, rather than left as an unpublished test dependency.
Existing published callable signatures and behavior were inspected. Protected
Permission changes add only the collector module and a docstring; this workflow
calls published module reports. The unrelated Permission/test paths are excluded.
The independent nine-file statistical slice is frozen, excluded and not retested.

W6 current-main isolation:8 affected cases,0 failure/error/skip; Constitution,
Takeover, single-product, database authority and diff checks all exit0. Tests
used an explicit empty seed and disposable DB. No production provider/browser
or database was invoked. The8 selected cases exercise normal CTH/BMP reopen,
render-time revocation, final actor/scope mismatch and honest analysis state.
These synthetic inputs are engineering evidence, not real-user acceptance.
Existing layer evidence is retained at its source pins; old106/8/7 were not
repeated. The initial Windows autocrlf representation error and wrong gate-name
tooling error are retained locally; their actual causes were corrected without
weakening any legitimate test/gate. Logs and counts remain independently readable.

Plain-text copies of the fixed-base gate receipts are linked for direct review:
[affected reopen](c3-workflow-source-20261003/affected-reopen.txt),
[AI-native constitution](c3-workflow-source-20261003/verify_ai_native_constitution.txt),
[takeover governance](c3-workflow-source-20261003/verify_codex_takeover_governance.txt),
[database authority](c3-workflow-source-20261003/verify_database_authority.txt),
and [single-product guard](c3-workflow-source-20261003/verify_lumenis_single_product.txt).
Each is byte-identical to its SHA-bound original output embedded in
`source-evidence.json`; these are engineering receipts, not full C3 acceptance.
The identical ignored `.log` copies remain local because the safety layer
rejected their deletion; they are not a second evidence source.

W6 review receipt39905c65b7d5907250ebe05b70da4d65db68fecf8dbd7f32aeda6bd0bef2e586;
local root integration9463a59fe482a1e38182acf488aa8fb42591e614013ee3c72a208b7464a42e25.
The integration preserved all93 preexisting protected file hashes and an empty
root index. The current M-owned icon constitution and all other unpublished
candidates remain outside this source unit.

Real user job remains a commercial Subject operating decision or BrandFocus
market/content decision using real admitted source inputs. Entry/API/UI and
normal Permission/use binding still need real verification. The parent three-job/
16-case inventory is retained; quality-v2 adds the full Guangzhou task and has
four tasks with the same16 cases. Both are NOT_RUN/NOT_GRANTED, not trained or
positive gold. Useful owned analysis, authoritative executed Action, measured/unknown
Outcome, independently committed Artifact/version/parent/hash/receipt, Evaluation,
reopen/recovery and Clear→GLOBAL remain required through existing owners.
An internal draft, source quotation or unavailable state cannot close that chain.

Global commercial, brand and Guangzhou reference coverage are not established
by this patch; GLOBAL remains product default and focus changes no Permission.
No random-entity business acceptance was performed by these synthetic tests.
The original95570B material archive remains NOT_RECEIVED; no14-source re-collection.
No full C3/C6, USER_VERIFIED, RELEASED, OPERATING or commercial-readiness claim.
