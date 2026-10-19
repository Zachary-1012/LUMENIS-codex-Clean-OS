from unittest.mock import Mock
import pytest
from ai_browser_runtime import AIBrowserRuntime, BrowserActionType

@pytest.mark.parametrize('url',['file:///etc/passwd','javascript:alert(1)','http://127.0.0.1/private'])
def test_tab_creation_cannot_skip_original_navigation_policy(monkeypatch,url):
 import browser_surface
 policy=Mock(return_value={'allowed':False});monkeypatch.setattr(browser_surface,'evaluate_navigation',policy)
 r=AIBrowserRuntime();r._context=Mock();r._page=Mock()
 with pytest.raises(PermissionError):r._do_execute(BrowserActionType.TAB_NEW,url=url)
 policy.assert_called_once_with(url);r._context.new_page.assert_not_called()

def test_allowed_new_tab_uses_original_policy_and_navigates(monkeypatch):
 import browser_surface
 policy=Mock(return_value={'allowed':True});monkeypatch.setattr(browser_surface,'evaluate_navigation',policy)
 r=AIBrowserRuntime();r._context=Mock();r._page=Mock()
 r._do_execute(BrowserActionType.TAB_NEW,url='https://example.org')
 policy.assert_called_once_with('https://example.org');r._context.new_page.return_value.goto.assert_called_once()

def test_blank_tab_still_allowed_without_external_navigation(monkeypatch):
 import browser_surface
 policy=Mock();monkeypatch.setattr(browser_surface,'evaluate_navigation',policy)
 r=AIBrowserRuntime();r._context=Mock();r._page=Mock()
 r._do_execute(BrowserActionType.TAB_NEW)
 policy.assert_not_called();r._context.new_page.return_value.goto.assert_not_called()

@pytest.mark.parametrize('url',['file:///etc/passwd','javascript:alert(1)','data:text/html,hello'])
def test_real_navigation_owner_rejects_dangerous_scheme_before_new_tab(url):
 r=AIBrowserRuntime();r._context=Mock();r._page=Mock()
 with pytest.raises(PermissionError):r._do_execute(BrowserActionType.TAB_NEW,url=url)
 r._context.new_page.assert_not_called()
