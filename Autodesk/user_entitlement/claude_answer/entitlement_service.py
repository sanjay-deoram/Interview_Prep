class EntitlementError(Exception):
    pass


class EntitlementService:
    def __init__(self):
        # user_id -> set of product_ids
        self._entitlements: dict[str, set[str]] = {}

    def assign_entitlement(self, user_id: str, product_id: str) -> None:
        self._validate(user_id, "user_id")
        self._validate(product_id, "product_id")

        if user_id not in self._entitlements:
            self._entitlements[user_id] = set()

        # idempotent — assigning an already-held product is a no-op
        self._entitlements[user_id].add(product_id)

    def revoke_entitlement(self, user_id: str, product_id: str) -> None:
        self._validate(user_id, "user_id")
        self._validate(product_id, "product_id")

        if user_id not in self._entitlements or product_id not in self._entitlements[user_id]:
            raise EntitlementError(
                f"User '{user_id}' does not hold entitlement '{product_id}'"
            )

        self._entitlements[user_id].remove(product_id)

    def get_entitlements(self, user_id: str) -> list[str]:
        self._validate(user_id, "user_id")

        # unknown user and user with no entitlements both return empty list
        return sorted(self._entitlements.get(user_id, set()))

    def _validate(self, value: str, field: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise EntitlementError(f"'{field}' must be a non-empty string, got: {value!r}")
