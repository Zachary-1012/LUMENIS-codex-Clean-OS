#!/usr/bin/env python3
"""Validate LUMENIS Experience V3 as the sole current design authority."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CANONICAL="00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md"
REGISTRY="00-GOVERNANCE/LUMENIS-EXPERIENCE-AUTHORITY-CURRENT.json"
ROUTERS=("AGENTS.md","experience_v2/AGENTS.md","00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md")
LEGACY_PHRASE="44 screens may ONLY compose registered patterns/components (no bespoke layout)"
FORBIDDEN_BOOTSTRAP=(
 "LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md",
 "LUMENIS-EXPERIENCE-DESIGN-LANGUAGE-V2.4-20260911.md",
 "LUMENIS_NEW_PRODUCT_DESIGN_BASELINE_V1.md",
 "AUTHORITY_ALIGNMENT.md",
 "DESIGN_ECOSYSTEM_V2.5.md",
)

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def main() -> int:
    errors=[]
    cp,rp=ROOT/CANONICAL,ROOT/REGISTRY
    if not cp.exists(): errors.append("missing canonical Constitution")
    if not rp.exists(): errors.append("missing machine authority registry")
    if errors:
        print(json.dumps({"ok":False,"errors":errors},indent=2)); return 2
    cfg=json.loads(rp.read_text(encoding="utf-8"))
    if cfg.get("version")!="3.0.0": errors.append("authority version must be 3.0.0")
    if cfg.get("status")!="CANONICAL_SINGLE_CURRENT_AUTHORITY": errors.append("V3 is not sole current authority")
    if cfg.get("scope")!="WHOLE_PRODUCT_EXPERIENCE": errors.append("V3 scope is not whole-product")
    if cfg.get("cleanup_policy")!="FROZEN_DURING_V3_ROUND__SEPARATE_NEXT_ROUND_TASK":
        errors.append("cleanup policy does not match V3-first phase")
    raw=cp.read_bytes()
    if blob_sha(raw)!=(cfg.get("constitution") or {}).get("git_blob_sha"): errors.append("Constitution fingerprint drift")
    if (cfg.get("constitution") or {}).get("path")!=CANONICAL: errors.append("canonical path mismatch")
    text=raw.decode("utf-8",errors="replace")
    for needle in (
      "Status: **CANONICAL / SOLE EXPERIENCE DESIGN AUTHORITY**",
      "Internal version: **3.0**",
      "## 0. Full-product scope",
      "## 8. Realm dialects",
      "## 10. AI / Agent experience",
      "## 12. Evidence presentation",
      "## 14. Data visualization",
      "## 15. Reports / exports",
      "## 20. Responsive recomposition",
      "## 21. Accessibility",
      "## 22. Trilingual copy",
      "## 24. Anti-template hard failures",
      "## 25. Golden Pages",
      "## 27. Authority exclusivity and cleanup freeze",
      "## 28. Acceptance",
    ):
        if needle not in text: errors.append("Constitution missing: "+needle)
    needed={"CTH","BMP","SHARED_CAPABILITY","SYSTEM","AI_AGENT","EVIDENCE","REPORT","EXPORT","RESPONSIVE_WEB","ZH_EN_KO","FUTURE_APP","FUTURE_MINI_PROGRAM"}
    missing=sorted(needed-set(cfg.get("coverage") or []))
    if missing: errors.append("coverage missing: "+", ".join(missing))
    for rel in ROUTERS:
        p=ROOT/rel
        if not p.exists(): errors.append("missing router: "+rel); continue
        body=p.read_text(encoding="utf-8",errors="replace")
        if CANONICAL not in body: errors.append("router missing Constitution: "+rel)
        if REGISTRY not in body: errors.append("router missing registry: "+rel)
    local=(ROOT/"experience_v2/AGENTS.md").read_text(encoding="utf-8",errors="replace")
    for old in FORBIDDEN_BOOTSTRAP:
        if old in local: errors.append("bootstrap references superseded authority: "+old)
    if (ROOT/"00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION-V3-20260918.md").exists():
        errors.append("duplicate V3 Constitution path exists")
    sec=ROOT/"experience_v2/10_prototype/assets/sections.js"
    if sec.exists() and LEGACY_PHRASE in sec.read_text(encoding="utf-8",errors="replace"):
        errors.append("legacy fixed-composer authority remains")
    out={"ok":not errors,"authority":CANONICAL,"version":cfg.get("version"),"scope":cfg.get("scope"),"cleanup_policy":cfg.get("cleanup_policy"),"errors":errors}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if not errors else 2

if __name__=="__main__": sys.exit(main())
