from __future__ import annotations

from backend.main import _apply_structured_redactions, redact_names


SAMPLE_TEXT = (
    "Patient JOHN SMITH visited Dr. Arun Raj at Apollo Hospital. "
    "MRN: 1234567. Phone: +91 98765 43210. SSN: 123-45-6789."
)


if __name__ == "__main__":
    structured_text, counts = _apply_structured_redactions(SAMPLE_TEXT)
    redacted_text, names_found = redact_names(structured_text)

    print(redacted_text)
    print({**counts, "names_found": names_found})
