from unittest.mock import Mock
import pytest
from ai_browser_runtime import AIBrowserRuntime, BrowserActionType as A, BrowserPageState, ExpectedState, ActionVerifier, FailureRecovery

def runtime(after):
 r=object.__new__(AIBrowserRuntime);r._active_human_link_navigation_guard=None;r._page=None;r.recovery=FailureRecovery();r.verifier=ActionVerifier();r._do_execute=Mock(side_effect=TimeoutError('timed out after effect'));r.observe=Mock(return_value=after);r._try_recovery_strategy=Mock(return_value=True)
 return r

def run(r, action, expected):
 return r._execute_with_recovery(action_type=action,target='',selector='#send',text='',value='',url='',before_state=BrowserPageState(),expected=expected)

def test_landed_effect_is_read_back_without_second_click():
 r=runtime(BrowserPageState(body_text='receipt 123'));out=run(r,A.CLICK,ExpectedState(text_present='receipt 123'))
 assert out.success and r._do_execute.call_count==1 and not r._try_recovery_strategy.called
 assert out.recovery_attempts[0].strategy=='observe_before_retry'
@pytest.mark.parametrize('action',[A.CLICK,A.INPUT,A.SELECT,A.KEYBOARD,A.UPLOAD,A.DOWNLOAD,A.NAVIGATE,A.TAB_NEW,A.TAB_CLOSE])
def test_uncertain_effect_never_blindly_replayed(action):
 r=runtime(BrowserPageState(body_text='no receipt'));out=run(r,action,ExpectedState(text_present='receipt 123'))
 assert not out.success and out.human_escalation_required and not r._try_recovery_strategy.called
 assert r._do_execute.call_count==1
@pytest.mark.parametrize('expected',[None,ExpectedState()])
def test_readiness_alone_cannot_claim_landed_effect(expected):
 r=runtime(BrowserPageState());out=run(r,A.CLICK,expected)
 assert not out.success and not r._try_recovery_strategy.called

def test_permission_failure_never_recovered_as_success():
 r=runtime(BrowserPageState(body_text='receipt 123'));r._do_execute.side_effect=PermissionError('permission denied');out=run(r,A.CLICK,ExpectedState(text_present='receipt 123'))
 assert not out.success and not r.observe.called and not r._try_recovery_strategy.called

def test_already_true_condition_does_not_prove_new_effect():
 r=runtime(BrowserPageState(body_text='receipt 123'))
 out=r._execute_with_recovery(action_type=A.CLICK,target='',selector='#send',text='',value='',url='',before_state=BrowserPageState(body_text='receipt 123'),expected=ExpectedState(text_present='receipt 123'))
 assert not out.success and not r._try_recovery_strategy.called
