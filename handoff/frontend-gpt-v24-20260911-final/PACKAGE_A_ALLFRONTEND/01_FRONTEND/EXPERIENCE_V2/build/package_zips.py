# -*- coding: utf-8 -*-
"""Package experience_v2 into a FULL zip + thematic part zips (deterministic, repo-external output)."""
import os,zipfile,datetime
EV=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(os.path.dirname(os.path.dirname(EV)),"_experience_delivery")  # D:\LUMENIS_REBUILD\_experience_delivery
os.makedirs(OUT,exist_ok=True)
STAMP="20260911"; PREFIX=f"LUMENIS_ExperienceV2_{STAMP}"
SKIP_DIRS={"_rec","__pycache__"}; SKIP_EXT={".pyc"}
VOLUMES={
 "P1_design_system_docs":["00_readme","01_repo_audit","02_authority","03_ia_and_flows","04_design_system",
                          "05_components","06_motion","13_research","15_provenance_licenses","16_versioning"],
 "P2_screens_contracts":["07_screens","11_integration_skeleton","12_contracts","12_i18n"],
 "P3_runnable_prototype_build":["10_prototype","build"],
 "P4_visual_regression_media":["14_visual_regression","19_previews","08_psd","09_responsive"],
 "P5_codex_handoff_validation":["codex_handoff","19_handoff","17_acceptance","18_validation"],
}
def files_under(top):
    out=[]
    for root,dirs,files in os.walk(top):
        dirs[:]=[d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if os.path.splitext(fn)[1] in SKIP_EXT:continue
            out.append(os.path.join(root,fn))
    return out
def make_zip(name, folders):
    paths=[]
    for f in folders:
        p=os.path.join(EV,f)
        if os.path.isdir(p):paths+=files_under(p)
        elif os.path.isfile(p):paths.append(p)
    zp=os.path.join(OUT,name)
    with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(set(paths)):
            z.write(p, os.path.join("experience_v2",os.path.relpath(p,EV)).replace("\\","/"))
    return zp,len(set(paths)),os.path.getsize(zp)
allfolds=sorted([d for d in os.listdir(EV) if os.path.isdir(os.path.join(EV,d))])
report=[]
for v,fs in VOLUMES.items():
    r=make_zip(f"{PREFIX}_{v}.zip",fs); report.append(r); print(v,r[1],"files",round(r[2]/1e6,2),"MB")
r=make_zip(f"{PREFIX}_FULL.zip",allfolds); report.append(r); print("FULL",r[1],"files",round(r[2]/1e6,2),"MB")
idx=os.path.join(OUT,"DELIVERY_INDEX.txt")
with open(idx,"w",encoding="utf-8") as f:
    f.write("LUMENIS / 序境 Experience V2 — delivery "+datetime.datetime.now().isoformat(timespec="seconds")+"\n")
    f.write("Frozen local HEAD ab67612367c172ced2dff62b44e98de86469d1e6 ; remote main b910117 (docs only)\n")
    f.write("Open 10_prototype/index.html ; Codex reads experience_v2/19_handoff/INTEGRATION_START_HERE.md\n\n")
    for nm,n,sz in report: f.write(f"{nm}\t{n} files\t{round(sz/1e6,2)} MB\n")
print("OUT",OUT)
