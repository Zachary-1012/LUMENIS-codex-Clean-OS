// LUMENIS experience handoff validator. Deterministic; prints JSON + writes validate_result.json / raw log.
// Usage: node validate_handoff.mjs [experience_v2_root]
import fs from 'node:fs';import path from 'node:path';
const ROOT=process.argv[2]||path.resolve(process.cwd(),'..');
const R={ok:true,root:ROOT,checks:[],json_parse:{ok:0,fail:[]},counts:{},missing:[],notes:[]};
function ck(name,cond,detail){R.checks.push({name,pass:!!cond,detail:detail||''});if(!cond)R.ok=false;}
function exists(rel){return fs.existsSync(path.join(ROOT,rel));}
// 1) required tree (red-line 00..10 mapping inside experience_v2)
const req=['01_DOCUMENTS/MASTER_PLAN.docx','01_DOCUMENTS/ADDENDUM_FINAL.docx','01_DOCUMENTS/FINAL_PLAN.pdf','01_DOCUMENTS/MASTER_MATRIX.xlsx',
 '02_REPO_AUDIT/EXECUTION_ANCHOR.json','06_CONTRACTS/unknown-bindings.json','07_I18N/copy-registry.json','08_FIXTURES/REPLACEMENT_LIST.json',
 '10_prototype/index.html','04_design_system/v2.5/DESIGN_ECOSYSTEM_V2.5.md','05_components/brand/svg/lumenis-mark.svg',
 '05_components/icons/lum-icons-sprite.svg','06_motion/source/MOTION_SOURCES_V2.5.json','10_ORIGINALITY/ORIGINALITY_ATTESTATION.md',
 '12_contracts/presentation-mapping/PRESENTATION_CONTRACT_MAPPING_V2.5.md'];
for(const r of req){if(!exists(r))R.missing.push(r);}
ck('required_paths',R.missing.length===0,'missing='+R.missing.length);
// 2) parse every JSON
function walk(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){const fp=path.join(d,e.name);
 if(e.isDirectory()){if(/node_modules/.test(fp))continue;walk(fp);}else if(e.name.endsWith('.json')){try{JSON.parse(fs.readFileSync(fp,'utf8'));R.json_parse.ok++;}catch(err){R.json_parse.fail.push({file:path.relative(ROOT,fp),error:err.message});}}}}
walk(ROOT);ck('all_json_parse',R.json_parse.fail.length===0,'parsed='+R.json_parse.ok+' fail='+R.json_parse.fail.length);if(R.json_parse.fail.length)R.ok=false;
// 3) counts
const countPng=d=>exists(d)?fs.readdirSync(path.join(ROOT,d)).filter(f=>f.endsWith('.png')).length:0;
R.counts.screens=(()=>{const w={};new Function('window',fs.readFileSync(path.join(ROOT,'10_prototype/data/screens.js'),'utf8'))(w);return Object.keys(w.LUM_SCREENS).length;})();
const im=JSON.parse(fs.readFileSync(path.join(ROOT,'05_components/icons/icons-manifest.json'),'utf8'));R.counts.icons=im.count;
for(const w of [1920,1440,1280,1024,768,430,390,360]){R.counts['baseline_'+w+'_light']=countPng('04_VISUAL_BASELINES/'+w+'/light');R.counts['baseline_'+w+'_dark']=countPng('04_VISUAL_BASELINES/'+w+'/dark');}
ck('screens_44',R.counts.screens===44,'got '+R.counts.screens);
ck('icons_69',R.counts.icons===69,'got '+R.counts.icons);
const baseFail=Object.entries(R.counts).filter(([k,v])=>k.startsWith('baseline_')&&v!==44);
ck('baselines_8x2x44',baseFail.length===0,'incomplete='+JSON.stringify(baseFail));if(baseFail.length)R.notes.push('baseline matrix incomplete (may still be capturing): '+baseFail.map(x=>x[0]+'='+x[1]).join(','));
// 4) legacy css import guard
const idx=fs.readFileSync(path.join(ROOT,'10_prototype/index.html'),'utf8');
const links=[...idx.matchAll(/href="\.\/assets\/([^"]+\.css)"/g)].map(m=>m[1]);
const allowed=['fonts.css','tokens.css','base.css','components.css','shell.css','optical.css','brand.css','motion.css'];
ck('legacy_css_import_zero',links.every(l=>allowed.includes(l))&&links.length===8,'links='+links.join(','));
// 5) external runtime scan result
if(exists('10_ORIGINALITY/EXTERNAL_RUNTIME_SCAN.json')){const e=JSON.parse(fs.readFileSync(path.join(ROOT,'10_ORIGINALITY/EXTERNAL_RUNTIME_SCAN.json'),'utf8'));ck('zero_external_runtime',e.runtime_external_requests===0,'req='+e.runtime_external_requests);}
fs.mkdirSync(path.join(ROOT,'09_QA/validate_handoff'),{recursive:true});
fs.writeFileSync(path.join(ROOT,'09_QA/validate_handoff/validate_result.json'),JSON.stringify(R,null,1));
console.log(JSON.stringify({ok:R.ok,checks:R.checks,counts:R.counts,missing:R.missing,json_fail:R.json_parse.fail.length,notes:R.notes},null,1));
process.exit(R.ok?0:2);
