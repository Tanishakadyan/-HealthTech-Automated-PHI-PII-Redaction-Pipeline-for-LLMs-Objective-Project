from __future__ import annotations

from backend.main import (
    Pseudonymizer,
    _apply_structured_redactions,
    redact_names,
    restore_pseudonymized_text,
)
from backend.mapping_store import create_session, delete_session, get_mapping


SAMPLE_TEXT = (
    "Patient JOHN SMITH visited Dr. Arun Raj at Apollo Hospital. "
    "MRN: 1234567. Phone: +91 98765 43210. SSN: 123-45-6789."
)


if __name__ == "__main__":
    session_id = create_session()
    pseudonymizer = Pseudonymizer(session_id=session_id)

    try:
        structured_text, counts = _apply_structured_redactions(
            SAMPLE_TEXT,
            pseudonymizer=pseudonymizer,
        )
        redacted_text, names_found = redact_names(
            structured_text,
            pseudonymizer=pseudonymizer,
        )
        restored_text = restore_pseudonymized_text(redacted_text, get_mapping(session_id) or {})

        print(session_id)
        print(redacted_text)
        print(restored_text)
        print({**counts, "names_found": names_found})
    finally:
        delete_session(session_id)
