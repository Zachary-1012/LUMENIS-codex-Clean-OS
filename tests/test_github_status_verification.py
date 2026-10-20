import json
import pytest
from github_connector import GitHubConnector, GitHubConnectorConfig, GitHubConnectorError
from lumenis.system.collector.adapters.github import GitHubAdapter
from lumenis.system.collector.adapters.base import CollectionStatus


def test_token_presence_is_not_connected_and_does_not_probe():
    def forbidden(*args,**kwargs):raise AssertionError('status must not make network calls')
    c=GitHubConnector(config=GitHubConnectorConfig(),token_provider=lambda:'synthetic-token',opener=forbidden)
    s=c.status()
    assert s['state']=='PROVIDER_UNAVAILABLE'
    assert s['authorization_verification']=='NOT_VERIFIED'
    assert s['code']=='HEALTH_CHECK_REQUIRED'
    assert s['write_enabled'] is False
    assert 'synthetic-token' not in json.dumps(s)


def test_credential_provider_failure_is_unavailable():
    def fail():raise RuntimeError('synthetic-sensitive-error')
    s=GitHubConnector(token_provider=fail).status()
    assert s['state']=='PROVIDER_UNAVAILABLE'
    assert s['code']=='CREDENTIAL_PROVIDER_ERROR'
    assert 'synthetic-sensitive-error' not in json.dumps(s)


@pytest.mark.parametrize('payload',[{}, {'login':''},{'login':123}, {'login':'  '}, []])
def test_invalid_user_payload_cannot_verify(payload):
    c=GitHubConnector(token_provider=lambda:'synthetic-token')
    c.get_json=lambda path:payload
    r=GitHubAdapter(connector=c).health_check()
    assert r.status != CollectionStatus.SUCCESS
    assert r.metadata.get('state')!='CONNECTED'


def test_explicit_health_checks_current_user_each_time():
    c=GitHubConnector(token_provider=lambda:'synthetic-token')
    calls=[]
    def good(path):calls.append(path);return {'login':'fixture-owner'}
    c.get_json=good
    r=GitHubAdapter(connector=c).health_check()
    assert r.status==CollectionStatus.SUCCESS and r.metadata['state']=='CONNECTED'
    assert r.metadata['authorization_verification']=='CURRENT_USER_VERIFIED'
    assert r.metadata['repository_access_verification']=='NOT_VERIFIED'
    assert calls==['/user']
    def revoked(path):raise GitHubConnectorError('AUTHENTICATION_OR_PERMISSION_FAILED','Authorization failed')
    c.get_json=revoked
    r=GitHubAdapter(connector=c).health_check()
    assert r.status==CollectionStatus.SESSION_EXPIRED
    assert c.status()['state']!='CONNECTED'


def test_absent_credentials_remain_unconfigured_without_probe():
    c=GitHubConnector(config=GitHubConnectorConfig(),token_provider=lambda:'')
    c.get_json=lambda path:pytest.fail('must not probe')
    assert c.status()['state']=='NOT_CONFIGURED'
    assert GitHubAdapter(connector=c).health_check().status==CollectionStatus.NOT_CONFIGURED
