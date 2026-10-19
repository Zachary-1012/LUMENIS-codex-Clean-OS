import hashlib
import uuid
from tests.test_saved_document_workflow import workspace
from tests.test_growth_learning_exchange import journey, transition
from tests.test_internal_pitch_workflow import manuscript_arguments
from api_dual_domain import BusinessDecisionWorkflow
from lumenis.shared.learning import contribution as learning
from lumenis.shared.content_creation import internal_pitch as pitch
from lumenis.system.security import permission


def test_real_original_action_unknown_outcome_review_learning_local_receive_reopen(journey):
    j=journey
    from ai_task_engine import init_task_engine_db
    init_task_engine_db();pitch.engine.cache_clear()
    actor_ref,scope=j['common']['actor_id'],j['common']['expected_scope']
    auth=lambda operation:{**j['authorize'](),'operation':operation}
    service=BusinessDecisionWorkflow(internal_action_reader=pitch.read_internal_pitch,action_actor=j['actor'],source_actor=j['actor'])
    options=[{'option_id':label,'proposal':'Inspect bounded internal wording '+label,'rationale':'Source statements are not measured effects.','source_ids':[j['source']['source_id']],'assumptions':['No outcome established.'],'unknowns':['Audience impact.'],'check':'Review saved original document.'} for label in ('A','B')]
    work=service.prepare(actor_ref=actor_ref,scope=scope,submission_id='independent-full-prepare',source_job_id=j['report']['job_id'],kind='venue_operations',question='Which bounded wording should be reviewed?',options=options,authorize=auth)
    def step(operation,payload):
        nonlocal work
        work=service.advance(work['work_id'],actor_ref=actor_ref,scope=scope,authorize=auth,expected_revision=work['revision'],submission_id='independent-'+uuid.uuid4().hex,operation=operation,payload=payload)
    step('choose',{'option_id':'A','reason':'Inspect internal draft only.','owner':'Synthetic operator','review_at':'2026-10-20T12:00:00+00:00'})
    args=manuscript_arguments(j,request='independent-real-pitch')
    args.pop('input_manifest');args.update(profile='source-bound/v3',upstream_ref={'kind':'source_brief_job','job_id':j['report']['job_id'],'expected_artifact_hash':j['report']['artifact_outcome']['artifact_hash']})
    pending=pitch.prepare_internal_pitch(**args)
    actual=pitch.run_internal_pitch(pending['task_id'],actor=j['actor'],scope=j['scope'])
    assert actual['state']=='succeeded'
    downloaded=pitch.download_internal_pitch(pending['task_id'],actor=j['actor'],scope=j['scope'])
    assert hashlib.sha256(downloaded['content']).hexdigest()==actual['action_receipt']['output']['sha256']
    step('action',{'option_id':'A','task_id':pending['task_id']})
    step('outcome_unknown',{'limits':'Actual internal Word artifact exists; no external campaign or growth effect observed.'})
    step('review',{'assessment':'inconclusive','observations':'Saved internal output is reviewable; business effect unknown.','limitations':['Synthetic engineering source only.'],'next_step':'retain','source_ids':[j['source']['source_id']]})
    assert work['action_state']=='EXECUTED' and work['business_outcome']=='UNKNOWN'
    candidate=learning.create_business_candidate(work_id=work['work_id'],expected_business_revision=work['revision'],job_id=j['report']['job_id'],submission_id=str(uuid.uuid4()),authorize=j['authorize'],**j['common'])
    validated=transition(j,transition(j,candidate,'review'),'validate')
    out=learning.enqueue_candidate(validated['id'],expected_revision=validated['revision'],receiver=learning.LOCAL_REPO,submission_id=str(uuid.uuid4()),authorize=j['authorize'],**j['common'])
    staged=transition(j,out,'stage')
    j['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,resource=learning.approval_resource(out['id'],'receive_local',staged['revision']),granted_by=actor_ref)
    ack=learning.receive_local_contribution(out['id'],expected_revision=staged['revision'],submission_id=str(uuid.uuid4()),authorize=j['authorize'],**j['common'])
    assert ack['transport']=='ACKNOWLEDGED' and ack['remote_delivery_proven'] is False
    assert learning.get_outbox(out['id'],**j['common'])==ack
    assert learning.get_candidate(candidate['id'],**j['common'])['admission']=='VALIDATED'
    assert not ack['training_eligible'] and not ack['production_truth_write']
    reopened=service.reopen(work['work_id'],actor_ref=actor_ref,scope=scope,authorize=auth)
    assert reopened==work and reopened['action_read']['state']=='FRESH_OWNER_VERIFIED'
    pitch.engine.cache_clear()
