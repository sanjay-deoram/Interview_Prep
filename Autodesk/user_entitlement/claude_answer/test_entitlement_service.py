import pytest
from entitlement_service import EntitlementService, EntitlementError


@pytest.fixture
def service():
    return EntitlementService()


# --- assign_entitlement ---

class TestAssign:
    def test_assign_single_product(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        assert "AutoCAD" in service.get_entitlements("user_1")

    def test_assign_multiple_products(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        service.assign_entitlement("user_1", "Revit")
        assert service.get_entitlements("user_1") == ["AutoCAD", "Revit"]

    def test_assign_is_idempotent(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        service.assign_entitlement("user_1", "AutoCAD")
        assert service.get_entitlements("user_1").count("AutoCAD") == 1

    def test_assign_to_multiple_users(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        service.assign_entitlement("user_2", "Revit")
        assert service.get_entitlements("user_1") == ["AutoCAD"]
        assert service.get_entitlements("user_2") == ["Revit"]

    def test_assign_raises_on_empty_user_id(self, service):
        with pytest.raises(EntitlementError):
            service.assign_entitlement("", "AutoCAD")

    def test_assign_raises_on_none_user_id(self, service):
        with pytest.raises(EntitlementError):
            service.assign_entitlement(None, "AutoCAD")

    def test_assign_raises_on_empty_product_id(self, service):
        with pytest.raises(EntitlementError):
            service.assign_entitlement("user_1", "")

    def test_assign_raises_on_whitespace_product_id(self, service):
        with pytest.raises(EntitlementError):
            service.assign_entitlement("user_1", "   ")


# --- revoke_entitlement ---

class TestRevoke:
    def test_revoke_removes_product(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        service.revoke_entitlement("user_1", "AutoCAD")
        assert service.get_entitlements("user_1") == []

    def test_revoke_only_removes_target_product(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        service.assign_entitlement("user_1", "Revit")
        service.revoke_entitlement("user_1", "AutoCAD")
        assert service.get_entitlements("user_1") == ["Revit"]

    def test_revoke_nonexistent_entitlement_raises(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        with pytest.raises(EntitlementError):
            service.revoke_entitlement("user_1", "Revit")

    def test_revoke_unknown_user_raises(self, service):
        with pytest.raises(EntitlementError):
            service.revoke_entitlement("ghost_user", "AutoCAD")

    def test_revoke_then_reassign(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        service.revoke_entitlement("user_1", "AutoCAD")
        service.assign_entitlement("user_1", "AutoCAD")
        assert service.get_entitlements("user_1") == ["AutoCAD"]

    def test_revoke_raises_on_empty_user_id(self, service):
        with pytest.raises(EntitlementError):
            service.revoke_entitlement("", "AutoCAD")

    def test_revoke_raises_on_none_product_id(self, service):
        with pytest.raises(EntitlementError):
            service.revoke_entitlement("user_1", None)


# --- get_entitlements ---

class TestGetEntitlements:
    def test_get_returns_empty_list_for_unknown_user(self, service):
        assert service.get_entitlements("ghost_user") == []

    def test_get_returns_empty_list_after_all_revoked(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        service.revoke_entitlement("user_1", "AutoCAD")
        assert service.get_entitlements("user_1") == []

    def test_get_returns_sorted_list(self, service):
        service.assign_entitlement("user_1", "Revit")
        service.assign_entitlement("user_1", "AutoCAD")
        service.assign_entitlement("user_1", "Fusion360")
        assert service.get_entitlements("user_1") == ["AutoCAD", "Fusion360", "Revit"]

    def test_get_does_not_affect_other_users(self, service):
        service.assign_entitlement("user_1", "AutoCAD")
        service.assign_entitlement("user_2", "Revit")
        service.get_entitlements("user_1")
        assert service.get_entitlements("user_2") == ["Revit"]

    def test_get_raises_on_empty_user_id(self, service):
        with pytest.raises(EntitlementError):
            service.get_entitlements("")

    def test_get_raises_on_none_user_id(self, service):
        with pytest.raises(EntitlementError):
            service.get_entitlements(None)
