import pytest
from subject_classifier import SubjectClassifier, enrich_note_types

@pytest.mark.parametrize('flag',[False,None,'false','true','1',0,2])
def test_self_declared_official_does_not_become_official(flag):
 r=SubjectClassifier().classify(author_name='合成品牌官方店',author_desc='品牌官方服务',is_verified=flag,verified_type='企业')
 assert r['subject_type']=='unknown'
 assert r['suggested_subject_type']=='official'
 assert r['identity_truth']=='NOT_ESTABLISHED'
 assert r['needs_manual_review'] is True
 assert r['content_type_hint']!='official'

@pytest.mark.parametrize('flag',[True,1])
def test_platform_verified_input_does_not_prove_target_brand_ownership(flag):
 r=SubjectClassifier().classify(author_name='合成品牌官方',is_verified=flag,verified_type='其他企业')
 assert r['subject_type']=='unknown'
 assert r['platform_verification_observed'] is True
 assert r['identity_truth']=='NOT_ESTABLISHED'

def test_ingestion_wrapper_does_not_turn_false_string_into_verified():
 assert enrich_note_types(author_name='合成品牌官方',is_verified='false')[0]=='unknown'

def test_unverified_claim_does_not_imply_impersonation_or_sanction():
 r=SubjectClassifier().classify(author_name='合成品牌官方 禁言中')
 assert r['subject_type']=='unknown'
 assert not any(k in r for k in ('fraud','impersonation_confirmed','platform_sanction_verified'))

def test_original_confirmed_ownership_owner_keeps_precedence(monkeypatch):
 import kos_engine
 monkeypatch.setattr(kos_engine,'_load_overrides',lambda:{'synthetic-brand::account-a':{'ownership_class':'OFFICIAL','confirmed_by':'synthetic-reviewer','confirmed_at':'2026-10-18'}})
 r=kos_engine.ownership_for({'author_id':'account-a','subject_type':'unknown'},brand='synthetic-brand')
 assert r['ownership_class']=='OFFICIAL' and r['ai_status']=='VERIFIED'
 assert r['needs_manual_review'] is False

@pytest.mark.parametrize('name',['合成品牌官方服务中心','合成品牌购物中心','合成品牌官方协会'])
def test_institution_conflict_does_not_imply_official_content(name):
 r=SubjectClassifier().classify(author_name=name,is_verified=True)
 assert r['content_type_hint']!='official'
 assert r['identity_truth']=='NOT_ESTABLISHED'
 assert r['needs_manual_review'] is True
