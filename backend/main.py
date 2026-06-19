from __future__ import annotations

import html
import logging
import os
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from presidio_analyzer import AnalyzerEngine
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from transformer_ner import (
    NAME_REDACTION_TOKEN,
    NameEntity,
    build_redacted_text,
    detect_name_entities,
    post_process_name_entities,
)


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = int(os.getenv("MAX_REDACTION_CHARS", "50000"))
PRESIDIO_PERSON_THRESHOLD = float(os.getenv("PRESIDIO_PERSON_THRESHOLD", "0.80"))

EMAIL_REDACTION_TOKEN = "[EMAIL_REDACTED]"
PHONE_REDACTION_TOKEN = "[PHONE_REDACTED]"
IP_REDACTION_TOKEN = "[IP_REDACTED]"
MRN_REDACTION_TOKEN = "[MRN_REDACTED]"
DOB_REDACTION_TOKEN = "[DOB_REDACTED]"
ADDRESS_REDACTION_TOKEN = "[ADDRESS_REDACTED]"


try:
    analyzer: AnalyzerEngine | None = AnalyzerEngine()
except Exception as exc:
    logger.warning("Presidio AnalyzerEngine unavailable; continuing without Presidio PERSON fallback: %s", exc)
    analyzer = None

limiter = Limiter(key_func=get_remote_address)


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOW_ORIGINS", "https://yourdomain.com")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(
    title="PHI/PII Redaction API",
    description="""
Healthcare PHI/PII Redaction Service.

Features:
- Name Redaction
- Email Redaction
- Phone Number Redaction
- IP Address Redaction
- MRN Redaction
- DOB Redaction
- Address Redaction
- Hybrid NER (Transformer + Presidio + Healthcare Rules)

This API detects and masks sensitive healthcare information before text is sent to external AI systems.
""",
    version="1.1.0",
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"},
    )


EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])"
)

PHONE_PATTERN = re.compile(
    r"""
    (?<!\w)
    (?:\+?\d{1,3}[\s.-]?)?
    (?:
        \(?\d{3}\)?[\s.-]?\d{3}[\s.-]\d{4}
        |
        \d{5}[\s.-]\d{5}
    )
    (?:\s*(?:x|ext\.?|extension)\s*\d{1,5})?
    (?!\w)
    """,
    re.VERBOSE,
)

IP_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
)

MRN_PATTERN = re.compile(
    r"""
    \b
    (?:
        M\.?R\.?N\.?
        | Medical\s+Record(?:\s+Number)?
        | Record\s*(?:No\.?|Number)
        | Patient\s*(?:ID|Identifier)
        | Hospital\s*ID
        | UHID
    )
    \s*[:#=-]?\s*
    [A-Z0-9][A-Z0-9-]{2,}
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

DOB_PATTERN = re.compile(
    r"""
    \b
    (?:
        \d{1,2}[/-]\d{1,2}[/-]\d{2,4}
        |
        \d{4}[/-]\d{1,2}[/-]\d{1,2}
        |
        (?:
            Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|
            Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|
            Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?
        )
        \s+\d{1,2},?\s+\d{4}
        |
        \d{1,2}\s+
        (?:
            Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|
            Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|
            Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?
        )
        \s+\d{4}
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

ADDRESS_PATTERN = re.compile(
    r"""
    \b
    \d{1,6}
    \s+
    (?:[A-Za-z0-9.'-]+\s+){0,6}
    (?:
        Street|St\.?|Road|Rd\.?|Avenue|Ave\.?|Lane|Ln\.?|Block|Blvd\.?|
        Drive|Dr\.?|Nagar|Colony|Layout|Cross|Main|Sector|Phase
    )
    (?:\s*,?\s*[A-Za-z][A-Za-z .'-]{1,40}){0,3}
    """,
    re.IGNORECASE | re.VERBOSE,
)

STRUCTURED_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("emails_found", EMAIL_PATTERN, EMAIL_REDACTION_TOKEN),
    ("phones_found", PHONE_PATTERN, PHONE_REDACTION_TOKEN),
    ("ips_found", IP_PATTERN, IP_REDACTION_TOKEN),
    ("mrns_found", MRN_PATTERN, MRN_REDACTION_TOKEN),
    ("dobs_found", DOB_PATTERN, DOB_REDACTION_TOKEN),
    ("addresses_found", ADDRESS_PATTERN, ADDRESS_REDACTION_TOKEN),
)


class TextInput(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="Input clinical text for PHI/PII redaction",
    )

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        value = html.unescape(value)
        value = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", "", value, flags=re.IGNORECASE)
        value = re.sub(r"<[^>]+>", "", value)
        value = value.replace("\x00", "")
        value = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", value)
        value = value.strip()
        if not value:
            raise ValueError("Text cannot be empty after sanitization")
        return value


class RedactionResponse(BaseModel):
    status: str
    redacted_text: str
    emails_found: int
    phones_found: int
    ips_found: int
    names_found: int
    mrns_found: int
    dobs_found: int
    addresses_found: int


def _count_matches(pattern: re.Pattern[str], text: str) -> int:
    return sum(1 for _ in pattern.finditer(text))


def _apply_structured_redactions(text: str) -> tuple[str, dict[str, int]]:
    counts = {
        key: _count_matches(pattern, text)
        for key, pattern, _replacement in STRUCTURED_PATTERNS
    }

    redacted_text = text
    for _key, pattern, replacement in STRUCTURED_PATTERNS:
        redacted_text = pattern.sub(replacement, redacted_text)

    return redacted_text, counts


def _presidio_person_entities(text: str) -> list[NameEntity]:
    if analyzer is None:
        return []

    results = analyzer.analyze(text=text, entities=["PERSON"], language="en")
    entities: list[NameEntity] = []

    for result in results:
        if result.score < PRESIDIO_PERSON_THRESHOLD:
            continue

        value = text[result.start : result.end]
        entities.append(
            NameEntity(
                text=value,
                start=result.start,
                end=result.end,
                score=float(result.score),
                source="presidio",
            )
        )

    return entities


def redact_names(text: str) -> tuple[str, int]:
    """
    Redact names using a true hybrid detector:
    transformer NER + title/context rules + Presidio PERSON entities.
    """
    candidates: list[NameEntity] = []
    candidates.extend(detect_name_entities(text))
    candidates.extend(_presidio_person_entities(text))

    final_entities = post_process_name_entities(text, candidates)
    if not final_entities:
        return text, 0

    return build_redacted_text(text, final_entities, replacement=NAME_REDACTION_TOKEN), len(final_entities)


@app.get("/")
@limiter.limit("30/minute")
def home(request: Request):
    """Health check endpoint."""
    return {"status": "ok", "message": "Backend Working"}


@app.get("/health")
@limiter.limit("30/minute")
def health(request: Request):
    """Machine-readable health endpoint for load balancers and monitoring."""
    return {"status": "healthy"}


@app.post("/redact", response_model=RedactionResponse)
@limiter.limit("10/minute")
def redact(request: Request, data: TextInput):
    """
    Detect and redact PHI/PII entities from clinical text.

    Redaction order:
    1. Structured PHI/PII: email, phone, IP, MRN, dates, addresses.
    2. Names: transformer NER + title/context rules + Presidio.
    """
    structured_text, counts = _apply_structured_redactions(data.text)
    redacted_text, name_count = redact_names(structured_text)

    return {
        "status": "success",
        "redacted_text": redacted_text,
        "emails_found": counts["emails_found"],
        "phones_found": counts["phones_found"],
        "ips_found": counts["ips_found"],
        "names_found": name_count,
        "mrns_found": counts["mrns_found"],
        "dobs_found": counts["dobs_found"],
        "addresses_found": counts["addresses_found"],
    }
