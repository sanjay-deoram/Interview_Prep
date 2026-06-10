import pytest
from collections import defaultdict
from user_entitlement import EntitlementService, UserService, USERS, ENTITLEMENTS


@pytest.fixture
def service():
    """Fresh EntitlementService with clean state per test."""
    return EntitlementService()


# ---------------------------------------------------------------------------
# Assign entitlement
# ---------------------------------------------------------------------------

class TestAssignEntitlement:
    def test_assign_valid_entitlement_to_active_user(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        entitlements = service.get_entitlements_from_user("u1")
        assert any(e.id == "p1" for e in entitlements)

    def test_assigned_entitlement_appears_in_get(self, service):
        service.assign_entitlement_to_user("u1", "p2")
        entitlements = service.get_entitlements_from_user("u1")
        assert len(entitlements) == 1
        assert entitlements[0].id == "p2"

    def test_assign_multiple_entitlements_to_same_user(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        service.assign_entitlement_to_user("u1", "p2")
        entitlements = service.get_entitlements_from_user("u1")
        ids = {e.id for e in entitlements}
        assert ids == {"p1", "p2"}


# ---------------------------------------------------------------------------
# Duplicate prevention
# ---------------------------------------------------------------------------

class TestNoDuplicates:
    def test_assigning_same_entitlement_twice_raises(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        with pytest.raises(Exception):
            service.assign_entitlement_to_user("u1", "p1")

    def test_duplicate_does_not_inflate_count(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        try:
            service.assign_entitlement_to_user("u1", "p1")
        except Exception:
            pass
        assert len(service.get_entitlements_from_user("u1")) == 1


# ---------------------------------------------------------------------------
# Revoke entitlement
# ---------------------------------------------------------------------------

class TestRevokeEntitlement:
    def test_revoke_existing_entitlement(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        service.revoke_entitlement("u1", "p1")
        entitlements = service.get_entitlements_from_user("u1")
        assert not any(e.id == "p1" for e in entitlements)

    def test_revoke_one_does_not_remove_others(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        service.assign_entitlement_to_user("u1", "p2")
        service.revoke_entitlement("u1", "p1")
        entitlements = service.get_entitlements_from_user("u1")
        ids = {e.id for e in entitlements}
        assert ids == {"p2"}

    def test_revoke_non_existent_entitlement_raises(self, service):
        with pytest.raises(Exception):
            service.revoke_entitlement("u1", "p1")

    def test_revoke_entitlement_user_never_had_raises(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        with pytest.raises(Exception):
            service.revoke_entitlement("u1", "p2")


# ---------------------------------------------------------------------------
# Get entitlements
# ---------------------------------------------------------------------------

class TestGetEntitlements:
    def test_get_entitlements_returns_empty_for_user_with_none(self, service):
        result = service.get_entitlements_from_user("u1")
        assert result == []

    def test_get_entitlements_returns_all_assigned(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        service.assign_entitlement_to_user("u1", "p2")
        service.assign_entitlement_to_user("u1", "p3")
        result = service.get_entitlements_from_user("u1")
        assert len(result) == 3

    def test_get_entitlements_does_not_affect_other_users(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        result = service.get_entitlements_from_user("u2")
        assert result == []


# ---------------------------------------------------------------------------
# Inactive users
# ---------------------------------------------------------------------------

class TestInactiveUsers:
    def test_assign_to_inactive_user_raises(self, service):
        # u4 is inactive in USERS fixture
        with pytest.raises(Exception):
            service.assign_entitlement_to_user("u4", "p1")

    def test_inactive_user_existing_entitlements_are_readable(self, service):
        # Entitlements already present for inactive user should still be retrievable
        service.user_entitlment["u4"] = {ENTITLEMENTS["p1"]}
        result = service.get_entitlements_from_user("u4")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Invalid users
# ---------------------------------------------------------------------------

class TestInvalidUsers:
    def test_assign_to_nonexistent_user_raises(self, service):
        with pytest.raises(Exception):
            service.assign_entitlement_to_user("does_not_exist", "p1")

    def test_revoke_for_nonexistent_user_raises(self, service):
        with pytest.raises(Exception):
            service.revoke_entitlement("does_not_exist", "p1")

    def test_get_entitlements_for_nonexistent_user_raises(self, service):
        with pytest.raises(Exception):
            service.get_entitlements_from_user("does_not_exist")


# ---------------------------------------------------------------------------
# Invalid entitlements
# ---------------------------------------------------------------------------

class TestInvalidEntitlements:
    def test_assign_nonexistent_entitlement_raises(self, service):
        with pytest.raises(Exception):
            service.assign_entitlement_to_user("u1", "p_fake")

    def test_revoke_nonexistent_entitlement_id_raises(self, service):
        with pytest.raises(Exception):
            service.revoke_entitlement("u1", "p_fake")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_user_id_raises(self, service):
        with pytest.raises(Exception):
            service.assign_entitlement_to_user("", "p1")

    def test_empty_entitlement_id_raises(self, service):
        with pytest.raises(Exception):
            service.assign_entitlement_to_user("u1", "")

    def test_assign_all_entitlements_to_one_user(self, service):
        for eid in ENTITLEMENTS:
            service.assign_entitlement_to_user("u1", eid)
        result = service.get_entitlements_from_user("u1")
        assert len(result) == len(ENTITLEMENTS)

    def test_multiple_users_independent_entitlements(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        service.assign_entitlement_to_user("u2", "p2")
        assert len(service.get_entitlements_from_user("u1")) == 1
        assert len(service.get_entitlements_from_user("u2")) == 1
        assert service.get_entitlements_from_user("u1")[0].id == "p1"
        assert service.get_entitlements_from_user("u2")[0].id == "p2"

    def test_revoke_then_reassign_works(self, service):
        service.assign_entitlement_to_user("u1", "p1")
        service.revoke_entitlement("u1", "p1")
        service.assign_entitlement_to_user("u1", "p1")
        result = service.get_entitlements_from_user("u1")
        assert len(result) == 1
