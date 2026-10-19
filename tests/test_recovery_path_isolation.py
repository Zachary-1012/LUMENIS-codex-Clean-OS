import ast
from pathlib import Path
import pytest

def functions(legacy_dir):
 import lumenis.adapters.auth_recovery as module
 # Read exact installed Owner source; compile only pure path helpers to avoid browser initialization.
 tree=ast.parse(Path(module.__file__).read_text())
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'_shot_path','_full_shot','_qr_shot'}]
 ns={'Path':Path,'SHOT_DIR':legacy_dir}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(module.__file__),'exec'),ns)
 return ns

@pytest.fixture
def isolated(tmp_path,monkeypatch):
 from lumenis.shared.database import registry
 monkeypatch.setenv('ZBC_DATA_DIR',str(tmp_path/'configured'));monkeypatch.setattr(registry,'_registry',None)
 legacy=tmp_path/"legacy";legacy.mkdir()
 return registry,functions(legacy)

def test_configured_directory(isolated,tmp_path):
 _,f=isolated
 assert f['_full_shot']('douyin')==tmp_path/'configured/recovery/login_douyin.png'
 assert f['_qr_shot']('xhs')==tmp_path/'configured/recovery/qr_xhs.png'

def test_registry_reload_after_import(isolated,tmp_path,monkeypatch):
 registry,f=isolated;f['_full_shot']('douyin')
 monkeypatch.setenv('ZBC_DATA_DIR',str(tmp_path/'second'));registry.get_registry(force_reload=True)
 assert f['_full_shot']('douyin')==tmp_path/'second/recovery/login_douyin.png'

def test_default_compatibility(isolated,tmp_path,monkeypatch):
 registry,f=isolated;monkeypatch.delenv('ZBC_DATA_DIR');monkeypatch.setenv('ZBC_REPO_ROOT',str(tmp_path));registry.get_registry(force_reload=True)
 assert f['_qr_shot']('weibo')==tmp_path/'data/recovery/qr_weibo.png'

@pytest.mark.parametrize('platform',['../../escape','a/b','a\\b','',None])
def test_traversal_refused(isolated,platform):
 _,f=isolated
 with pytest.raises(ValueError):f['_full_shot'](platform)

def test_directory_symlink_refused(isolated,tmp_path):
 _,f=isolated;target=tmp_path/'outside';target.mkdir();root=tmp_path/'configured';root.mkdir();(root/'recovery').symlink_to(target,target_is_directory=True)
 with pytest.raises(ValueError):f['_qr_shot']('xhs')
 assert list(target.iterdir())==[]

def test_file_symlink_refused(isolated,tmp_path):
 _,f=isolated;p=f['_full_shot']('xhs');outside=tmp_path/'outside';outside.write_text('synthetic');p.symlink_to(outside)
 with pytest.raises(ValueError):f['_full_shot']('xhs')
 assert outside.read_text()=='synthetic'
