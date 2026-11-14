from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from securecode.adapters.postgres.models import OrganizationMembership, SubscriptionEvent, UserSubscription
from securecode.api.app import (
    SubscriptionChangeRequest,
    change_subscription,
    get_subscription,
)


class UserStub:
    def __init__(self):
        self.id = uuid4()
        self.role = "organization_owner"


class QueryStub:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *_):
        return self

    def first(self):
        return self.result

    def order_by(self, *_):
        return self


class MembershipQuery(QueryStub):
    def __init__(self, user_id):
        super().__init__(type("Membership", (), {
            "user_id": user_id, "organization_id": uuid4(), "role": "organization_owner",
        })())


class SessionStub:
    def __init__(self, subscription=None, user_id=None):
        self.query_stub = QueryStub(subscription)
        self.user_id = user_id or uuid4()
        self.added = []
        self.commits = 0

    def query(self, model, *_):
        if model is OrganizationMembership:
            return MembershipQuery(self.user_id)
        return self.query_stub

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1

    def refresh(self, _):
        return None


def test_first_subscription_is_initialized_as_non_billable_pro_period():
    user = UserStub()
    response = get_subscription(SessionStub(user_id=user.id), user)

    assert response["plan_id"] == "pro"
    assert response["billing_mode"] == "demo_non_billable"
    assert response["expires_at"] - response["started_at"] == timedelta(days=30)


def test_subscription_change_requires_confirmation_and_respects_30_day_lock():
    user = UserStub()
    now = datetime.now(timezone.utc)
    locked = UserSubscription(
        user_id=user.id, plan_id="pro", started_at=now,
        expires_at=now + timedelta(days=30), last_changed_at=now,
    )

    with pytest.raises(HTTPException) as no_confirmation:
        change_subscription(SubscriptionChangeRequest(plan_id="premium", confirmation=False), SessionStub(locked, user.id), user)
    assert no_confirmation.value.status_code == 422

    with pytest.raises(HTTPException) as locked_change:
        change_subscription(SubscriptionChangeRequest(plan_id="premium", confirmation=True), SessionStub(locked, user.id), user)
    assert locked_change.value.status_code == 409


def test_confirmed_change_creates_history_and_new_30_day_period():
    user = UserStub()
    old = datetime.now(timezone.utc) - timedelta(days=31)
    subscription = UserSubscription(
        user_id=user.id, plan_id="pro", started_at=old,
        expires_at=old + timedelta(days=30), last_changed_at=old,
    )
    session = SessionStub(subscription, user.id)

    response = change_subscription(SubscriptionChangeRequest(plan_id="premium", confirmation=True), session, user)

    assert response["plan_id"] == "premium"
    assert response["can_change"] is False
    assert response["expires_at"] - response["started_at"] == timedelta(days=30)
    assert any(isinstance(item, SubscriptionEvent) and item.event_type == "plan_changed" for item in session.added)
