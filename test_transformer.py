"""
PHI/PII Redaction Test Suite
============================
Covers:
  - Name redaction (title-based, context-based, transformer)
  - Regex entity detection: Email, Phone, IP, MRN, DOB, Address
  - New entities: URL, VIN, License Number
  - Entity merge helpers
  - False-positive suppression
"""
from __future__ import annotations
import re
import time
from collections import Counter
from dataclasses import dataclass
from uuid import UUID, uuid4


try:
    from fastapi.testclient import TestClient

    from backend.main import (
        ACCOUNT_PATTERN,
        ADDRESS_PATTERN,
        AGE_PATTERN,
        DEVICE_PATTERN,
        DOB_PATTERN,
        EMAIL_PATTERN,
        FACILITY_PATTERN,
        FAX_PATTERN,
        HEALTH_PLAN_PATTERN,
        IP_PATTERN,
        LICENSE_PATTERN,
        LOCATION_PATTERN,
        MRN_PATTERN,
        PHONE_PATTERN,
        SSN_PATTERN,
        URL_PATTERN,
        VIN_PATTERN,
        TextInput,
        _apply_structured_redactions,
        app,
        redact_names,
    )
    from backend.mapping_store import create_session, delete_session, store_mapping
    from transformer_ner import (
        NameEntity,
        _merge_adjacent,
        _post_process,
        build_redacted_text,
        detect_names_transformer,
    )

    MODULES_AVAILABLE = True
    IMPORT_ERROR = ""

except Exception as exc:
    MODULES_AVAILABLE = False
    IMPORT_ERROR = str(exc)

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


@dataclass
class RedactionTestCase:
    name: str
    input_text: str
    expected_output: str
    category: str = "general"
    expected_name_count: int | None = None
    notes: str = ""


@dataclass
class EvalResult:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        if not self.precision + self.recall:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)

    def __add__(self, other: "EvalResult") -> "EvalResult":
        return EvalResult(
            tp=self.tp + other.tp,
            fp=self.fp + other.fp,
            fn=self.fn + other.fn,
        )


# ---------------------------------------------------------------------------
# Name test cases
# ---------------------------------------------------------------------------

NAME_TEST_CASES: list[RedactionTestCase] = [
    # --- original cases ---
    RedactionTestCase(
        name="title_dot_no_space",
        input_text="My name is Sathish doctor name : DR.Ashwin",
        expected_output="My name is [NAME_REDACTED] doctor name : DR.[NAME_REDACTED]",
        category="title",
        expected_name_count=2,
    ),
    RedactionTestCase(
        name="title_with_space",
        input_text="Referred by Dr. Ramesh to Mr. Kumar",
        expected_output="Referred by Dr. [NAME_REDACTED] to Mr. [NAME_REDACTED]",
        category="title",
        expected_name_count=2,
    ),
    RedactionTestCase(
        name="title_mrs",
        input_text="Patient is Mrs. Lakshmi, DOB 12/01/1985",
        expected_output="Patient is Mrs. [NAME_REDACTED], DOB [DOB_REDACTED]",
        category="title",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="title_prof",
        input_text="Reviewed by Prof. Subramaniam",
        expected_output="Reviewed by Prof. [NAME_REDACTED]",
        category="title",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="title_only_no_name",
        input_text="The doctor ordered an MRI.",
        expected_output="The doctor ordered an MRI.",
        category="title",
        expected_name_count=0,
    ),
    RedactionTestCase(
        name="plain_name_single",
        input_text="Patient Arun was admitted on Monday.",
        expected_output="Patient [NAME_REDACTED] was admitted on Monday.",
        category="names",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="plain_name_full",
        input_text="Contact Priya Sharma at extension 102.",
        expected_output="Contact [NAME_REDACTED] at extension 102.",
        category="names",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="multiple_names_sentence",
        input_text="Sathish visited Dr. Ashwin and was referred to Dr. Priya.",
        expected_output="[NAME_REDACTED] visited Dr. [NAME_REDACTED] and was referred to Dr. [NAME_REDACTED].",
        category="names",
        expected_name_count=3,
    ),
    RedactionTestCase(
        name="stopword_patient",
        input_text="The patient was seen by the nurse.",
        expected_output="The patient was seen by the nurse.",
        category="stopwords",
        expected_name_count=0,
    ),
    RedactionTestCase(
        name="stopword_diagnosis",
        input_text="Diagnosis: hypertension. Treatment: medication.",
        expected_output="Diagnosis: hypertension. Treatment: medication.",
        category="stopwords",
        expected_name_count=0,
    ),
    RedactionTestCase(
        name="stopword_email_word",
        input_text="Send via email to John.",
        expected_output="Send via email to [NAME_REDACTED].",
        category="stopwords",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="name_at_sentence_start",
        input_text="Ramesh is the referring physician.",
        expected_output="[NAME_REDACTED] is the referring physician.",
        category="edge",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="name_end_of_sentence",
        input_text="The prescription was signed by Vijay.",
        expected_output="The prescription was signed by [NAME_REDACTED].",
        category="edge",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="empty_after_sanitize",
        input_text="   ",
        expected_output="VALIDATION_ERROR",
        category="edge",
    ),
    # --- new healthcare name detection tests (≥10) ---
    RedactionTestCase(
        name="patient_title_first_last",
        input_text="Patient Robert Brown was discharged today.",
        expected_output="Patient [NAME_REDACTED] was discharged today.",
        category="healthcare_names",
        expected_name_count=1,
        notes="Patient as title prefix",
    ),
    RedactionTestCase(
        name="patient_title_single_name",
        input_text="Patient Meena presented with fever.",
        expected_output="Patient [NAME_REDACTED] presented with fever.",
        category="healthcare_names",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="doctor_no_dot",
        input_text="Dr Ashwin Kumar reviewed the case.",
        expected_output="Dr [NAME_REDACTED] reviewed the case.",
        category="healthcare_names",
        expected_name_count=1,
        notes="Dr without period",
    ),
    RedactionTestCase(
        name="mr_no_dot",
        input_text="Mr John Smith called the clinic.",
        expected_output="Mr [NAME_REDACTED] called the clinic.",
        category="healthcare_names",
        expected_name_count=1,
        notes="Mr without period",
    ),
    RedactionTestCase(
        name="professor_full_word",
        input_text="Professor Anand heads the cardiology department.",
        expected_output="Professor [NAME_REDACTED] heads the cardiology department.",
        category="healthcare_names",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="miss_title",
        input_text="Miss Deepika is scheduled for follow-up.",
        expected_output="Miss [NAME_REDACTED] is scheduled for follow-up.",
        category="healthcare_names",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="ms_title",
        input_text="Ms Kavitha reported chest pain.",
        expected_output="Ms [NAME_REDACTED] reported chest pain.",
        category="healthcare_names",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="signed_by_context",
        input_text="Report signed by Narayanan on 05/12/2024.",
        expected_output="Report signed by [NAME_REDACTED] on [DOB_REDACTED].",
        category="healthcare_names",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="referred_by_context",
        input_text="Referred by Dr. Senthil to the oncology unit.",
        expected_output="Referred by Dr. [NAME_REDACTED] to the oncology unit.",
        category="healthcare_names",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="attending_physician_context",
        input_text="Attending: Dr. Preethi Nair",
        expected_output="Attending: Dr. [NAME_REDACTED]",
        category="healthcare_names",
        expected_name_count=1,
    ),
    RedactionTestCase(
        name="no_fp_clinical_terms",
        input_text="Medical history includes hypertension and diabetes.",
        expected_output="Medical history includes hypertension and diabetes.",
        category="healthcare_names",
        expected_name_count=0,
        notes="Clinical terms must not be redacted",
    ),
    RedactionTestCase(
        name="uppercase_patient_name",
        input_text="Patient JOHN SMITH was admitted.",
        expected_output="Patient [NAME_REDACTED] was admitted.",
        category="healthcare_names",
        expected_name_count=1,
        notes="Uppercase chart headers should still redact names",
    ),
    RedactionTestCase(
        name="no_fp_department_to",
        input_text="Send to Cardiology for review.",
        expected_output="Send to Cardiology for review.",
        category="healthcare_names",
        expected_name_count=0,
        notes="Generic 'to' should not trigger name redaction",
    ),
    RedactionTestCase(
        name="no_fp_hospital_name",
        input_text="Admitted to Apollo Hospital on Monday.",
        expected_output="Admitted to [FACILITY_REDACTED] on Monday.",
        category="healthcare_names",
        expected_name_count=0,
        notes="Hospitals are redacted by the facility recognizer",
    ),
]

# ---------------------------------------------------------------------------
# Regex test cases
# ---------------------------------------------------------------------------

REGEX_TEST_CASES: list[tuple[str, str, str]] = [
    # Existing
    ("email_simple", "Contact us: admin@hospital.org", "EMAIL"),
    ("email_dot", "john.doe@clinic.co.in", "EMAIL"),
    ("phone_us", "Call 415-555-0192", "PHONE"),
    ("phone_intl", "+91 98765 43210 ext", "PHONE"),
    ("ip_v4", "Server 192.168.1.100 is up", "IP"),
    ("mrn_colon", "MRN: 1234567", "MRN"),
    ("mrn_hash", "Medical Record Number #9988776", "MRN"),
    ("dob_slash", "DOB 12/05/1990", "DOB"),
    ("dob_month_name", "Born on January 3, 1985", "DOB"),
    ("dob_iso", "Date: 1990-07-22", "DOB"),
    ("address_street", "456 MG Road, Bangalore", "ADDRESS"),
    ("address_nagar", "12 Gandhi Nagar", "ADDRESS"),
    ("ssn_labeled", "SSN: 123-45-6789", "SSN"),
    ("ssn_unlabeled_dash", "Patient SSN is 123-45-6789", "SSN"),
    ("fax_labeled", "Fax: 415-555-0199", "FAX"),
    ("account_number", "Account Number: 123456789", "ACCOUNT"),
    ("health_plan_id", "Health Plan ID: HP1234567", "HEALTH_PLAN"),
    ("device_imei", "IMEI: 490154203237518", "DEVICE"),
    ("age_over_89", "Age 92 male", "AGE"),
    ("location_city", "City: Bangalore", "LOCATION"),
    ("location_zip", "ZIP: 560001", "LOCATION"),
    ("facility_hospital", "Admitted to Apollo Hospital", "FACILITY"),
    # URL (≥10 tests)
    ("url_https", "Visit https://hospital.com for info", "URL"),
    ("url_http", "See http://clinic.org/appointments", "URL"),
    ("url_www_bare", "Check www.healthrecords.net for details", "URL"),
    ("url_with_path", "Download from https://records.hospital.org/patient/reports", "URL"),
    ("url_with_query", "Track at https://portal.clinic.com/track?id=123&ref=abc", "URL"),
    ("url_subdomain", "Login at https://patient.myclinic.in/login", "URL"),
    ("url_ip_based", "API at http://10.0.0.1:8080/api/v1", "URL"),
    ("url_with_port", "Connect to https://backend.hospital.com:443/data", "URL"),
    ("url_www_with_path", "Go to www.apollo.com/doctors/cardiology", "URL"),
    ("url_mixed_case", "Visit HTTPS://Hospital.COM/Info", "URL"),
    # VIN (≥10 tests)
    ("vin_standard", "Vehicle VIN: 1HGCM82633A004352", "VIN"),
    ("vin_ford", "VIN 1FTFW1ET5DFC10312 registered", "VIN"),
    ("vin_toyota", "Insured vehicle 4T1BF3EK8AU561234", "VIN"),
    ("vin_bmw", "BMW VIN WBAFW51000P987654", "VIN"),
    ("vin_mercedes", "Mercedes WDB2220161A987654", "VIN"),
    ("vin_honda", "Honda VIN 2HGFG12609H501234", "VIN"),
    ("vin_in_sentence", "Patient owns car 1G1ZT52806F109650 which was towed.", "VIN"),
    ("vin_end_of_line", "Ambulance VIN: 3VWFE21C04M000001", "VIN"),
    ("vin_hyundai", "Hyundai KMHCT4AE0GU123456", "VIN"),
    ("vin_nissan", "Nissan 1N4AL3AP6EC123456 insured", "VIN"),
    # License (≥10 tests)
    ("license_dl_prefix", "DL1234567 is the patient's driving licence.", "LICENSE"),
    ("license_lic_prefix", "LIC987654321 was verified.", "LICENSE"),
    ("license_tn_format", "TN0120230001234 issued by RTO.", "LICENSE"),
    ("license_mh_format", "MH12AB1234 vehicle registration.", "LICENSE"),
    ("license_full_word", "License Number: DL9876543210", "LICENSE"),
    ("license_ln_prefix", "LN-AB123456 on file.", "LICENSE"),
    ("license_driving_full", "Driving License No. DL456789012 verified.", "LICENSE"),
    ("license_ka_format", "KA0320210045678 renewed.", "LICENSE"),
    ("license_ap_format", "AP2820220056789 registered in Andhra.", "LICENSE"),
    ("license_lic_number", "LICENSE NUMBER: LIC00234567", "LICENSE"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def redact_markers_in(text: str) -> list[str]:
    return re.findall(r"\[(?:[A-Z_]+REDACTED|[A-Z][A-Z_]*_\d{3})\]", text)


def expected_pseudonymized_output(expected: str) -> str:
    """Convert legacy test markers to deterministic pseudonym placeholders."""
    counters: Counter[str] = Counter()

    def replace_marker(match: re.Match[str]) -> str:
        entity_type = match.group(1)
        counters[entity_type] += 1
        return f"[{entity_type}_{counters[entity_type]:03d}]"

    return re.sub(r"\[([A-Z_]+)_REDACTED\]", replace_marker, expected)


def compare_redaction(actual: str, expected: str) -> EvalResult:
    actual_markers = Counter(redact_markers_in(actual))
    expected_markers = Counter(redact_markers_in(expected))
    tp = sum(min(actual_markers[key], expected_markers[key]) for key in expected_markers)
    fp = sum(actual_markers.values()) - tp
    fn = sum(expected_markers.values()) - tp
    return EvalResult(tp=tp, fp=max(fp, 0), fn=max(fn, 0))


def redact_for_evaluation(text: str) -> tuple[str, int]:
    structured_text, _counts = _apply_structured_redactions(text)
    return redact_names(structured_text)


# ---------------------------------------------------------------------------
# Test runners
# ---------------------------------------------------------------------------

def run_name_tests() -> EvalResult:
    print("\n" + "=" * 72)
    print("NAME REDACTION TESTS")
    print("=" * 72)

    if not MODULES_AVAILABLE:
        print(f"Modules unavailable: {IMPORT_ERROR}")
        return EvalResult()

    total = EvalResult()
    for case in NAME_TEST_CASES:
        if case.expected_output == "VALIDATION_ERROR":
            try:
                TextInput(text=case.input_text)
                print(f"  [{case.category:<18}] {case.name:<38} {FAIL} expected validation error")
                total.fn += 1
            except Exception:
                print(f"  [{case.category:<18}] {case.name:<38} {PASS}")
            continue

        try:
            actual_text, name_count = redact_for_evaluation(case.input_text)
            expected_output = expected_pseudonymized_output(case.expected_output)
            result = compare_redaction(actual_text, expected_output)
            total += result

            passed = actual_text == expected_output
            if case.expected_name_count is not None and name_count != case.expected_name_count:
                passed = False

            status = PASS if passed else FAIL
            print(f"  [{case.category:<18}] {case.name:<38} {status}")
            if not passed:
                print(f"      input:    {case.input_text}")
                print(f"      expected: {expected_output}")
                print(f"      actual:   {actual_text}")
                if case.expected_name_count is not None:
                    print(f"      expected names: {case.expected_name_count}, actual names: {name_count}")
        except Exception as exc:
            print(f"  [{case.category:<18}] {case.name:<38} {FAIL} error: {exc}")
            total.fn += 1

    return total


def run_regex_tests() -> EvalResult:
    print("\n" + "=" * 72)
    print("REGEX ENTITY DETECTION TESTS")
    print("=" * 72)

    if not MODULES_AVAILABLE:
        print(f"Modules unavailable: {IMPORT_ERROR}")
        return EvalResult()

    pattern_map = {
        "ACCOUNT": ACCOUNT_PATTERN,
        "EMAIL": EMAIL_PATTERN,
        "AGE": AGE_PATTERN,
        "DEVICE": DEVICE_PATTERN,
        "FACILITY": FACILITY_PATTERN,
        "FAX": FAX_PATTERN,
        "HEALTH_PLAN": HEALTH_PLAN_PATTERN,
        "PHONE": PHONE_PATTERN,
        "IP": IP_PATTERN,
        "MRN": MRN_PATTERN,
        "DOB": DOB_PATTERN,
        "ADDRESS": ADDRESS_PATTERN,
        "LOCATION": LOCATION_PATTERN,
        "SSN": SSN_PATTERN,
        "URL": URL_PATTERN,
        "VIN": VIN_PATTERN,
        "LICENSE": LICENSE_PATTERN,
    }

    total = EvalResult()
    for test_name, text, label in REGEX_TEST_CASES:
        pattern = pattern_map[label]
        matches = [match.group(0) for match in pattern.finditer(text)]
        found = bool(matches)
        status = PASS if found else FAIL
        if found:
            total.tp += 1
        else:
            total.fn += 1
        sample = repr(matches[0]) if matches else "(no match)"
        print(f"  [{label:<8}] {test_name:<36} {status} {sample}")

    return total


def run_entity_merge_tests() -> EvalResult:
    print("\n" + "=" * 72)
    print("ENTITY MERGE UNIT TESTS")
    print("=" * 72)

    if not MODULES_AVAILABLE:
        print(f"Modules unavailable: {IMPORT_ERROR}")
        return EvalResult()

    total = EvalResult()

    # merge_title_chain
    text = "DR.Ashwin Kumar"
    entities = [
        NameEntity(text="DR", start=0, end=2, score=0.91, source="test"),
        NameEntity(text="Ashwin", start=3, end=9, score=0.95, source="test"),
        NameEntity(text="Kumar", start=10, end=15, score=0.93, source="test"),
    ]
    merged = _merge_adjacent(text, entities)
    processed = _post_process(text, entities)
    try:
        assert len(merged) == 1
        assert merged[0].start == 0 and merged[0].end == 15
        assert len(processed) == 1
        assert processed[0].start == 3 and processed[0].end == 15
        assert build_redacted_text(text, processed) == "DR.[NAME_REDACTED]"
        print("  merge_title_chain                          PASS")
        total.tp += 1
    except AssertionError:
        print("  merge_title_chain                          FAIL")
        print(f"      merged:    {merged}")
        print(f"      processed: {processed}")
        total.fn += 1

    # redact_two_titled_names
    text2 = "Mr. Ravi and Dr. Priya"
    entities2 = [
        NameEntity(text="Ravi", start=4, end=8, score=0.96, source="test"),
        NameEntity(text="Priya", start=17, end=22, score=0.97, source="test"),
    ]
    output = build_redacted_text(text2, entities2)
    if output == "Mr. [NAME_REDACTED] and Dr. [NAME_REDACTED]":
        print("  redact_two_titled_names                    PASS")
        total.tp += 1
    else:
        print("  redact_two_titled_names                    FAIL")
        print(f"      actual: {output}")
        total.fn += 1

    # public_detector_contract
    detected = detect_names_transformer("Dr.Ashwin spoke with Patient Arun.")
    if len(detected) >= 2:
        print("  public_detector_contract                   PASS")
        total.tp += 1
    else:
        print("  public_detector_contract                   FAIL")
        print(f"      detected: {detected}")
        total.fn += 1

    # patient_title_detection
    detected2 = detect_names_transformer("Patient Robert Brown was admitted.")
    names = [d["name"] for d in detected2]
    if any("Robert" in n or "Brown" in n for n in names):
        print("  patient_title_detection                    PASS")
        total.tp += 1
    else:
        print("  patient_title_detection                    FAIL")
        print(f"      detected: {detected2}")
        total.fn += 1

    return total


def run_structured_redaction_integration_tests() -> EvalResult:
    """Integration tests for full structured redaction pipeline ordering."""
    print("\n" + "=" * 72)
    print("STRUCTURED REDACTION INTEGRATION TESTS")
    print("=" * 72)

    if not MODULES_AVAILABLE:
        print(f"Modules unavailable: {IMPORT_ERROR}")
        return EvalResult()

    cases: list[tuple[str, str, str]] = [
        # (label, input, expected_token)
        ("URL_https", "Patient portal: https://myhealth.hospital.com/login", "[URL_REDACTED]"),
        ("URL_www", "See www.clinic.org for directions.", "[URL_REDACTED]"),
        ("URL_http_path", "Referral form at http://forms.nhs.gov/referral/submit", "[URL_REDACTED]"),
        ("URL_query_string", "API call https://api.hospital.com/v1/records?id=99", "[URL_REDACTED]"),
        ("URL_mixed_case", "Visit HTTPS://Hospital.COM", "[URL_REDACTED]"),
        ("SSN_labeled", "SSN: 123-45-6789", "[SSN_REDACTED]"),
        ("MRN_not_phone", "MRN: 1234567", "[MRN_REDACTED]"),
        ("ACCOUNT_not_phone", "Account Number: 123456789", "[ACCOUNT_REDACTED]"),
        ("HEALTH_PLAN", "Health Plan ID: HP1234567", "[HEALTH_PLAN_REDACTED]"),
        ("DEVICE_IMEI", "IMEI: 490154203237518", "[DEVICE_REDACTED]"),
        ("FAX_labeled", "Fax: 415-555-0199", "[FAX_REDACTED]"),
        ("AGE_over_89", "Age 92 male", "[AGE_REDACTED]"),
        ("LOCATION_zip", "ZIP: 560001", "[LOCATION_REDACTED]"),
        ("FACILITY_hospital", "Admitted to Apollo Hospital", "[FACILITY_REDACTED]"),
        ("PHONE_india", "+91 98765 43210 ext", "[PHONE_REDACTED]"),
        ("VIN_in_note", "Ambulance VIN 1HGCM82633A004352 was logged.", "[VIN_REDACTED]"),
        ("VIN_mid_sentence", "Insured vehicle 4T1BF3EK8AU561234 involved in accident.", "[VIN_REDACTED]"),
        ("VIN_end", "Patient transported via 2HGFG12609H501234", "[VIN_REDACTED]"),
        ("LICENSE_dl", "ID verified: DL1234567", "[LICENSE_REDACTED]"),
        ("LICENSE_lic", "LIC987654321 on file.", "[LICENSE_REDACTED]"),
        ("LICENSE_state_format", "TN0120230001234 driving licence.", "[LICENSE_REDACTED]"),
        ("LICENSE_full_label", "Driving License No. DL456789012", "[LICENSE_REDACTED]"),
    ]

    total = EvalResult()
    for label, input_text, expected_token in cases:
        try:
            redacted, _counts = _apply_structured_redactions(input_text)
            expected_token = expected_pseudonymized_output(expected_token)
            found = expected_token in redacted
            status = PASS if found else FAIL
            if found:
                total.tp += 1
            else:
                total.fn += 1
            print(f"  [{label:<26}] {status}")
            if not found:
                print(f"      input:   {input_text}")
                print(f"      output:  {redacted}")
        except Exception as exc:
            print(f"  [{label:<26}] FAIL error: {exc}")
            total.fn += 1

    return total


def run_pseudonymization_api_tests() -> EvalResult:
    """API tests for reversible pseudonymization and session handling."""
    print("\n" + "=" * 72)
    print("REVERSIBLE PSEUDONYMIZATION API TESTS")
    print("=" * 72)

    if not MODULES_AVAILABLE:
        print(f"Modules unavailable: {IMPORT_ERROR}")
        return EvalResult()

    client = TestClient(app)
    total = EvalResult()

    def check(label: str, condition: bool, detail: str = "") -> None:
        status = PASS if condition else FAIL
        print(f"  {label:<42} {status}")
        if condition:
            total.tp += 1
        else:
            total.fn += 1
            if detail:
                print(f"      {detail}")

    input_text = (
        "Patient John Smith was admitted. Patient John Smith returned. "
        "Dr. Jane Doe reviewed the case. "
        "Phone: +91 98765 43210. Alternate phone: 415-555-0192. "
        "Email: john@example.com; Backup email: jane@example.org"
    )

    session_id = ""
    try:
        redact_response = client.post("/redact", json={"text": input_text})
        check("redact endpoint status", redact_response.status_code == 200, redact_response.text)
        if redact_response.status_code != 200:
            return total

        payload = redact_response.json()
        session_id = payload.get("session_id", "")
        redacted_text = payload.get("redacted_text", "")

        try:
            UUID(session_id)
            valid_uuid = True
        except ValueError:
            valid_uuid = False

        check("session id is random UUID format", valid_uuid, repr(session_id))
        check("mappings are not returned", "mapping" not in payload and "mappings" not in payload)
        check("multiple names get per-type counters", "[NAME_001]" in redacted_text and "[NAME_002]" in redacted_text, redacted_text)
        check("duplicate names reuse placeholder", redacted_text.count("[NAME_001]") == 2, redacted_text)
        check("multiple phones get phone counters", "[PHONE_001]" in redacted_text and "[PHONE_002]" in redacted_text, redacted_text)
        check("multiple emails get email counters", "[EMAIL_001]" in redacted_text and "[EMAIL_002]" in redacted_text, redacted_text)
        check("entity counts preserved", payload.get("names_found") == 3 and payload.get("phones_found") == 2 and payload.get("emails_found") == 2, str(payload))

        restore_response = client.post(
            "/restore",
            json={"session_id": session_id, "text": redacted_text},
        )
        check("restore endpoint status", restore_response.status_code == 200, restore_response.text)
        if restore_response.status_code == 200:
            restored_text = restore_response.json().get("text")
            check("restore endpoint reconstructs text", restored_text == input_text, repr(restored_text))

        invalid_response = client.post(
            "/restore",
            json={"session_id": str(uuid4()), "text": "Patient [NAME_001]"},
        )
        check("invalid session returns 404", invalid_response.status_code == 404, invalid_response.text)

        expired_session_id = create_session(ttl_seconds=0.05)
        store_mapping(expired_session_id, "NAME_001", "Expired Patient")
        time.sleep(0.06)
        expired_response = client.post(
            "/restore",
            json={"session_id": expired_session_id, "text": "Patient [NAME_001]"},
        )
        check("expired session returns 404", expired_response.status_code == 404, expired_response.text)
    except Exception as exc:
        print(f"  pseudonymization_api_tests              {FAIL} error: {exc}")
        total.fn += 1
    finally:
        if session_id:
            delete_session(session_id)

    return total


def print_summary(
    name_result: EvalResult,
    regex_result: EvalResult,
    merge_result: EvalResult,
    integration_result: EvalResult,
    pseudonymization_result: EvalResult,
) -> None:
    combined = (
        name_result
        + regex_result
        + merge_result
        + integration_result
        + pseudonymization_result
    )
    print("\n" + "=" * 72)
    print("OVERALL EVALUATION SUMMARY")
    print("=" * 72)
    print(f"  {'Category':<28} {'TP':>4} {'FP':>4} {'FN':>4} {'Prec':>7} {'Rec':>7} {'F1':>7}")
    print(f"  {'-' * 66}")
    for label, result in (
        ("Name Redaction", name_result),
        ("Regex Detection", regex_result),
        ("Merge Helpers", merge_result),
        ("Integration", integration_result),
        ("Pseudonymization API", pseudonymization_result),
        ("Combined", combined),
    ):
        print(
            f"  {label:<28} {result.tp:>4} {result.fp:>4} {result.fn:>4}"
            f" {result.precision:>7.1%} {result.recall:>7.1%} {result.f1:>7.1%}"
        )

    if combined.f1 >= 0.90:
        verdict = "PRODUCTION-LEANING FOR THE COVERED TEST SET"
    elif combined.f1 >= 0.75:
        verdict = "NEEDS MORE ACCURACY WORK"
    else:
        verdict = "NOT READY"
    print(f"\n  Verdict: {verdict}\n")


if __name__ == "__main__":
    name_result = run_name_tests()
    regex_result = run_regex_tests()
    merge_result = run_entity_merge_tests()
    integration_result = run_structured_redaction_integration_tests()
    pseudonymization_result = run_pseudonymization_api_tests()
    print_summary(
        name_result,
        regex_result,
        merge_result,
        integration_result,
        pseudonymization_result,
    )
