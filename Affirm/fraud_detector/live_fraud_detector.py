from dataclasses import dataclass
from math import pi
from typing import Optional, Dict

# run tests: python3 -m pytest test_fraud_detector.py -v


@dataclass
class Event:
    event_type: str
    loan_amount: Optional[int] = None
    customer_details: Optional[Dict[str, str]] = None


pii_keys = ("address", "phone", "email", "ssn")


class FraudDetector:

    def __init__(self):
        self.pii = set()

    def handle_event(self, event: Event) -> str:
        print("event ==", event)
        if not event.event_type:
            raise Exception("No event type provided")

        if not event.customer_details:
            raise Exception("Customer details missing")

        customer_details = event.customer_details

        if event.event_type == "fraud_flag":
            self.add_pii_value(customer_details)
            return ""

        if event.event_type == "underwriting":
            if self.is_fraud(customer_details):
                self.add_pii_value(customer_details)
                return "declined"
            return "approved"

        raise ValueError("Invalid event type")

    def add_pii_value(self, customer_details: Event.customer_details):
        for pii in pii_keys:
            pii_value = customer_details.get(pii, "")
            if pii_value:
                self.pii.add(pii_value)

    def is_fraud(self, customer_details: Event.customer_details) -> bool:
        for pii in pii_keys:
            pii_value = customer_details.get(pii, "")
            if pii_value in self.pii:
                return True
        return False


if __name__ == "__main__":
    sample_events = [
        {
            "event_type": "underwriting",
            "customer_details": {
                "address": "123 Main St",
                "phone": "182-920-4124",
                "email": "johndoe@gmail.com",
                "ssn": "4568698929",
            },
            "loan_amount": 3000,
        },
        {
            "event_type": "fraud_flag",
            "customer_details": {
                "address": "123 Main St",
                "phone": "182-920-4124",
                "email": "johndoe@gmail.com",
                "ssn": "4568698929",
            },
        },
        {
            "event_type": "underwriting",
            "customer_details": {
                "address": "123 Main St",
                "phone": "947-213-9402",
                "email": "janedoe@yahoo.com",
                "ssn": "4568698929",
            },
            "loan_amount": 3000,
        },
        {
            "event_type": "underwriting",
            "customer_details": {
                "address": "654 5th Ave",
                "phone": "947-213-9402",
                "email": "jamesdoe@hotmail.com",
                "ssn": "938103583",
            },
            "loan_amount": 5000,
        },
    ]

    detector = FraudDetector()

    for i, raw in enumerate(sample_events):
        event = Event(**raw)
        result = detector.handle_event(event)
        print(
            f"Event {i + 1} ({event.event_type}): {result!r}  |  pii set: {detector.pii}"
        )
