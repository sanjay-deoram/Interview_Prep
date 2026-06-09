from dataclasses import dataclass, field
from datetime import date
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
    created_at: datetime = field(default_factory=datetime.datetime.now())


USERS = {
    "u1": User(id="u1", name="Brandon Deoram", active=True),
    "u2": User(id="u1", name="Brandon Deoram", active=True),
    "u3": User(id="u1", name="Brandon Deoram", active=True),
    "u4": User(id="u1", name="Brandon Deoram", active=False),
    "u5": User(id="u1", name="Brandon Deoram", active=True),
}

ENTITLEMENTS = {
    "p1": Entitlement(id="p1", name="autocad"),
    "p2": Entitlement(id="p2", name="revit"),
    "p3": Entitlement(id="p3", name="3dsmax"),
}


class EntitlementService:
    def __init__(self) -> None:
        self.user_entitlment: dict[User.id : set[Entitlement]()] = {}

    def assign_entitlement() -> None:
        pass

    def revoke_entitlement() -> None:
        pass

    def get_entitlements() -> None:
        pass
