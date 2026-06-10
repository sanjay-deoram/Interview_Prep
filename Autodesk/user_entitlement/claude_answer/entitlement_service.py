class EntitlementError(Exception):
    pass


USERS = {"alice", "bob", "carol", "dave"}
PRODUCTS = {"autocad", "revit", "fusion360", "maya"}

DEFAULT_ENTITLEMENTS: dict[str, set[str]] = {
    "alice": {"autocad", "revit"},
    "bob":   {"autocad"},
    "carol": {"fusion360", "maya"},
}


class EntitlementService:
    def __init__(self):
        self._entitlements: dict[str, set[str]] = {
            user: set(products)
            for user, products in DEFAULT_ENTITLEMENTS.items()
        }

    def assign_entitlement(self, user_id: str, product_id: str) -> None:
        self._validate_user(user_id)
        self._validate_product(product_id)

        if user_id not in self._entitlements:
            self._entitlements[user_id] = set()

        self._entitlements[user_id].add(product_id)

    def revoke_entitlement(self, user_id: str, product_id: str) -> None:
        self._validate_user(user_id)
        self._validate_product(product_id)

        if user_id not in self._entitlements or product_id not in self._entitlements[user_id]:
            raise EntitlementError(
                f"User '{user_id}' does not hold entitlement '{product_id}'"
            )

        self._entitlements[user_id].remove(product_id)

    def get_entitlements(self, user_id: str) -> list[str]:
        self._validate_user(user_id)
        return sorted(self._entitlements.get(user_id, set()))

    def _validate_user(self, user_id: str) -> None:
        if not isinstance(user_id, str) or not user_id.strip():
            raise EntitlementError(f"'user_id' must be a non-empty string, got: {user_id!r}")
        if user_id not in USERS:
            raise EntitlementError(f"Unknown user: '{user_id}'")

    def _validate_product(self, product_id: str) -> None:
        if not isinstance(product_id, str) or not product_id.strip():
            raise EntitlementError(f"'product_id' must be a non-empty string, got: {product_id!r}")
        if product_id not in PRODUCTS:
            raise EntitlementError(f"Unknown product: '{product_id}'")
