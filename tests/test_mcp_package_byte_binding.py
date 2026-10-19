import json
from pathlib import Path
import pytest
from tests.test_mcp_skill_runtime import _package

def info(runtime,package):
 return {'skill_id':'trendhub-mcp','version':'1.5.2','active_version':'1.5.2','install_path':str(package),'entrypoint':json.dumps(runtime.build_entrypoint(str(package)))}

def test_package_byte_change_invalidates_approved_contract(tmp_path,monkeypatch):
 runtime,p=_package(tmp_path,monkeypatch);meta=info(runtime,p)
 before=runtime.runtime_contract_binding(meta)
 (p/'dist/src/index.js').write_text('// harmless changed bytes')
 assert runtime.runtime_contract_binding(meta)!=before

@pytest.mark.parametrize('target',['dist/src/index.js','node_modules/dep.js','manifest.json'])
def test_every_runtime_file_is_bound(tmp_path,monkeypatch,target):
 runtime,p=_package(tmp_path,monkeypatch);meta=info(runtime,p)
 f=p/target
 if not f.exists():f.write_text('original')
 before=runtime.runtime_contract_binding(meta);f.write_text(f.read_text()+' ')
 assert runtime.runtime_contract_binding(meta)!=before

def test_add_remove_file_changes_binding(tmp_path,monkeypatch):
 runtime,p=_package(tmp_path,monkeypatch);meta=info(runtime,p)
 before=runtime.runtime_contract_binding(meta);extra=p/'node_modules/added.js';extra.write_text('')
 assert runtime.runtime_contract_binding(meta)!=before
 extra.unlink();assert runtime.runtime_contract_binding(meta)==before

@pytest.mark.parametrize('name',['.env','.env.local','credentials.json','cookies.txt'])
def test_secret_named_file_refused_without_read(tmp_path,monkeypatch,name):
 runtime,p=_package(tmp_path,monkeypatch);f=p/name;f.write_text('synthetic-do-not-read')
 original=__import__('os').open
 def checked(path,*args,**kwargs):
  assert Path(path)!=f
  return original(path,*args,**kwargs)
 monkeypatch.setattr(__import__('os'),'open',checked)
 with pytest.raises(ValueError,match='SNAPSHOT'):runtime.runtime_contract_binding(info(runtime,p))

def test_symlink_cannot_escape_package(tmp_path,monkeypatch):
 runtime,p=_package(tmp_path,monkeypatch);outside=tmp_path/'outside';outside.write_text('synthetic')
 (p/'node_modules/link').symlink_to(outside)
 with pytest.raises(ValueError,match='SNAPSHOT'):runtime.runtime_contract_binding(info(runtime,p))

def test_missing_root_refused(tmp_path,monkeypatch):
 runtime,p=_package(tmp_path,monkeypatch);meta=info(runtime,p);meta['install_path']=str(p/'missing')
 with pytest.raises(ValueError,match='SNAPSHOT'):runtime.runtime_contract_binding(meta)

def test_large_sparse_file_is_rejected_before_read(tmp_path,monkeypatch):
 runtime,p=_package(tmp_path,monkeypatch)
 with (p/'oversize.bin').open('wb') as f:f.truncate(1024*1024*1024+1)
 with pytest.raises(ValueError,match='SNAPSHOT'):runtime.runtime_contract_binding(info(runtime,p))

def test_normal_cookie_library_name_is_not_secret_file(tmp_path,monkeypatch):
 runtime,p=_package(tmp_path,monkeypatch);(p/'node_modules/cookie.js').write_text('// ordinary source')
 assert runtime.runtime_contract_binding(info(runtime,p))

from tests.test_mcp_contract_review import prepare_fixture, registry, canonical_gate, _row, _workspace_app, _workspace_admission
from lumenis.shared.agents.skills import lifecycle as lc

def test_mutation_during_snapshot_refused(tmp_path,monkeypatch):
 runtime,p=_package(tmp_path,monkeypatch); original=__import__('os').open; mutated=[]
 def changing(path,*args,**kwargs):
  if not mutated:
   mutated.append(True);(p/'new-during-scan.txt').write_text('synthetic')
  return original(path,*args,**kwargs)
 monkeypatch.setattr(__import__('os'),'open',changing)
 with pytest.raises(ValueError,match='SNAPSHOT'):runtime.runtime_contract_binding(info(runtime,p))

def test_package_mutation_after_review_blocks_signed_apply(registry,canonical_gate,tmp_path,monkeypatch):
 candidate=prepare_fixture(registry,tmp_path,monkeypatch);before=_row(registry[0])
 (registry[1]/'added-after-review.txt').write_text('synthetic')
 with _workspace_app().test_request_context('/',environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
  args,_,_=_workspace_admission(candidate,canonical_gate)
  with pytest.raises((PermissionError,ValueError,RuntimeError)):lc.apply_skill_metadata_change(candidate,**args)
 assert _row(registry[0])==before

def test_package_mutation_during_discovery_blocks_candidate(registry,tmp_path,monkeypatch):
 import mcp_skill_runtime as runtime
 original=runtime.discover_registered_mcp
 def changing(meta):
  result=original(meta);(registry[1]/'added-during-discovery.txt').write_text('synthetic');return result
 monkeypatch.setattr(runtime,'discover_registered_mcp',changing)
 with pytest.raises(ValueError,match='CHANGED_DURING_DISCOVERY'):prepare_fixture(registry,tmp_path,monkeypatch)

def test_changed_package_never_starts_call_process(tmp_path,monkeypatch):
 runtime,p=_package(tmp_path,monkeypatch);meta=info(runtime,p)
 meta.update(tools_json='["read_signal"]',permissions_granted_json='["mcp:tools/call", "read_only"]')
 meta['compatibility_json']={'mcp_tool_contracts':{'read_signal':'synthetic-contract'},'mcp_runtime_binding':runtime.runtime_contract_binding(meta)}
 (p/'dist/src/index.js').write_text('// changed')
 called=[];monkeypatch.setattr(runtime,'call_mcp_stdio',lambda *a,**k:called.append(True) or {'ok':True})
 result=runtime.invoke_registered_mcp(meta,{'tool_name':'read_signal','arguments':{},'human_approved':True})
 assert result['ok'] is False and result['state']=='CONTRACT_CHANGED'
 assert not called

@pytest.mark.parametrize('change',['same_length_restore_mtime','remove','symlink','replace_inode'])
def test_final_sweep_rechecks_previously_hashed_file(tmp_path,monkeypatch,change):
 import os
 runtime,p=_package(tmp_path,monkeypatch);early=p/'aaa.js';late=p/'zzz.js'
 early.write_text('aaaa');late.write_text('later');before=early.stat()
 outside=tmp_path/'outside';outside.write_text('synthetic')
 original=os.open;changed=[]
 def changing(path,*args,**kwargs):
  if Path(path)==late and not changed:
   changed.append(True)
   if change=='same_length_restore_mtime':
    early.write_text('bbbb');os.utime(early,ns=(before.st_atime_ns,before.st_mtime_ns))
   elif change=='remove':early.unlink()
   elif change=='symlink':early.unlink();early.symlink_to(outside)
   else:
    replacement=p/'replacement';replacement.write_text('aaaa');replacement.replace(early)
  return original(path,*args,**kwargs)
 monkeypatch.setattr(os,'open',changing)
 with pytest.raises(ValueError,match='SNAPSHOT'):runtime.runtime_contract_binding(info(runtime,p))
 assert changed
