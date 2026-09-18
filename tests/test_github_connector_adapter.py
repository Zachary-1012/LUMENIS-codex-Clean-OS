"""GitHub connector/adapter contract tests; all network calls are injected."""

from github_connector import GitHubConnector, GitHubConnectorConfig, GitHubConnectorError
from lumenis.system.collector.adapters.github import GitHubAdapter
from lumenis.system.collector.adapters.base import CollectionStatus


def test_github_adapter_maps_allowlisted_read_data_without_business_rules():
    class Connector:
        def search_repositories(self, keyword, *, limit=20):
            assert keyword == "lumenis"
            return [{
                "id": 1,
                "full_name": "owner/lumenis",
                "description": "production truth",
                "owner": {"login": "owner"},
                "html_url": "https://github.com/owner/lumenis",
                "stargazers_count": 3,
            }]

    result = GitHubAdapter(connector=Connector()).search("lumenis")
    assert result.status == CollectionStatus.SUCCESS
    assert result.metadata["provider"] == "github_app_user_authorization"
    assert result.metadata["write_enabled"] is False
    assert result.items[0]["platform_content_id"] == "1"
    assert result.items[0]["title"] == "owner/lumenis"
    assert result.items[0]["content"] == "production truth"


def test_github_adapter_keeps_unconfigured_state_truthful():
    adapter = GitHubAdapter(connector=GitHubConnector(
        config=GitHubConnectorConfig(), token_provider=lambda: "",
    ))
    result = adapter.search("lumenis")
    assert result.status == CollectionStatus.NOT_CONFIGURED
    assert result.items == []
    assert result.metadata["error_code"] == "NOT_CONNECTED"


def test_github_connector_rejects_non_allowlisted_repo_before_network():
    calls = []

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("network must not run for a non-allowlisted repository")

    connector = GitHubConnector(
        config=GitHubConnectorConfig(repositories=("owner/allowed",)),
        token_provider=lambda: "token",
        opener=opener,
    )
    try:
        connector.repository("owner/blocked")
    except GitHubConnectorError as exc:
        assert exc.code == "REPOSITORY_NOT_ALLOWLISTED"
    else:
        raise AssertionError("expected repository allowlist failure")
    assert calls == []
