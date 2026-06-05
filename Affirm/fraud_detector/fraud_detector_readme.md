# Fraud Detector — Interview Problem

## Background

You are building a real-time fraud detection system for a Buy Now Pay Later (BNPL) company. Events arrive as a stream — each event is either a **loan underwriting application** or a **fraud flag**. Your system must maintain a running set of known-fraudulent PII (Personally Identifiable Information) and use it to make approve/decline decisions on incoming loan applications.

---

## Event Schemas

### Underwriting Event

A customer is applying for a loan.

| Required | Field | Type |
|----------|-------|------|
| yes | `event_type` | `"underwriting"` |
| yes | `loan_amount` | `int` |
| yes | `customer_details` | `dict` |
| **yes** | `customer_details.phone` | `string` |
| no | `customer_details.email` | `string` |
| no | `customer_details.address` | `string` |
| no | `customer_details.ssn` | `string` |
| no | `customer_details.credit_score` | `int` |

### Fraud Flag Event

A human investigator has confirmed a previous application was fraudulent. When received, store any supplied customer identifiers and return an empty string.

| Required | Field | Type |
|----------|-------|------|
| yes | `event_type` | `"fraud_flag"` |
| yes | `customer_details` | `dict` |
| no | `customer_details.phone` | `string` |
| no | `customer_details.email` | `string` |
| no | `customer_details.address` | `string` |
| no | `customer_details.ssn` | `string` |

---

## The Data Model

```python
@dataclass
class Event:
    event_type: str                          # "underwriting" | "fraud_flag"
    loan_amount: Optional[int]               # present on underwriting events only
    customer_details: Optional[Dict[str, str]]  # keys: phone, email, address, ssn, credit_score
```

---

## Your Task

Implement `FraudDetector.handle_event(self, event: Event) -> str`.

The class already has `self.pii` — a `set` initialized in `__init__` — that persists across calls. You must update it and return the appropriate result string for each event type.

### Event: `"fraud_flag"`

A downstream system has confirmed that this customer committed fraud. You must:

1. Add any supplied PII field values (`phone`, `email`, `address`, `ssn`) to `self.pii`.
2. Return `""` (empty string).

### Event: `"underwriting"`

A customer is applying for a loan. You must:

1. Check whether **any** of the customer's PII field values appear in `self.pii`.
2. **If a match is found** (fraudulent PII detected):
   - Add **all** of that customer's PII field values to `self.pii` (fraud is transitive — their info may expose future fraudsters).
   - Return `"declined"`.
3. **If no match is found**:
   - Return `"approved"`.

---

## Example Walkthrough

Given the following event stream:

```json
[
  {
    "event_type": "underwriting",
    "customer_details": {
      "address": "123 Main St",
      "phone": "182-920-4124",
      "email": "johndoe@gmail.com",
      "ssn": "4568698929"
    },
    "loan_amount": 3000
  },
  {
    "event_type": "fraud_flag",
    "customer_details": {
      "address": "123 Main St",
      "phone": "182-920-4124",
      "email": "johndoe@gmail.com",
      "ssn": "4568698929"
    }
  },
  {
    "event_type": "underwriting",
    "customer_details": {
      "address": "123 Main St",
      "phone": "947-213-9402",
      "email": "janedoe@yahoo.com",
      "ssn": "4568698929"
    },
    "loan_amount": 3000
  },
  {
    "event_type": "underwriting",
    "customer_details": {
      "address": "654 5th Ave",
      "phone": "947-213-9402",
      "email": "jamesdoe@hotmail.com",
      "ssn": "938103583"
    },
    "loan_amount": 5000
  }
]
```

**Step-by-step:**

| # | Event | PII Set Before | Result | PII Set After |
|---|-------|---------------|--------|---------------|
| 1 | underwriting — johndoe | `{}` | `"approved"` | `{}` |
| 2 | fraud_flag — johndoe | `{}` | `""` | `{"123 Main St", "182-920-4124", "johndoe@gmail.com", "4568698929"}` |
| 3 | underwriting — janedoe | `{..johndoe PII..}` | `"declined"` (ssn matches) | adds janedoe's phone `"947-213-9402"` and other fields |
| 4 | underwriting — jamesdoe | `{..johndoe + janedoe PII..}` | `"declined"` (phone `947-213-9402` matches janedoe's) | adds jamesdoe's fields |

Key insight: fraud is **transitive**. Because janedoe's SSN matched johndoe's (known fraudster), janedoe's phone was added to the PII set — which then caught jamesdoe.

**Expected output for the stream:** `["approved", "", "declined", "declined"]`

---

## Constraints & Notes

- `self.pii` is a `set` — O(1) lookups.
- PII field values are plain strings. Treat them as opaque tokens (no parsing needed).
- Missing or empty string field values should be ignored (do not add `""` to the PII set).
- The only two valid `event_type` values are `"underwriting"` and `"fraud_flag"`. You can assume well-formed input.
- `handle_event` is called one event at a time, in order.

---

## Starter Code

See `live_fraud_detector.py`. The `Event` dataclass and class skeleton are provided. Implement the body of `handle_event`.
