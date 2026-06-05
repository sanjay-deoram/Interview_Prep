import pytest
from live_fraud_detector import Event, FraudDetector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_stream(events):
    """Run a list of Event dicts through a fresh FraudDetector and return results."""
    detector = FraudDetector()
    results = []
    for e in events:
        results.append(detector.handle_event(Event(**e)))
    return results


# ---------------------------------------------------------------------------
# 1. Baseline — no fraud in the system yet
# ---------------------------------------------------------------------------

class TestNoFraud:

    def test_single_underwriting_approved(self):
        detector = FraudDetector()
        event = Event(
            event_type="underwriting",
            customer_details={"address": "1 Safe St", "phone": "555-000-0001", "email": "safe@example.com", "ssn": "000000001"},
            loan_amount=1000,
        )
        assert detector.handle_event(event) == "approved"

    def test_multiple_underwritings_all_approved(self):
        events = [
            {"event_type": "underwriting", "customer_details": {"address": "1 A St", "phone": "111-111-1111", "email": "a@x.com", "ssn": "111"}, "loan_amount": 500},
            {"event_type": "underwriting", "customer_details": {"address": "2 B St", "phone": "222-222-2222", "email": "b@x.com", "ssn": "222"}, "loan_amount": 500},
            {"event_type": "underwriting", "customer_details": {"address": "3 C St", "phone": "333-333-3333", "email": "c@x.com", "ssn": "333"}, "loan_amount": 500},
        ]
        assert run_stream(events) == ["approved", "approved", "approved"]

    def test_fraud_flag_returns_empty_string(self):
        detector = FraudDetector()
        event = Event(
            event_type="fraud_flag",
            customer_details={"address": "Bad Ave", "phone": "666-666-6666", "email": "bad@bad.com", "ssn": "666"},
        )
        assert detector.handle_event(event) == ""


# ---------------------------------------------------------------------------
# 2. Direct fraud flag → underwriting with matching PII
# ---------------------------------------------------------------------------

class TestDirectFraudDetection:

    def test_exact_same_customer_declined(self):
        """Same customer applies after being fraud-flagged."""
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "Bad Ave", "phone": "666-000-0001", "email": "fraud@bad.com", "ssn": "BAD001"}},
            {"event_type": "underwriting", "customer_details": {"address": "Bad Ave", "phone": "666-000-0001", "email": "fraud@bad.com", "ssn": "BAD001"}, "loan_amount": 2000},
        ]
        assert run_stream(events) == ["", "declined"]

    def test_matching_phone_is_sufficient_to_decline(self):
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "Old Addr", "phone": "999-000-0001", "email": "x@x.com", "ssn": "X01"}},
            {"event_type": "underwriting", "customer_details": {"address": "New Addr", "phone": "999-000-0001", "email": "new@new.com", "ssn": "NEW01"}, "loan_amount": 1000},
        ]
        assert run_stream(events) == ["", "declined"]

    def test_matching_email_is_sufficient_to_decline(self):
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "A", "phone": "000-000-0001", "email": "evil@evil.com", "ssn": "E01"}},
            {"event_type": "underwriting", "customer_details": {"address": "B", "phone": "000-000-0002", "email": "evil@evil.com", "ssn": "E02"}, "loan_amount": 500},
        ]
        assert run_stream(events) == ["", "declined"]

    def test_matching_address_is_sufficient_to_decline(self):
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "666 Bad Blvd", "phone": "000-000-0001", "email": "a@a.com", "ssn": "A01"}},
            {"event_type": "underwriting", "customer_details": {"address": "666 Bad Blvd", "phone": "111-111-1111", "email": "b@b.com", "ssn": "B01"}, "loan_amount": 500},
        ]
        assert run_stream(events) == ["", "declined"]

    def test_matching_ssn_is_sufficient_to_decline(self):
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "A", "phone": "000-000-0001", "email": "a@a.com", "ssn": "SHARED_SSN"}},
            {"event_type": "underwriting", "customer_details": {"address": "B", "phone": "111-111-1111", "email": "b@b.com", "ssn": "SHARED_SSN"}, "loan_amount": 500},
        ]
        assert run_stream(events) == ["", "declined"]

    def test_underwriting_before_fraud_flag_is_approved(self):
        """Event ordering matters — underwriting before the flag should be approved."""
        events = [
            {"event_type": "underwriting", "customer_details": {"address": "A", "phone": "999-999-9999", "email": "a@a.com", "ssn": "S01"}, "loan_amount": 1000},
            {"event_type": "fraud_flag", "customer_details": {"address": "A", "phone": "999-999-9999", "email": "a@a.com", "ssn": "S01"}},
        ]
        assert run_stream(events) == ["approved", ""]

    def test_no_pii_overlap_is_approved(self):
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "Bad Ave", "phone": "666-666-6666", "email": "bad@bad.com", "ssn": "BAD"}},
            {"event_type": "underwriting", "customer_details": {"address": "Safe St", "phone": "111-111-1111", "email": "safe@safe.com", "ssn": "SAFE"}, "loan_amount": 1000},
        ]
        assert run_stream(events) == ["", "approved"]


# ---------------------------------------------------------------------------
# 3. Transitive / cascading fraud (the core insight)
# ---------------------------------------------------------------------------

class TestTransitiveFraud:

    def test_sample_stream_from_problem(self):
        """Exact sample data from the problem statement."""
        events = [
            {
                "event_type": "underwriting",
                "customer_details": {"address": "123 Main St", "phone": "182-920-4124", "email": "johndoe@gmail.com", "ssn": "4568698929"},
                "loan_amount": 3000,
            },
            {
                "event_type": "fraud_flag",
                "customer_details": {"address": "123 Main St", "phone": "182-920-4124", "email": "johndoe@gmail.com", "ssn": "4568698929"},
            },
            {
                "event_type": "underwriting",
                "customer_details": {"address": "123 Main St", "phone": "947-213-9402", "email": "janedoe@yahoo.com", "ssn": "4568698929"},
                "loan_amount": 3000,
            },
            {
                "event_type": "underwriting",
                "customer_details": {"address": "654 5th Ave", "phone": "947-213-9402", "email": "jamesdoe@hotmail.com", "ssn": "938103583"},
                "loan_amount": 5000,
            },
        ]
        assert run_stream(events) == ["approved", "", "declined", "declined"]

    def test_second_hop_via_phone(self):
        """Fraudster B shares phone with flagged A; fraudster C shares email with B."""
        events = [
            # Flag person A
            {"event_type": "fraud_flag", "customer_details": {"address": "A-addr", "phone": "SHARED-AB", "email": "a@a.com", "ssn": "SSN-A"}},
            # Person B shares phone with A → declined, B's email added to set
            {"event_type": "underwriting", "customer_details": {"address": "B-addr", "phone": "SHARED-AB", "email": "SHARED-BC@b.com", "ssn": "SSN-B"}, "loan_amount": 1000},
            # Person C shares email with B → declined (two hops from original flag)
            {"event_type": "underwriting", "customer_details": {"address": "C-addr", "phone": "CLEAN-PHONE", "email": "SHARED-BC@b.com", "ssn": "SSN-C"}, "loan_amount": 1000},
        ]
        assert run_stream(events) == ["", "declined", "declined"]

    def test_chain_does_not_catch_unrelated_party(self):
        """Even after chaining, a customer with no PII overlap is still approved."""
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "A-addr", "phone": "SHARED-AB", "email": "a@a.com", "ssn": "SSN-A"}},
            {"event_type": "underwriting", "customer_details": {"address": "B-addr", "phone": "SHARED-AB", "email": "b@b.com", "ssn": "SSN-B"}, "loan_amount": 500},
            # Person D has zero PII overlap with any flagged customer
            {"event_type": "underwriting", "customer_details": {"address": "D-addr", "phone": "CLEAN", "email": "clean@clean.com", "ssn": "CLEAN-SSN"}, "loan_amount": 500},
        ]
        assert run_stream(events) == ["", "declined", "approved"]

    def test_declined_customer_pii_poisons_future_applicants(self):
        """A declined underwriting adds their PII; the next applicant sharing that PII is also declined."""
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "Origin", "phone": "P-ORIGIN", "email": "origin@x.com", "ssn": "SSN-ORIGIN"}},
            # Hop 1: shares phone with origin
            {"event_type": "underwriting", "customer_details": {"address": "Hop1", "phone": "P-ORIGIN", "email": "hop1@x.com", "ssn": "SSN-HOP1"}, "loan_amount": 100},
            # Hop 2: shares ssn with hop1 (not directly connected to origin)
            {"event_type": "underwriting", "customer_details": {"address": "Hop2", "phone": "P-FRESH", "email": "hop2@x.com", "ssn": "SSN-HOP1"}, "loan_amount": 100},
        ]
        assert run_stream(events) == ["", "declined", "declined"]


# ---------------------------------------------------------------------------
# 4. Multiple fraud flags
# ---------------------------------------------------------------------------

class TestMultipleFraudFlags:

    def test_two_separate_fraud_flags_both_propagate(self):
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "A-addr", "phone": "P-A", "email": "a@a.com", "ssn": "SSN-A"}},
            {"event_type": "fraud_flag", "customer_details": {"address": "B-addr", "phone": "P-B", "email": "b@b.com", "ssn": "SSN-B"}},
            # Matches group A
            {"event_type": "underwriting", "customer_details": {"address": "X-addr", "phone": "P-A", "email": "x@x.com", "ssn": "SSN-X"}, "loan_amount": 500},
            # Matches group B
            {"event_type": "underwriting", "customer_details": {"address": "Y-addr", "phone": "P-B", "email": "y@y.com", "ssn": "SSN-Y"}, "loan_amount": 500},
            # No match
            {"event_type": "underwriting", "customer_details": {"address": "Z-addr", "phone": "P-Z", "email": "z@z.com", "ssn": "SSN-Z"}, "loan_amount": 500},
        ]
        assert run_stream(events) == ["", "", "declined", "declined", "approved"]

    def test_duplicate_fraud_flag_idempotent(self):
        """Flagging the same customer twice should not break anything."""
        events = [
            {"event_type": "fraud_flag", "customer_details": {"address": "A", "phone": "P-A", "email": "a@a.com", "ssn": "SSN-A"}},
            {"event_type": "fraud_flag", "customer_details": {"address": "A", "phone": "P-A", "email": "a@a.com", "ssn": "SSN-A"}},
            {"event_type": "underwriting", "customer_details": {"address": "A", "phone": "P-A", "email": "a@a.com", "ssn": "SSN-A"}, "loan_amount": 1000},
        ]
        assert run_stream(events) == ["", "", "declined"]


# ---------------------------------------------------------------------------
# 5. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_pii_fields_not_added_to_set(self):
        """Empty-string PII values must not pollute the set."""
        detector = FraudDetector()
        # Flag a customer where some fields are empty
        flag = Event(event_type="fraud_flag", customer_details={"address": "", "phone": "", "email": "real@bad.com", "ssn": "BAD-SSN"})
        detector.handle_event(flag)

        # A completely different customer who happens to have empty address/phone
        underwriting = Event(
            event_type="underwriting",
            customer_details={"address": "", "phone": "", "email": "innocent@good.com", "ssn": "GOOD-SSN"},
            loan_amount=500,
        )
        assert detector.handle_event(underwriting) == "approved"

    def test_pii_set_grows_across_calls(self):
        """Verify the detector's pii set actually accumulates over multiple events."""
        detector = FraudDetector()
        detector.handle_event(Event(event_type="fraud_flag", customer_details={"address": "A", "phone": "PA", "email": "a@a.com", "ssn": "SA"}))
        assert "PA" in detector.pii
        assert "a@a.com" in detector.pii

    def test_fresh_detector_has_empty_pii(self):
        detector = FraudDetector()
        assert len(detector.pii) == 0

    def test_fraud_flag_adds_all_four_fields(self):
        detector = FraudDetector()
        detector.handle_event(Event(
            event_type="fraud_flag",
            customer_details={"address": "ADDR", "phone": "PHONE", "email": "EMAIL", "ssn": "SSN"},
        ))
        assert {"ADDR", "PHONE", "EMAIL", "SSN"}.issubset(detector.pii)

    def test_declined_adds_all_four_fields_to_pii(self):
        """When an underwriting is declined, all 4 of that customer's fields enter the PII set."""
        detector = FraudDetector()
        detector.handle_event(Event(event_type="fraud_flag", customer_details={"address": "X", "phone": "PX", "email": "x@x.com", "ssn": "SX"}))
        detector.handle_event(Event(
            event_type="underwriting",
            customer_details={"address": "Y", "phone": "PX", "email": "NEW-EMAIL", "ssn": "NEW-SSN"},
            loan_amount=1000,
        ))
        # After decline, NEW-EMAIL and NEW-SSN should now be in pii
        assert "NEW-EMAIL" in detector.pii
        assert "NEW-SSN" in detector.pii

    def test_approved_does_not_modify_pii_set(self):
        """A clean underwriting should leave the PII set unchanged."""
        detector = FraudDetector()
        detector.handle_event(Event(event_type="fraud_flag", customer_details={"address": "BAD", "phone": "PBAD", "email": "bad@bad.com", "ssn": "SBAD"}))
        pii_before = set(detector.pii)
        detector.handle_event(Event(
            event_type="underwriting",
            customer_details={"address": "GOOD", "phone": "PGOOD", "email": "good@good.com", "ssn": "SGOOD"},
            loan_amount=500,
        ))
        assert detector.pii == pii_before
