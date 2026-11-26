"""Regression tests for vendor-neutral SCM port substitution."""

from securecode.adapters.github import GitHubSCMProvider
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence
from securecode.ports.scm_provider import SCMProviderPort


class FakeSCMProvider:
    """A provider that requires no GitHub dependency or network access."""

    def get_gh001_evidence(
        self, owner: str, repo: str, branch: str, token: str | None = None,
    ) -> GH001Evidence:
        return GH001Evidence(required_review_approvals=1, dismiss_stale_reviews=True)

    def get_gh002_evidence(
        self, owner: str, repo: str, token: str | None = None,
    ) -> GH002Evidence:
        return GH002Evidence(default_branch="main", protection_enabled=True)

    def get_gh003_evidence(
        self, owner: str, repo: str, branch: str, token: str | None = None,
    ) -> GH003Evidence:
        return GH003Evidence(branch=branch, required_signatures_enabled=True)


def test_github_adapter_implements_scm_provider_contract() -> None:
    provider: SCMProviderPort = GitHubSCMProvider()
    assert callable(provider.get_gh001_evidence)
    assert callable(provider.get_gh002_evidence)
    assert callable(provider.get_gh003_evidence)


def test_provider_can_be_replaced_without_github_network() -> None:
    provider: SCMProviderPort = FakeSCMProvider()
    assert provider.get_gh001_evidence("org", "repo", "main").required_review_approvals == 1
    assert provider.get_gh002_evidence("org", "repo").protection_enabled is True
    assert provider.get_gh003_evidence("org", "repo", "main").required_signatures_enabled is True
