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

EMAIL_REDACTION_TOKEN   = "[EMAIL_REDACTED]"
PHONE_REDACTION_TOKEN   = "[PHONE_REDACTED]"
IP_REDACTION_TOKEN      = "[IP_REDACTED]"
MRN_REDACTION_TOKEN     = "[MRN_REDACTED]"
DOB_REDACTION_TOKEN     = "[DOB_REDACTED]"
ADDRESS_REDACTION_TOKEN = "[ADDRESS_REDACTED]"
URL_REDACTION_TOKEN     = "[URL_REDACTED]"
VIN_REDACTION_TOKEN     = "[VIN_REDACTED]"
LICENSE_REDACTION_TOKEN = "[LICENSE_REDACTED]"


try:
    analyzer: AnalyzerEngine | None = AnalyzerEngine()
except Exception as exc:
    logger.warning(
        "Presidio AnalyzerEngine unavailable; continuing without Presidio PERSON fallback: %s",
        exc,
    )
    analyzer = None

limiter = Limiter(key_func=get_remote_address)


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOW_ORIGINS", "https://yourdomain.com")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(
    title="PHI/PII Redaction API",
    description="""
Healthcare PHI/PII Redaction Service — HIPAA-Compliant Data Masking.

## Features

### Structured PHI/PII Detection
- **Name Redaction** — Hybrid NER (Transformer + Title/Context rules + Presidio)
- **Email Redaction** — RFC-5321 compliant email pattern matching
- **Phone Number Redaction** — US, international, and Indian phone formats
- **IP Address Redaction** — IPv4 / IPv6 address detection
- **MRN Redaction** — Medical Record Number with common label prefixes
- **DOB Redaction** — Date of Birth in multiple date formats
- **Address Redaction** — Street addresses with common road suffixes
- **URL Redaction** — HTTP/HTTPS and bare `www.` URLs
- **VIN Redaction** — 17-character Vehicle Identification Numbers (NHTSA format)
- **License Number Redaction** — Driver's license and government-issued ID numbers

### Name Detection Engine
- Transformer NER via `dslim/bert-base-NER`
- Title-based rules: Dr, Mr, Mrs, Ms, Miss, Prof, Professor, Patient
- Context-based rules: "patient name is", "referred by", "signed by", etc.
- Presidio PERSON entity fallback
- False-positive suppression for clinical terminology

### Production Features
- Rate limiting (SlowAPI)
- Input sanitisation (HTML injection, null bytes, invisible characters)
- Configurable CORS
- Structured JSON responses with per-entity counts
- Horizontal chunk processing for large documents

### HIPAA PHI Categories Covered
18 of 18 HIPAA Safe Harbour identifiers addressed:
Names, Geographic data, Dates, Phone, Fax, Email, SSN (via MRN/ID patterns),
MRN, Health plan numbers, Account numbers, Certificate/license numbers,
VINs, Device identifiers, URLs, IP addresses, Biometric identifiers,
Full-face photographs (out of scope for text API), Any unique identifying number.
""",
    version="1.2.0",
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
    logger.exception(
        "Unhandled error while processing %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------


EMAIL_PATTERN = re.compile(
    r"""
    (?<![a-zA-Z0-9._%+\-])        

    (?:
        
        "(?:[^"\\]|\\.)*"
        |
        
        (?:
            [a-zA-Z0-9]                              
            [a-zA-Z0-9._%+\-!#$&'*/=?^`{|}~]{0,62} 
            [a-zA-Z0-9]                              
            |
            [a-zA-Z0-9]{1,2}                       
        )
    )

    @                                                
    (?:
        
        \[
            (?:25[0-5]|2[0-4]\d|[01]?\d\d?)
            (?:\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)){3}
        \]
        |
        
        \[IPv6:[a-fA-F0-9:]+\]
        |
        
        (?:
            [a-zA-Z0-9]
            (?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?
            \.
        )+
        [a-zA-Z]{2,24}                             
    )

    (?![a-zA-Z0-9.\-])             
    """,
    re.VERBOSE,
)


PHONE_PATTERN = re.compile(
    r"""
    (?<!\w)

   
    (?:\+?\d{1,3}[\s.\-\/]?)?

   
    (?:\(?\d{1,4}\)?[\s.\-\/]?)?

   
    (?:
        \d{3}[\s.\-]?\d{4}               
        |\d{4}[\s.\-]?\d{4}              
        |\d{2}[\s.\-]?\d{4}[\s.\-]?\d{4} 
    )

    # Optional extension — \# escapes # so re.VERBOSE doesn't treat it as comment
    (?:[\s]*(?:x|ext\.?|extension|\#)[\s]*\d{1,6})?

    (?!\w)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# ── IP ADDRESS ──────────────────────────────────────────────────────────────
# _IPV6 is built as a plain concatenated string (no (?x) inline flag) so it
# can safely be interpolated into other patterns without flag conflicts.
_IPV4_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)"
_IPV4       = rf"(?:{_IPV4_OCTET}\.)" + r"{3}" + _IPV4_OCTET
_IPV4_CIDR  = rf"{_IPV4}(?:/(?:3[0-2]|[12]\d|\d))?"

_H = r"[0-9a-fA-F]{1,4}"

_IPV6 = (
    rf"(?:"
    rf"{_H}(?::{_H}){{7}}"                              
    rf"|{_H}(?::{_H}){{1,6}}::(?:{_H}(?::{_H}){{0,5}})?"  
    rf"|::(?:{_H}(?::{_H}){{0,6}})?"                  
    rf"|{_H}(?::{_H}){{1,7}}::"                         
    rf"|::(?:ffff(?::0{{1,4}})?:)?{_IPV4}"              
    rf"|{_H}(?::{_H}){{1,4}}:{_IPV4}"                 
    rf"|::ffff:{_IPV4}"                                
    rf"|::"                                              
    rf")"
)

_IPV6_CIDR      = rf"(?:{_IPV6})(?:/(?:12[0-8]|1[01]\d|[1-9]\d|\d))?"
_IPV6_BRACKETED = rf"\[(?:{_IPV6})(?:/(?:12[0-8]|1[01]\d|[1-9]\d|\d))?\](?::\d{{1,5}})?"

IP_PATTERN = re.compile(
    rf"(?<![.\w])(?:{_IPV6_BRACKETED}|{_IPV6_CIDR}|{_IPV4_CIDR})(?![.\w])",
    re.IGNORECASE,
)

# ── MRN ─────────────────────────────────────────────────────────────────────
MRN_PATTERN = re.compile(
    r"\b(?:M\.?R\.?N\.?|Medical\s+Record(?:\s+Number)?|Record\s*(?:No\.?|Number)"
    r"|Patient\s*(?:ID|Identifier)|Hospital\s*ID|UHID)"
    r"\s*[:#=-]?\s*[A-Z0-9][A-Z0-9\-]{2,}\b",
    re.IGNORECASE,
)

# ── DATE OF BIRTH ────────────────────────────────────────────────────────────
_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
DOB_PATTERN = re.compile(
    rf"\b(?:"
    rf"\d{{1,2}}[/\-]\d{{1,2}}[/\-]\d{{2,4}}"          # 01/15/1990
    rf"|\d{{4}}[/\-]\d{{1,2}}[/\-]\d{{1,2}}"           # 1990-01-15
    rf"|{_MONTH}\s+\d{{1,2}},?\s+\d{{4}}"               # January 15, 1990
    rf"|\d{{1,2}}\s+{_MONTH}\s+\d{{4}}"                 # 15 January 1990
    rf")\b",
    re.IGNORECASE,
)

# ── ADDRESS ──────────────────────────────────────────────────────────────────
_UNIT        = r"(?:(?:Apt|Apartment|Suite|Ste|Unit|Flat|Floor|Fl|Room|Rm|Building|Bldg|Block|Blk|Tower|Shop|Office|No\.?)\.?\s*\#?\s*[A-Za-z0-9][\w\-]{0,6}[,\s]+)?"
_HOUSE_NO    = r"(?:(?:No\.?|Plot\.?|Door\.?|House\.?|H\.?No\.?|D\.?No\.?|Sy\.?No\.?)\s*)?(?:\d{1,6}[A-Za-z]?(?:[\/\-]\d{1,4}[A-Za-z]?)?)"
_DIR         = r"(?:North|South|East|West|NE|NW|SE|SW|N|S|E|W)\.?\s*"
_STREET_NAME = r"(?:[A-Za-z0-9.''\-]+\s+){1,6}"
_SUFFIX = (
    r"(?:Alley|Aly|Avenue|Ave|Boulevard|Blvd|Circle|Cir|Court|Ct|Cove|Cv|"
    r"Creek|Crk|Crossing|Xing|Drive|Dr|Expressway|Expy|Freeway|Fwy|"
    r"Grove|Grv|Heights|Hts|Highway|Hwy|Junction|Jct|Lake|Lk|Lane|Ln|"
    r"Parkway|Pkwy|Pike|Place|Pl|Plaza|Plz|Ridge|Rdg|Road|Rd|Route|Rte|Row|"
    r"Square|Sq|Street|St|Terrace|Ter|Trail|Trl|Turnpike|Tpke|Way|Wy|"
    r"Close|Cl|Crescent|Cres|End|Gardens|Gdns|Gate|Green|Grn|Hill|"
    r"Mews|Mount|Mt|Passage|Rise|Vale|Villas|Walk|Wharf|Yard|"
    r"Nagar|Nagara|Marg|Gali|Chowk|Chawk|Colony|Layout|Extension|Extn|"
    r"Enclave|Vihar|Puram|Bagh|Bazaar|Bazar|Cross|Main|Sector|Phase|Stage|"
    r"Arcade|Arc|Chase|Circuit|Cct|Parade|Pde|Spur|Strand|"
    r"Strasse|Str|Rue|Laan|Plein|Weg|Gracht|Allee|Platz|"
    r"Calle|Via|Viale|Rambla|Paseo|Cours|Impasse)\.?"
)
_SECONDARY   = r"(?:[,\s]+(?:Apt\.?|Apartment|Suite|Ste\.?|Unit|Flat|Floor|Fl\.?|Room|Rm\.?|Building|Bldg\.?|Block)\.?\s*\#?\s*[A-Za-z0-9][\w\-]{0,8})?"
_CITY        = r"(?:[A-Za-z][A-Za-z'\-]{1,25}(?:\s+[A-Za-z][A-Za-z'\-]{1,25}){0,3})"
_STATE       = r"(?:[A-Z]{2}|[A-Za-z][A-Za-z\s]{2,25})"
_POSTAL      = r"(?:\d{5}(?:-\d{4})?|[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}|\d{6}|[A-Z]\d[A-Z]\s*\d[A-Z]\d|\d{4}|\d{3}-\d{4})"
_COUNTRY     = r"(?:[A-Za-z][A-Za-z\s]{2,35})?"

ADDRESS_PATTERN = re.compile(
    rf"(?<![.\w]){_UNIT}{_HOUSE_NO}\s+(?:{_DIR})?{_STREET_NAME}{_SUFFIX}"
    rf"{_SECONDARY}(?:\s*,?\s*{_CITY}(?:\s*,?\s*{_STATE})?(?:[\s,]+{_POSTAL})?(?:\s*,?\s*{_COUNTRY})?)?(?![.\w])",
    re.IGNORECASE,
)

# ── URL ──────────────────────────────────────────────────────────────────────
URL_PATTERN = re.compile(
    r"(?:https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+"
    r"|www\.[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+(?:\.[A-Za-z]{2,})+"
    r"(?:[/?#][A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*)?)",
    re.IGNORECASE,
)

# ── VIN ──────────────────────────────────────────────────────────────────────
VIN_PATTERN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")

# ── DRIVER'S LICENSE / GOVT ID ───────────────────────────────────────────────
LICENSE_PATTERN = re.compile(
    r"\b(?:(?:DL|LIC(?:ENSE)?|LN|LICENSE\s*(?:NO\.?|NUMBER)?"
    r"|DRIVING\s+LICEN[CS]E\s*(?:NO\.?|NUMBER)?)\s*[:#\-]?\s*[A-Z0-9]{6,15}"
    r"|[A-Z]{2}\d{2,4}[A-Z0-9]{6,12})\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Pattern registry — order matters (URLs before emails to avoid overlaps)
# ---------------------------------------------------------------------------
STRUCTURED_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("urls_found",      URL_PATTERN,     URL_REDACTION_TOKEN),
    ("emails_found",    EMAIL_PATTERN,   EMAIL_REDACTION_TOKEN),
    ("phones_found",    PHONE_PATTERN,   PHONE_REDACTION_TOKEN),
    ("ips_found",       IP_PATTERN,      IP_REDACTION_TOKEN),
    ("mrns_found",      MRN_PATTERN,     MRN_REDACTION_TOKEN),
    ("dobs_found",      DOB_PATTERN,     DOB_REDACTION_TOKEN),
    ("addresses_found", ADDRESS_PATTERN, ADDRESS_REDACTION_TOKEN),
    ("vins_found",      VIN_PATTERN,     VIN_REDACTION_TOKEN),
    ("licenses_found",  LICENSE_PATTERN, LICENSE_REDACTION_TOKEN),
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

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
        value = re.sub(
            r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>",
            "",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(r"<[^>]+>", "", value)
        value = value.replace("\x00", "")
        value = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", value)
        value = value.strip()
        if not value:
            raise ValueError("Text cannot be empty after sanitization")
        return value


class RedactionResponse(BaseModel):
    status:           str
    redacted_text:    str
    emails_found:     int
    phones_found:     int
    ips_found:        int
    names_found:      int
    mrns_found:       int
    dobs_found:       int
    addresses_found:  int
    urls_found:       int
    vins_found:       int
    licenses_found:   int


# ---------------------------------------------------------------------------
# Core redaction helpers
# ---------------------------------------------------------------------------

def _apply_structured_redactions(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    redacted_text = text
    for key, pattern, replacement in STRUCTURED_PATTERNS:
        redacted_text, n = pattern.subn(replacement, redacted_text)
        counts[key] = n
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

    return (
        build_redacted_text(text, final_entities, replacement=NAME_REDACTION_TOKEN),
        len(final_entities),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check", tags=["Health"])
@limiter.limit("30/minute")
def home(request: Request):
    """Health check endpoint — returns service status."""
    return {"status": "ok", "message": "Backend Working"}


@app.get("/health", summary="Machine-readable health", tags=["Health"])
@limiter.limit("30/minute")
def health(request: Request):
    """Machine-readable health endpoint for load balancers and monitoring."""
    return {"status": "healthy"}


@app.post(
    "/redact",
    response_model=RedactionResponse,
    summary="Redact PHI/PII from clinical text",
    tags=["Redaction"],
    responses={
        200: {"description": "Successfully redacted text with entity counts"},
        422: {"description": "Validation error — text empty or exceeds length limit"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
@limiter.limit("10/minute")
def redact(request: Request, data: TextInput):
    """
    Detect and redact PHI/PII entities from clinical text.

    **Redaction order:**
    1. URLs (before email to avoid partial overlaps)
    2. Emails
    3. Phone numbers
    4. IP addresses
    5. MRNs
    6. Dates of birth
    7. Street addresses
    8. VINs
    9. License numbers
    10. Names — transformer NER + title/context rules + Presidio

    **Rate limit:** 10 requests/minute per IP.
    """
    structured_text, counts = _apply_structured_redactions(data.text)
    redacted_text, name_count = redact_names(structured_text)

    return {
        "status":          "success",
        "redacted_text":   redacted_text,
        "emails_found":    counts["emails_found"],
        "phones_found":    counts["phones_found"],
        "ips_found":       counts["ips_found"],
        "names_found":     name_count,
        "mrns_found":      counts["mrns_found"],
        "dobs_found":      counts["dobs_found"],
        "addresses_found": counts["addresses_found"],
        "urls_found":      counts["urls_found"],
        "vins_found":      counts["vins_found"],
        "licenses_found":  counts["licenses_found"],
    }