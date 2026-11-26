"""Source-control provider contract for collecting rule evidence.

Application services depend on this protocol, not on a vendor-specific adapter.
"""

from typing import Protocol

from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence


class SCMProviderPort(Protocol):
    """Evidence acquisition contract for supported SCM controls."""

    def get_gh001_evidence(
        self, owner: str, repo: str, branch: str, token: str | None = None,
    ) -> GH001Evidence:
        """Fetch branch review requirements."""
        ...

    def get_gh002_evidence(
        self, owner: str, repo: str, token: str | None = None,
    ) -> GH002Evidence:
        """Fetch default branch protection."""
        ...

    def get_gh003_evidence(
        self, owner: str, repo: str, branch: str, token: str | None = None,
    ) -> GH003Evidence:
        """Fetch signed commit requirements."""
        ...
