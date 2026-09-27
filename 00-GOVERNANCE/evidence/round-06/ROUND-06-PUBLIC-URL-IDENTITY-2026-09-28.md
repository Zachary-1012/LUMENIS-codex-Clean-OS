# ROUND 06 — preserve long public source URLs

Base: 2530d557236fa4b9f8b02ee749344c569fffe739.
The Norway country task found an official source URL blocked by a social search
keyword length guard. This existing Collector input validator now distinguishes
public source URLs (4096 chars) from social keywords (120 chars). URLs are never
truncated or rewritten, preserving Permission/resource/hash/provenance identity.
Network authorization, safe DNS, redirect validation and anonymous policy remain.

Seven focused input/exact-scope tests PASS on isolated v18 seed, exit 0. Current
source and new test AST parse PASS; staged bytes match tested candidate.
Real long-URL source ingestion still NOT VERIFIED; country task consumes this
fix in its existing source chain. No new owner/dependency or collector runtime.

真实用户工作闭环验收 / REAL DELIVERY CARD: manual operator provides an approved
public source URL; unchanged URL reaches the existing adapter and source policy.
Failure/recovery remains explicit when source/network/evidence refuses it. This
bounded input repair is TESTED, not user E2E/ROUND 06 acceptance.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: removes accidental URL exclusion, not a
coverage claim. COMMERCIAL OVERLAY IMPACT: none. CONTINUOUS FRONTIER RESEARCH /
CAPABILITY EVOLUTION: existing URL/request/source contracts reused; no new stack.
