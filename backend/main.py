from __future__ import annotations

import html
import logging
import os
import re
import secrets
from collections import defaultdict
from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

try:
    from .mapping_store import create_session, delete_session, get_mapping, store_mapping
except ImportError:  # pragma: no cover - supports direct script execution.
    from mapping_store import create_session, delete_session, get_mapping, store_mapping

from transformer_ner import (
    NameEntity,
    detect_name_entities,
    post_process_name_entities,
)


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        logger.warning("Invalid %s=%r; using %s", name, raw_value, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        logger.warning("Invalid %s=%r; using %s", name, raw_value, default)
        return default


MAX_TEXT_LENGTH = _env_int("MAX_REDACTION_CHARS", 50000)
PRESIDIO_PERSON_THRESHOLD = _env_float("PRESIDIO_PERSON_THRESHOLD", 0.80)
PRESIDIO_LANGUAGE = os.getenv("PRESIDIO_LANGUAGE", "en").strip() or "en"
PRESIDIO_SPACY_MODEL = os.getenv("PRESIDIO_SPACY_MODEL", "").strip()
REDACTION_API_KEY = os.getenv("REDACTION_API_KEY", "").strip()

EMAIL_REDACTION_TOKEN = "[EMAIL_REDACTED]"
PHONE_REDACTION_TOKEN = "[PHONE_REDACTED]"
FAX_REDACTION_TOKEN = "[FAX_REDACTED]"
IP_REDACTION_TOKEN = "[IP_REDACTED]"
MRN_REDACTION_TOKEN = "[MRN_REDACTED]"
DOB_REDACTION_TOKEN = "[DOB_REDACTED]"
AGE_REDACTION_TOKEN = "[AGE_REDACTED]"
ADDRESS_REDACTION_TOKEN = "[ADDRESS_REDACTED]"
LOCATION_REDACTION_TOKEN = "[LOCATION_REDACTED]"
FACILITY_REDACTION_TOKEN = "[FACILITY_REDACTED]"
URL_REDACTION_TOKEN = "[URL_REDACTED]"
SSN_REDACTION_TOKEN = "[SSN_REDACTED]"
ACCOUNT_REDACTION_TOKEN = "[ACCOUNT_REDACTED]"
HEALTH_PLAN_REDACTION_TOKEN = "[HEALTH_PLAN_REDACTED]"
DEVICE_REDACTION_TOKEN = "[DEVICE_REDACTED]"
VIN_REDACTION_TOKEN = "[VIN_REDACTED]"
LICENSE_REDACTION_TOKEN = "[LICENSE_REDACTED]"

limiter = Limiter(key_func=get_remote_address)


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOW_ORIGINS", "https://yourdomain.com")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(
    title="PHI/PII Pseudonymization API",
    description="""
Healthcare PHI/PII Redaction Service for HIPAA de-identification workflows.
Deployment compliance still requires access controls, audit controls,
encryption, retention policy, and vendor/business-associate controls.

## Features

### Structured PHI/PII Detection
- **Name Redaction** — Hybrid NER (Transformer + Title/Context rules + Presidio)
- **Email Redaction** — RFC-5321 compliant email pattern matching
- **Phone Number Redaction** — US, international, and Indian phone formats
- **Fax Redaction** — fax labels plus phone-number formats
- **IP Address Redaction** — IPv4 / IPv6 address detection
- **MRN Redaction** — Medical Record Number with common label prefixes
- **SSN / Account / Health Plan / Device ID Redaction** — labeled identifiers
- **Date and Age Redaction** — full dates and ages over 89
- **Address Redaction** — Street addresses with common road suffixes
- **Location and Facility Redaction** — labeled geographic values and hospitals/clinics
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
- Optional API-key enforcement via `REDACTION_API_KEY`
- No-store response headers
- Input sanitisation (HTML injection, null bytes, invisible characters)
- Configurable CORS
- Structured JSON responses with per-entity counts
- Horizontal chunk processing for large documents

### HIPAA PHI Categories Covered
Text identifiers addressed include names, geographic data, dates, ages over 89,
phone, fax, email, SSN, MRN, health plan numbers, account numbers,
certificate/license numbers, VINs, device identifiers, URLs, IP addresses,
facilities, and other labeled unique identifiers. Biometric identifiers and
full-face photographs are out of scope for this text API.
""",
    version="1.4.0",
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
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


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("Pragma", "no-cache")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if not REDACTION_API_KEY:
        return

    provided_keys = (x_api_key or "", _bearer_token(authorization))
    if not any(
        secrets.compare_digest(provided, REDACTION_API_KEY)
        for provided in provided_keys
        if provided
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
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


_PHONE_NUMBER = r"""
    (?:
        \+\d{10,15}
        |
        (?:\+?\d{1,3}[\s.\-/]+)?
        (?:
            \(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}
            |\d{5}[\s.\-]\d{5}
            |\d{2}[\s.\-]\d{4}[\s.\-]\d{4}
            |\d{4}[\s.\-]\d{4}
            |\d{3}[\s.\-]\d{4}
            |\d{10,15}
        )
    )
"""
_PHONE_EXTENSION = r"(?:\s*(?:x|ext\.?|extension|\#)\s*\d{1,6})?"

PHONE_PATTERN = re.compile(
    rf"(?<![\w]){_PHONE_NUMBER}{_PHONE_EXTENSION}(?![\w])",
    re.VERBOSE | re.IGNORECASE,
)

FAX_PATTERN = re.compile(
    rf"""
    \b(?:fax|facsimile)(?:\s*(?:no\.?|number))?\s*[:#=-]?\s*
    {_PHONE_NUMBER}{_PHONE_EXTENSION}
    (?![\w])
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

# ── LABELED IDENTIFIERS ──────────────────────────────────────────────────────
_IDENTIFIER_VALUE = (
    r"(?=[A-Z0-9][A-Z0-9\-]{2,31}\b)(?=[A-Z0-9\-]*\d)"
    r"[A-Z0-9][A-Z0-9\-]{2,31}"
)
_LICENSE_VALUE = (
    r"(?=[A-Z0-9][A-Z0-9\-]{4,19}\b)(?=[A-Z0-9\-]*\d)"
    r"[A-Z0-9][A-Z0-9\-]{4,19}"
)

SSN_PATTERN = re.compile(
    r"""
    \b(?:
        (?:S\.?S\.?N\.?|Social\s+Security(?:\s+Number)?)\s*[:#=-]?\s*
        (?:\d{3}-\d{2}-\d{4}|\d{9})
        |
        \d{3}-\d{2}-\d{4}
    )\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

MRN_PATTERN = re.compile(
    rf"""
    \b(?:M\.?R\.?N\.?|Medical\s+Record(?:\s+Number)?|Record\s*(?:No\.?|Number)
    |Patient\s*(?:ID|Identifier)|Hospital\s*ID|UHID)
    \s*[:#=-]?\s*{_IDENTIFIER_VALUE}\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

ACCOUNT_PATTERN = re.compile(
    rf"""
    \b(?:Account\s*(?:No\.?|Number|\#)?|Acct\.?)
    \s*[:#=-]?\s*{_IDENTIFIER_VALUE}\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

HEALTH_PLAN_PATTERN = re.compile(
    rf"""
    \b(?:
        Health(?:care)?\s*Plan\s*(?:ID|No\.?|Number)?
        |Insurance\s*(?:ID|Policy(?:\s*(?:No\.?|Number))?)
        |Policy\s*(?:No\.?|Number)
        |Member\s*ID
        |Subscriber\s*ID
    )
    \s*[:#=-]?\s*{_IDENTIFIER_VALUE}\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

DEVICE_PATTERN = re.compile(
    rf"""
    \b(?:Device\s*(?:ID|Identifier|Serial(?:\s*Number)?)
    |UDI|Serial\s*(?:No\.?|Number)|S/N|SN|IMEI|MEID)
    \s*[:#=-]?\s*{_IDENTIFIER_VALUE}\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

LICENSE_PATTERN = re.compile(
    rf"""
    \b(?:
        (?:(?:Driver'?s|Driving)\s+Licen[cs]e|Licen[cs]e|License)
        (?:\s*(?:No\.?|Number|\#))?
        \s*[:#=-]?\s*{_LICENSE_VALUE}
        |(?:DL|LIC|LN)\s*[-:#]?\s*{_LICENSE_VALUE}
        |[A-Z]{{2}}\d{{2,4}}[A-Z0-9]{{6,12}}
    )\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

VIN_PATTERN = re.compile(
    r"\b[A-HJ-NPR-Z0-9]{17}\b",
    re.IGNORECASE,
)

# ── DATES / AGES ─────────────────────────────────────────────────────────────
_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
DOB_PATTERN = re.compile(
    rf"\b(?:"
    rf"\d{{1,2}}[./\-]\d{{1,2}}[./\-]\d{{2,4}}"
    rf"|\d{{4}}[./\-]\d{{1,2}}[./\-]\d{{1,2}}"
    rf"|{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{2,4}}"
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}\s+\d{{2,4}}"
    rf")\b",
    re.IGNORECASE,
)

AGE_PATTERN = re.compile(
    r"""
    \b(?:
        (?:age(?:d)?|patient\s+age)\s*[:#=-]?\s*(?:9\d|1[01]\d|120)
        |
        (?:9\d|1[01]\d|120)\s*(?:years?\s*old|y/o|yo)
    )\b
    """,
    re.VERBOSE | re.IGNORECASE,
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

LOCATION_PATTERN = re.compile(
    rf"""
    \b(?:City|County|Precinct|ZIP(?:\s*Code)?|Postal\s*Code|PIN\s*Code)
    \s*[:#=-]?\s*(?:{_CITY}|{_POSTAL})\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

_FACILITY_WORD = r"[A-Z][A-Za-z&.'-]*"
_FACILITY_SUFFIX = (
    r"(?i:Hospital|Clinic|Medical\s+Center|Health\s+Center|Healthcare\s+Center|"
    r"Care\s+Center|Nursing\s+Home|Laboratory|Lab|Pharmacy|Hospice|"
    r"Rehabilitation\s+Center|Rehab\s+Center)"
)
FACILITY_PATTERN = re.compile(
    rf"\b{_FACILITY_WORD}(?:\s+{_FACILITY_WORD}){{0,5}}\s+{_FACILITY_SUFFIX}\b"
)

# ── URL ──────────────────────────────────────────────────────────────────────
URL_PATTERN = re.compile(
    r"(?:https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+"
    r"|www\.[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+(?:\.[A-Za-z]{2,})+"
    r"(?:[/?#][A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*)?)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Pattern registry — order matters:
# broad values such as phone numbers run after labeled identifiers.
# ---------------------------------------------------------------------------
STRUCTURED_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("urls_found", URL_PATTERN, URL_REDACTION_TOKEN),
    ("emails_found", EMAIL_PATTERN, EMAIL_REDACTION_TOKEN),
    ("ssns_found", SSN_PATTERN, SSN_REDACTION_TOKEN),
    ("mrns_found", MRN_PATTERN, MRN_REDACTION_TOKEN),
    ("account_numbers_found", ACCOUNT_PATTERN, ACCOUNT_REDACTION_TOKEN),
    (
        "health_plan_ids_found",
        HEALTH_PLAN_PATTERN,
        HEALTH_PLAN_REDACTION_TOKEN,
    ),
    ("device_ids_found", DEVICE_PATTERN, DEVICE_REDACTION_TOKEN),
    ("licenses_found", LICENSE_PATTERN, LICENSE_REDACTION_TOKEN),
    ("vins_found", VIN_PATTERN, VIN_REDACTION_TOKEN),
    ("faxes_found", FAX_PATTERN, FAX_REDACTION_TOKEN),
    ("phones_found", PHONE_PATTERN, PHONE_REDACTION_TOKEN),
    ("ips_found", IP_PATTERN, IP_REDACTION_TOKEN),
    ("dobs_found", DOB_PATTERN, DOB_REDACTION_TOKEN),
    ("ages_found", AGE_PATTERN, AGE_REDACTION_TOKEN),
    ("addresses_found", ADDRESS_PATTERN, ADDRESS_REDACTION_TOKEN),
    ("locations_found", LOCATION_PATTERN, LOCATION_REDACTION_TOKEN),
    ("facilities_found", FACILITY_PATTERN, FACILITY_REDACTION_TOKEN),
)

REDACTION_TOKEN_ENTITY_TYPES: dict[str, str] = {
    URL_REDACTION_TOKEN: "URL",
    EMAIL_REDACTION_TOKEN: "EMAIL",
    SSN_REDACTION_TOKEN: "SSN",
    MRN_REDACTION_TOKEN: "MRN",
    ACCOUNT_REDACTION_TOKEN: "ACCOUNT",
    HEALTH_PLAN_REDACTION_TOKEN: "HEALTH_PLAN",
    DEVICE_REDACTION_TOKEN: "DEVICE",
    LICENSE_REDACTION_TOKEN: "LICENSE",
    VIN_REDACTION_TOKEN: "VIN",
    FAX_REDACTION_TOKEN: "FAX",
    PHONE_REDACTION_TOKEN: "PHONE",
    IP_REDACTION_TOKEN: "IP",
    DOB_REDACTION_TOKEN: "DOB",
    AGE_REDACTION_TOKEN: "AGE",
    ADDRESS_REDACTION_TOKEN: "ADDRESS",
    LOCATION_REDACTION_TOKEN: "LOCATION",
    FACILITY_REDACTION_TOKEN: "FACILITY",
}

PSEUDONYM_TOKEN_PATTERN = re.compile(r"\[([A-Z][A-Z_]*_\d{3})\]")


class Pseudonymizer:
    """Generate deterministic placeholders for one redaction request."""

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._placeholder_by_value: dict[tuple[str, str], str] = {}

    def pseudonym_for(self, entity_type: str, original_value: str) -> str:
        lookup_key = (entity_type, original_value)
        placeholder = self._placeholder_by_value.get(lookup_key)
        if placeholder is None:
            self._counters[entity_type] += 1
            placeholder = f"{entity_type}_{self._counters[entity_type]:03d}"
            self._placeholder_by_value[lookup_key] = placeholder
            if self.session_id is not None:
                store_mapping(self.session_id, placeholder, original_value)

        return f"[{placeholder}]"


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


class RestoreInput(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="UUID returned by POST /redact",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="Pseudonymized text containing placeholders to restore",
    )

    @field_validator("session_id")
    @classmethod
    def sanitize_session_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("session_id cannot be empty")
        return value

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        return TextInput.sanitize_text(value)


class RedactionResponse(BaseModel):
    status: str
    session_id: str
    redacted_text: str
    emails_found: int
    phones_found: int
    faxes_found: int
    ips_found: int
    names_found: int
    mrns_found: int
    ssns_found: int
    dobs_found: int
    ages_found: int
    addresses_found: int
    locations_found: int
    facilities_found: int
    urls_found: int
    account_numbers_found: int
    health_plan_ids_found: int
    device_ids_found: int
    vins_found: int
    licenses_found: int


class RestoreResponse(BaseModel):
    status: str
    text: str


# ---------------------------------------------------------------------------
# Core redaction helpers
# ---------------------------------------------------------------------------

def _apply_structured_redactions(
    text: str,
    pseudonymizer: Pseudonymizer | None = None,
) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    redacted_text = text
    request_pseudonymizer = pseudonymizer or Pseudonymizer()
    for key, pattern, replacement in STRUCTURED_PATTERNS:
        entity_type = REDACTION_TOKEN_ENTITY_TYPES[replacement]
        redacted_text, n = pattern.subn(
            lambda match, entity_type=entity_type: request_pseudonymizer.pseudonym_for(
                entity_type,
                match.group(0),
            ),
            redacted_text,
        )
        counts[key] = n
    return redacted_text, counts


def restore_pseudonymized_text(text: str, mapping: dict[str, str]) -> str:
    return PSEUDONYM_TOKEN_PATTERN.sub(
        lambda match: mapping.get(match.group(1), match.group(0)),
        text,
    )


def _apply_name_pseudonyms(
    text: str,
    entities: list[NameEntity],
    pseudonymizer: Pseudonymizer,
) -> str:
    pseudonymized_text = text
    entity_replacements = []
    for entity in sorted(entities, key=lambda item: (item.start, item.end)):
        original_value = text[entity.start : entity.end]
        entity_replacements.append(
            (entity, pseudonymizer.pseudonym_for("NAME", original_value))
        )

    for entity, replacement in reversed(entity_replacements):
        pseudonymized_text = (
            pseudonymized_text[: entity.start]
            + replacement
            + pseudonymized_text[entity.end :]
        )
    return pseudonymized_text


@lru_cache(maxsize=1)
def _get_presidio_analyzer() -> AnalyzerEngine | None:
    if os.getenv("DISABLE_PRESIDIO", "").lower() in {"1", "true", "yes"}:
        return None

    try:
        if PRESIDIO_SPACY_MODEL:
            provider = NlpEngineProvider(
                nlp_configuration={
                    "nlp_engine_name": "spacy",
                    "models": [
                        {
                            "lang_code": PRESIDIO_LANGUAGE,
                            "model_name": PRESIDIO_SPACY_MODEL,
                        }
                    ],
                }
            )
            nlp_engine = provider.create_engine()
            return AnalyzerEngine(
                nlp_engine=nlp_engine,
                supported_languages=[PRESIDIO_LANGUAGE],
                default_score_threshold=PRESIDIO_PERSON_THRESHOLD,
            )

        return AnalyzerEngine(
            supported_languages=[PRESIDIO_LANGUAGE],
            default_score_threshold=PRESIDIO_PERSON_THRESHOLD,
        )
    except Exception as exc:
        logger.warning(
            "Presidio AnalyzerEngine unavailable; continuing without PERSON fallback: %s",
            exc,
        )
        return None


def _presidio_person_entities(text: str) -> list[NameEntity]:
    analyzer = _get_presidio_analyzer()
    if analyzer is None:
        return []

    try:
        results = analyzer.analyze(
            text=text,
            entities=["PERSON"],
            language=PRESIDIO_LANGUAGE,
        )
    except Exception as exc:
        logger.warning("Presidio PERSON analysis failed; skipping fallback: %s", exc)
        return []

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


def redact_names(
    text: str,
    pseudonymizer: Pseudonymizer | None = None,
) -> tuple[str, int]:
    """
    Pseudonymize names using a true hybrid detector:
    transformer NER + title/context rules + Presidio PERSON entities.
    """
    candidates: list[NameEntity] = []
    candidates.extend(detect_name_entities(text))
    candidates.extend(_presidio_person_entities(text))

    final_entities = post_process_name_entities(text, candidates)
    if not final_entities:
        return text, 0

    return (
        _apply_name_pseudonyms(text, final_entities, pseudonymizer or Pseudonymizer()),
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
    summary="Pseudonymize PHI/PII from clinical text",
    tags=["Redaction"],
    responses={
        200: {"description": "Successfully pseudonymized text with entity counts"},
        422: {"description": "Validation error — text empty or exceeds length limit"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
@limiter.limit("10/minute")
def redact(
    request: Request,
    data: TextInput,
    _: None = Depends(require_api_key),
):
    """
    Detect and pseudonymize PHI/PII entities from clinical text.

    **Pseudonymization order:**
    1. URLs (before email to avoid partial overlaps)
    2. Emails
    3. SSNs and labeled identifiers (MRN, account, health plan, device IDs)
    4. License numbers and VINs
    5. Fax and phone numbers
    6. IP addresses
    7. Dates, ages over 89, addresses, locations, and facilities
    8. Names — transformer NER + title/context rules + Presidio

    **Rate limit:** 10 requests/minute per IP.
    """
    session_id = create_session()
    pseudonymizer = Pseudonymizer(session_id=session_id)

    try:
        structured_text, counts = _apply_structured_redactions(
            data.text,
            pseudonymizer=pseudonymizer,
        )
        redacted_text, name_count = redact_names(
            structured_text,
            pseudonymizer=pseudonymizer,
        )
    except Exception:
        delete_session(session_id)
        raise

    return {
        "status": "success",
        "session_id": session_id,
        "redacted_text": redacted_text,
        "emails_found": counts["emails_found"],
        "phones_found": counts["phones_found"],
        "faxes_found": counts["faxes_found"],
        "ips_found": counts["ips_found"],
        "names_found": name_count,
        "mrns_found": counts["mrns_found"],
        "ssns_found": counts["ssns_found"],
        "dobs_found": counts["dobs_found"],
        "ages_found": counts["ages_found"],
        "addresses_found": counts["addresses_found"],
        "locations_found": counts["locations_found"],
        "facilities_found": counts["facilities_found"],
        "urls_found": counts["urls_found"],
        "account_numbers_found": counts["account_numbers_found"],
        "health_plan_ids_found": counts["health_plan_ids_found"],
        "device_ids_found": counts["device_ids_found"],
        "vins_found": counts["vins_found"],
        "licenses_found": counts["licenses_found"],
    }


@app.post(
    "/restore",
    response_model=RestoreResponse,
    summary="Restore pseudonymized PHI/PII for an active session",
    tags=["Restoration"],
    responses={
        200: {"description": "Successfully restored text for an active session"},
        404: {"description": "Session not found or expired"},
        422: {"description": "Validation error - text empty or exceeds length limit"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
@limiter.limit("10/minute")
def restore(
    request: Request,
    data: RestoreInput,
    _: None = Depends(require_api_key),
):
    """
    Restore pseudonym placeholders using server-side mappings for an active session.

    Mappings are never returned by this endpoint. Unknown placeholders remain
    unchanged so callers can safely restore partial snippets from a session.
    """
    mapping = get_mapping(data.session_id)
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired",
        )

    return {
        "status": "success",
        "text": restore_pseudonymized_text(data.text, mapping),
    }
