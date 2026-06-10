from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional
import datetime


@dataclass
class User:
    id: str
    name: str
    active: bool


@dataclass
class Entitlement:
    id: int
    name: str
    created_at: datetime = field(default_factory=datetime.datetime.now)

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"{self.id} | {self.name}"


USERS = {
    "u1": User(id="u1", name="Brandon Deoram", active=True),
    "u2": User(id="u2", name="John Doe", active=True),
    "u3": User(id="u3", name="Richard Singh", active=True),
    "u4": User(id="u4", name="Brianna Singh", active=False),
    "u5": User(id="u5", name="Amisha Deoram", active=True),
}

ENTITLEMENTS = {
    "p1": Entitlement(id="p1", name="autocad"),
    "p2": Entitlement(id="p2", name="revit"),
    "p3": Entitlement(id="p3", name="3dsmax"),
}


class UserService:
    def __init__(self) -> None:
        self.users: dict[str:User] = USERS

    def _find_user_by_id(self, user_id: str) -> User:
        """Find user by id, active or inactive"""
        if not user_id in USERS:
            raise Exception("User not found")

        return USERS[user_id]

    def _find_active_user_by_id(self, user_id: str) -> Optional[User]:
        """Finds active user by id only"""
        user = self._find_user_by_id(user_id)

        if user.active == False:
            raise Exception("Cannot assign entitlment to inactive user")

        return USERS[user_id]


class EntitlementService:
    def __init__(self) -> None:
        self.user_entitlment: defaultdict[User.id : set[Entitlement]()] = defaultdict(
            set
        )
        self.entitlements: defaultdict[str:Entitlement] = ENTITLEMENTS
        self.users = UserService()

    def assign_entitlement_to_user(self, user_id: str, entitlement_id: str):
        user = self.users._find_active_user_by_id(user_id)
        entitlement = self._get_entitlement(entitlement_id)

        if entitlement in self.user_entitlment[user.id]:
            raise Exception(f"Entitlement already exists")

        self.user_entitlment[user.id].add(entitlement)

    def revoke_entitlement(
        self, user_id: str, entitlement_id: str
    ) -> List[Entitlement]:
        user = self.users._find_active_user_by_id(user_id)
        entitlement = self._get_entitlement(entitlement_id)

        if entitlement not in self.user_entitlment[user.id]:
            raise Exception("User doesnt have this entitlment to revoke")

        self.user_entitlment[user.id].remove(entitlement)

        return self.get_entitlements_from_user(user.id)

    def get_entitlements_from_user(self, user_id) -> List[Entitlement]:
        user = self.users._find_user_by_id(user_id)

        return list(self.user_entitlment[user.id])

    def _get_entitlement(self, entitlement_id: str) -> Entitlement:
        if not entitlement_id in self.entitlements:
            raise Exception(f"Entitilment with id: {entitlement_id} not found")

        return self.entitlements[entitlement_id]
