import sqlite3
from dataclasses import replace
from unittest.mock import Mock
import pytest
from tests.test_agent_task_operational_admission import admission
from tests.test_skill_http_durable_identity import skill_client
from ai_browser_runtime import AIBrowserRuntime, BrowserActionType
from lumenis.system.security import permission

@pytest.fixture
def bound(admission):
 allowed,engine,path,context=admission
 with sqlite3.connect(path) as con:
  con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SYSTEM','browser','write')")
  sid=con.execute('SELECT id FROM v4_sessions WHERE user_id=1').fetchone()[0]
 permission.get_permission_gate().grant_permission(permission.PermissionLevel.VERIFY)
 r=AIBrowserRuntime(owner_actor_id=1,owner_account_session_id=sid)
 return r,allowed,engine,path

def test_real_task_and_run_binding_requires_separate_browser_permission(bound):
 r,a,engine,path=bound
 permission.get_permission_gate().revoke_permission(permission.PermissionLevel.VERIFY)
 with pytest.raises(PermissionError):r.bind_task_admission(a,actor={'id':1})
 assert r.task_binding_status=='UNBOUND'
 permission.get_permission_gate().grant_permission(permission.PermissionLevel.VERIFY)
 r.bind_task_admission(a,actor={'id':1})
 assert r.task_binding_status=='BOUND' and r._resolve_task_trace(None,None)==(a.task_id,a.run_id)

@pytest.mark.parametrize('mutation',['task_scope','actor','session','browser_permission','lease','cancel'])
def test_bound_action_rechecks_revocation_before_actual_page_access(bound,mutation):
 r,a,engine,path=bound;r.bind_task_admission(a,actor={'id':1});r._page=Mock()
 if mutation=='lease':a.queue.ack(a.queue_task_id,run_id=a.run_id,worker_id=a.worker_id,lease_owner=a.lease_owner)
 else:
  with sqlite3.connect(path) as con:
   if mutation=='task_scope':con.execute("DELETE FROM v4_member_authorizations WHERE module='agent_runtime'")
   elif mutation=='actor':con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
   elif mutation=='session':con.execute('DELETE FROM v4_sessions WHERE user_id=1')
   elif mutation=='browser_permission':con.execute("DELETE FROM v4_member_authorizations WHERE module='browser'")
   elif mutation=='cancel':con.execute("UPDATE ai_task SET status='cancelled' WHERE task_id=?",(a.task_id,))
 with pytest.raises(PermissionError):r._do_execute(BrowserActionType.CLICK,selector='#button')
 r._page.click.assert_not_called()
 with pytest.raises(PermissionError):r.observe()

@pytest.mark.parametrize('change',[{'_seal':None},{'actor_id':2},{'run_id':'forged'}])
def test_forged_or_stale_task_seal_not_browser_authority(bound,change):
 r,a,engine,path=bound
 with pytest.raises(PermissionError):r.bind_task_admission(replace(a,**change),actor={'id':1})
 assert r.task_binding_status=='UNBOUND'

def test_other_runtime_owner_cannot_adopt_task(bound):
 r,a,engine,path=bound;r.owner_actor_id=2
 with pytest.raises(PermissionError):r.bind_task_admission(a,actor={'id':2})

def test_cannot_rebind_during_action(bound):
 r,a,engine,path=bound;r._active_control_actions=1
 with pytest.raises(PermissionError):r.bind_task_admission(a,actor={'id':1})
 assert r.task_binding_status=='UNBOUND'

def test_bound_runtime_keeps_existing_human_control_gate(bound):
 from ai_browser_runtime import BrowserHumanControlError
 r,a,engine,path=bound;r.bind_task_admission(a,actor={'id':1});r._human_control_token_digest='active';r._human_control_expires_at=9999999999
 with pytest.raises(BrowserHumanControlError):r.execute_action(BrowserActionType.CLICK,selector='#button')

def test_bound_action_uses_separate_gate_at_effect_time(bound):
 r,a,engine,path=bound;r.bind_task_admission(a,actor={'id':1});r._page=Mock()
 r._do_execute(BrowserActionType.CLICK,selector='#button')
 r._page.click.assert_called_once()
 r._page.reset_mock()
 permission.get_permission_gate().revoke_permission(permission.PermissionLevel.VERIFY)
 with pytest.raises(PermissionError,match='BROWSER_OPERATION_PERMISSION_DENIED'):
  r._do_execute(BrowserActionType.CLICK,selector='#button')
 r._page.click.assert_not_called()

@pytest.mark.parametrize('mutation',['cancel','browser_grant','session','lease'])
def test_authority_change_during_final_gate_blocks_page(bound,monkeypatch,mutation):
 r,a,engine,path=bound
 r.bind_task_admission(a,actor={'id':1});r._page=Mock()
 gate=permission.get_permission_gate();original=gate.check
 def check(*args,**kwargs):
  result=original(*args,**kwargs)
  if args and args[0]==permission.OperationType.BROWSER_OPERATION:
   if mutation=='lease':a.queue.ack(a.queue_task_id,run_id=a.run_id,worker_id=a.worker_id,lease_owner=a.lease_owner)
   else:
    with sqlite3.connect(path) as con:
     if mutation=='cancel':con.execute("UPDATE ai_task SET status='cancelled' WHERE task_id=?",(a.task_id,))
     elif mutation=='browser_grant':con.execute("DELETE FROM v4_member_authorizations WHERE module='browser'")
     elif mutation=='session':con.execute("DELETE FROM v4_sessions WHERE user_id=1")
  return result
 monkeypatch.setattr(gate,'check',check)
 with pytest.raises(PermissionError):r._do_execute(BrowserActionType.CLICK,selector='#external-submit')
 r._page.click.assert_not_called()

def test_revoked_during_observation_does_not_return_body(bound):
 r,a,engine,path=bound;r.bind_task_admission(a,actor={'id':1});r._page=Mock();r._page.url='https://example.invalid/task';r._page.title.return_value='Private task'
 def evaluate(script,*args):
  if 'innerText' in script:
   with sqlite3.connect(path) as con:con.execute('DELETE FROM v4_sessions WHERE user_id=1')
   return {'text':'sensitive task report','truncated':False,'ready_state':'complete'}
  return 1
 r._page.evaluate.side_effect=evaluate
 with pytest.raises(PermissionError):r.observe()

def test_queue_fence_is_released_before_external_effect(bound):
 import threading
 r,a,engine,path=bound;r.bind_task_admission(a,actor={'id':1});r._page=Mock()
 started=threading.Event();finished=threading.Event();threads=[]
 def retire():
  started.set()
  a.queue.ack(a.queue_task_id,run_id=a.run_id,worker_id=a.worker_id,lease_owner=a.lease_owner)
  finished.set()
 def effect(*args,**kwargs):
  t=threading.Thread(target=retire);threads.append(t);t.start()
  assert started.wait(2)
  assert finished.wait(2)
 r._page.click.side_effect=effect
 try:r._do_execute(BrowserActionType.CLICK,selector='#button')
 finally:
  for t in threads:t.join(2)
 assert finished.is_set()
 with pytest.raises(PermissionError):r._do_execute(BrowserActionType.CLICK,selector='#button')

@pytest.mark.parametrize('payload_change',[{'cancel_requested':True},{'deadline_at':1.0}])
def test_queue_cancel_or_deadline_denies_new_browser_action(bound,payload_change):
 import json
 r,a,engine,path=bound;r.bind_task_admission(a,actor={'id':1});r._page=Mock()
 row=a.queue.get(a.queue_task_id);payload=dict(row['payload']);payload.update(payload_change)
 with a.queue._conn:a.queue._conn.execute('UPDATE tasks SET payload=? WHERE id=?',(json.dumps(payload),a.queue_task_id))
 with pytest.raises(PermissionError):r._do_execute(BrowserActionType.CLICK,selector='#control')
 r._page.click.assert_not_called()
