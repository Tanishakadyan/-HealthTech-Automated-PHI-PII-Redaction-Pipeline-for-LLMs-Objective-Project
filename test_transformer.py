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
from collections import Counter
from dataclasses import dataclass


try:
    from backend.main import (
        ADDRESS_PATTERN,
        DOB_PATTERN,
        EMAIL_PATTERN,
        IP_PATTERN,
        LICENSE_PATTERN,
        MRN_PATTERN,
        PHONE_PATTERN,
        URL_PATTERN,
        VIN_PATTERN,
        TextInput,
        _apply_structured_redactions,
        redact_names,
    )
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
        name="no_fp_hospital_name",
        input_text="Admitted to Apollo Hospital on Monday.",
        expected_output="Admitted to Apollo Hospital on Monday.",
        category="healthcare_names",
        expected_name_count=0,
        notes="Org names — FP risk; hospital is in stopwords",
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
    return re.findall(r"\[[A-Z_]+REDACTED\]", text)


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
            result = compare_redaction(actual_text, case.expected_output)
            total += result

            passed = actual_text == case.expected_output
            if case.expected_name_count is not None and name_count != case.expected_name_count:
                passed = False

            status = PASS if passed else FAIL
            print(f"  [{case.category:<18}] {case.name:<38} {status}")
            if not passed:
                print(f"      input:    {case.input_text}")
                print(f"      expected: {case.expected_output}")
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
        "EMAIL": EMAIL_PATTERN,
        "PHONE": PHONE_PATTERN,
        "IP": IP_PATTERN,
        "MRN": MRN_PATTERN,
        "DOB": DOB_PATTERN,
        "ADDRESS": ADDRESS_PATTERN,
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
    """Integration tests for URL, VIN, License via full structured redaction pipeline."""
    print("\n" + "=" * 72)
    print("STRUCTURED REDACTION INTEGRATION TESTS (URL / VIN / LICENSE)")
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


def print_summary(
    name_result: EvalResult,
    regex_result: EvalResult,
    merge_result: EvalResult,
    integration_result: EvalResult,
) -> None:
    combined = name_result + regex_result + merge_result + integration_result
    print("\n" + "=" * 72)
    print("OVERALL EVALUATION SUMMARY")
    print("=" * 72)
    print(f"  {'Category':<28} {'TP':>4} {'FP':>4} {'FN':>4} {'Prec':>7} {'Rec':>7} {'F1':>7}")
    print(f"  {'-' * 66}")
    for label, result in (
        ("Name Redaction", name_result),
        ("Regex Detection", regex_result),
        ("Merge Helpers", merge_result),
        ("Integration (URL/VIN/LIC)", integration_result),
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
    print_summary(name_result, regex_result, merge_result, integration_result)