"""Offline replay plan guardrails; no runtime grants or network access."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('profile_replay',Path(__file__).resolve().parents[1]/'scripts/import_entity_profile_package.py')
replay=importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def inputs(tmp_path):
    baseline=tmp_path/'baseline.jsonl';bundle=tmp_path/'bundle.jsonl'
    baseline.write_text(json.dumps({'seed_key':'S1','domain_id':'CTH','subject_type':'company','name_en':'Synthetic','name_zh':'合成'})+'\n')
    bundle.write_text(json.dumps({'baseline_id':'S1','baseline_name_en':'Synthetic','baseline_name_zh':'合成','domain_id':'CTH',
        'manifest_template':{'entity':None,'review':{},'assertions':[]}})+'\n')
    return baseline,bundle


def test_default_dry_run_has_no_http(tmp_path,monkeypatch):
    baseline,bundle=inputs(tmp_path)
    monkeypatch.setattr(replay,'Client',lambda _:pytest.fail('offline dry-run called HTTP'))
    output=tmp_path/'dry.json'
    assert replay.main(['--baseline',str(baseline),'--bundles',str(bundle),'--output',str(output)])==0
    result=json.loads(output.read_text())
    assert result['mode']=='DRY_RUN_NO_HTTP_NO_WRITES' and result['registered_ids'] is None


def test_changed_identity_is_not_name_guessed(tmp_path):
    baseline,bundle=inputs(tmp_path)
    row=json.loads(bundle.read_text());row['baseline_name_en']='Different';bundle.write_text(json.dumps(row))
    with pytest.raises(ValueError,match='mismatched'):replay.package(baseline,[bundle])


@pytest.mark.parametrize('url',['https://example.com','http://127.0.0.1.evil.test','http://user:secret@localhost','http://localhost/private','http://localhost?token=secret'])
def test_replay_rejects_nonlocal_or_credential_urls(url):
    with pytest.raises(ValueError):replay.Client(url)


def test_registration_apply_never_accepts_unreviewed_preview(tmp_path,monkeypatch):
    baseline,bundle=inputs(tmp_path);calls=[]
    class FakeClient:
        def __init__(self,_):pass
        def call(self,*args):
            calls.append(args)
            return {'ok':True,'resource':'exact-review-resource'}
    monkeypatch.setattr(replay,'Client',FakeClient)
    with pytest.raises(ValueError,match='Review registration-prepare'):
        replay.main(['--mode','registration-apply','--baseline',str(baseline),'--bundles',str(bundle),'--output',str(tmp_path/'out.json')])
    assert len(calls)==1 and calls[0][2]=={'entries':replay.package(baseline,[bundle])['entries']}
