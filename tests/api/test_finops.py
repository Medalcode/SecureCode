from uuid import uuid4

from securecode.adapters.postgres.models import UserAuditEvent, UserFinOpsSettings
from securecode.api.app import (
    FinOpsSettingsUpdateRequest,
    get_finops,
    update_finops,
)


class UserStub:
    def __init__(self, role="auditor"):
        self.id = uuid4()
        self.role = role


class SettingsQuery:
    def __init__(self, settings):
        self.settings = settings

    def filter(self, *_):
        return self

    def first(self):
        return self.settings


class EvaluationQuery:
    def filter(self, *_):
        return self

    def count(self):
        return 7


class SessionStub:
    def __init__(self, settings=None):
        self.settings = settings
        self.added = []
        self.commits = 0

    def query(self, model):
        if model is UserFinOpsSettings:
            return SettingsQuery(self.settings)
        return EvaluationQuery()

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1

    def refresh(self, _):
        return None


def test_finops_initializes_safe_preferences_and_measurable_consumption():
    response = get_finops(SessionStub(), UserStub())

    assert response["scope"] == "account"
    assert response["evaluations_current_period"] == 7
    assert response["evaluations_all_time"] == 7
    assert response["budget_clp"] == 1000
    assert response["billing_data_state"] == "not_connected"
    assert response["observed_spend_clp"] is None


def test_finops_preference_update_is_persisted_and_audited():
    user = UserStub()
    settings = UserFinOpsSettings(user_id=user.id, budget_clp=1000, alert_threshold_pct=80, alert_enabled=True)
    session = SessionStub(settings)

    response = update_finops(
        FinOpsSettingsUpdateRequest(budget_clp=200, alert_threshold_pct=50, alert_enabled=False),
        session,
        user,
    )

    assert response["budget_clp"] == 200
    assert response["alert_threshold_pct"] == 50
    assert response["alert_enabled"] is False
    assert any(isinstance(item, UserAuditEvent) and item.action == "finops_preferences_updated" for item in session.added)
