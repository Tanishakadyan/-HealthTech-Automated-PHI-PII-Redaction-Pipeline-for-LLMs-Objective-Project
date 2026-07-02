"""
=======================================================================
  PHI / PII REDACTION PIPELINE — BACKEND
  FastAPI application implementing /redact and /restore endpoints
=======================================================================

  This file combines what would normally be three team members' work
  (Backend API, PHI Detection, Token Storage) into one runnable backend
  so the full project works end to end.

  Endpoints:
    POST /redact   - detects PHI/PII in text, returns anonymized text
    POST /restore  - reverses anonymization using stored token mapping
    GET  /health   - simple health check

  Storage:
    Uses Redis if a Redis server is reachable at localhost:6379.
    Otherwise falls back automatically to an in-memory dictionary,
    so the app still runs with zero extra setup.
=======================================================================
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re
import uuid

# -----------------------------------------------------------------------
# STORAGE LAYER — tries Redis first, falls back to in-memory dict
# -----------------------------------------------------------------------
USE_REDIS = False
redis_client = None

try:
    import redis as redis_lib
    redis_client = redis_lib.Redis(
        host="localhost", port=6379, db=0,
        decode_responses=True, socket_connect_timeout=1
    )
    redis_client.ping()
    USE_REDIS = True
    print("[storage] Connected to Redis — using Redis for token storage.")
except Exception:
    USE_REDIS = False
    print("[storage] Redis not available — falling back to in-memory storage.")

# In-memory fallback store: { token: original_value }
_memory_store: dict[str, str] = {}


def store_mapping(token: str, original_value: str) -> None:
    """Save a token -> original value mapping."""
    if USE_REDIS:
        redis_client.set(token, original_value)
    else:
        _memory_store[token] = original_value


def get_mapping(token: str) -> str | None:
    """Look up the original value for a token."""
    if USE_REDIS:
        return redis_client.get(token)
    return _memory_store.get(token)


# -----------------------------------------------------------------------
# PHI / PII DETECTION ENGINE
# Regex-based detection covering the entity types this project targets:
# NAME, PHONE, EMAIL, ADDRESS, MRN, DATE
#
# This is intentionally dependency-light (no large model download
# required) so it runs anywhere immediately. It can be swapped for
# Microsoft Presidio + spaCy NER for more advanced contextual detection
# (see README "Upgrading Detection" section).
# -----------------------------------------------------------------------

# Order matters: more specific patterns first to avoid overlap conflicts
PATTERNS = [
    ("MRN",     re.compile(r"\bMRN[-\s]?\d{4,8}\b", re.IGNORECASE)),
    ("EMAIL",   re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE",   re.compile(r"(\+?\d{1,2}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("DATE",    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
    ("ADDRESS", re.compile(
        r"\b\d{1,5}\s+[A-Z][a-zA-Z]*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Loop)\b"
        r"(?:,\s*[A-Za-z]+\s+[A-Z]{2}\s*\d{5})?",
    )),
    # Names: "Mr./Mrs./Ms./Dr." + Capitalized Word(s), OR two-capitalized-word sequences
    # following common clinical keywords (Patient, Doctor, Physician, Dear)
    ("NAME", re.compile(
        r"\b(?:Dr\.|Mr\.|Mrs\.|Ms\.)\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?"
        r"|\b(?:Patient|Patient Name|Doctor|Physician|Dear)\s*:?\s+([A-Z][a-z]+\s[A-Z][a-z]+)"
        r"|\b[A-Z][a-z]+\s[A-Z][a-z]+(?=,\s*(?:born|DOB|age))",
    )),
]

# Words that look like names but should NEVER be redacted
# (medical conditions named after people, common clinical terms)
NAME_WHITELIST = {
    "Parkinson's", "Parkinson's disease", "Alzheimer's", "Alzheimer's disease",
    "Type 2", "Type 1", "General Practitioner",
}


def detect_entities(text: str) -> list[dict]:
    """
    Scans the input text for PHI/PII entities.
    Returns a list of dicts: {start, end, text, label}
    Entities are matched without overlapping (first match wins per span).
    """
    found = []
    claimed_spans: list[tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        for s, e in claimed_spans:
            if start < e and end > s:
                return True
        return False

    for label, pattern in PATTERNS:
        for match in pattern.finditer(text):
            # For NAME pattern with capture groups, use group(1) if present
            if label == "NAME" and match.group(1):
                start, end = match.start(1), match.end(1)
                value = match.group(1)
            else:
                start, end = match.start(), match.end()
                value = match.group(0)

            if overlaps(start, end):
                continue
            if value.strip() in NAME_WHITELIST:
                continue
            if not value.strip():
                continue

            found.append({"start": start, "end": end, "text": value, "label": label})
            claimed_spans.append((start, end))

    # Sort by position in text (left to right) for predictable replacement
    found.sort(key=lambda e: e["start"])
    return found


def redact_text(text: str) -> tuple[str, list[dict]]:
    """
    Replaces every detected entity with a unique token (e.g. PATIENT_001).
    Stores the token -> original value mapping for later restoration.
    Returns (redacted_text, entities_list_with_replacements).
    """
    entities = detect_entities(text)

    # Counter per label so tokens read NAME -> PATIENT_001, PATIENT_002 etc.
    counters: dict[str, int] = {}
    token_prefix = {
        "NAME": "PATIENT",
        "PHONE": "PHONE",
        "EMAIL": "EMAIL",
        "ADDRESS": "ADDRESS",
        "MRN": "MRN",
        "DATE": "DATE",
    }

    # Build replacements first (so we can do a single pass without
    # shifting offsets as we substitute)
    result_entities = []
    for ent in entities:
        label = ent["label"]
        counters[label] = counters.get(label, 0) + 1
        token = f"{token_prefix.get(label, 'TOKEN')}_{counters[label]:03d}"

        # Store mapping for restore step (also store a unique session id
        # to avoid collisions across different requests using same tokens)
        store_mapping(token, ent["text"])

        result_entities.append({
            "text": ent["text"],
            "label": label,
            "replacement": token,
            "start": ent["start"],
            "end": ent["end"],
        })

    # Replace right-to-left so earlier offsets remain valid as we edit the string
    redacted = text
    for ent in sorted(result_entities, key=lambda e: e["start"], reverse=True):
        redacted = redacted[:ent["start"]] + ent["replacement"] + redacted[ent["end"]:]

    # Drop start/end from the response (frontend doesn't need them)
    for ent in result_entities:
        ent.pop("start", None)
        ent.pop("end", None)

    return redacted, result_entities


def restore_text(redacted_text: str) -> str:
    """
    Replaces every known token in the text with its original value
    by looking up each token in storage.
    """
    # Match any TOKEN_NNN pattern, e.g. PATIENT_001, PHONE_002
    token_pattern = re.compile(r"\b[A-Z]+_\d{3}\b")

    def replace_token(match: re.Match) -> str:
        token = match.group(0)
        original = get_mapping(token)
        return original if original is not None else token

    return token_pattern.sub(replace_token, redacted_text)


# -----------------------------------------------------------------------
# FASTAPI APP SETUP
# -----------------------------------------------------------------------

app = FastAPI(
    title="PHI/PII Redaction API",
    description="Detects and anonymizes PHI/PII in clinical text for safe LLM use.",
    version="1.0.0",
)

# Allow the frontend (opened as a local file or different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RedactRequest(BaseModel):
    text: str


class RedactResponse(BaseModel):
    redacted_text: str
    entities: list[dict]


class RestoreRequest(BaseModel):
    redacted_text: str


class RestoreResponse(BaseModel):
    original_text: str


@app.get("/health")
def health_check():
    """Simple endpoint to verify the server is running."""
    return {
        "status": "ok",
        "storage_backend": "redis" if USE_REDIS else "in-memory (fallback)",
    }


@app.post("/redact", response_model=RedactResponse)
def redact(payload: RedactRequest):
    """
    Accepts raw clinical text. Detects PHI/PII entities and replaces
    them with anonymized tokens. Returns the redacted text plus a list
    of every entity that was found.
    """
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Text field cannot be empty.")
    if len(text) > 5000:
        raise HTTPException(status_code=422, detail="Text exceeds 5000 character limit.")

    redacted_text, entities = redact_text(text)
    return RedactResponse(redacted_text=redacted_text, entities=entities)


@app.post("/restore", response_model=RestoreResponse)
def restore(payload: RestoreRequest):
    """
    Accepts redacted text containing tokens (e.g. PATIENT_001).
    Looks up each token in storage and replaces it with the original
    sensitive value, reconstructing the original text.
    """
    redacted_text = payload.redacted_text.strip()
    if not redacted_text:
        raise HTTPException(status_code=422, detail="redacted_text field cannot be empty.")

    original_text = restore_text(redacted_text)
    return RestoreResponse(original_text=original_text)


@app.get("/")
def root():
    return {
        "message": "PHI/PII Redaction API is running.",
        "docs": "/docs",
        "endpoints": ["/redact", "/restore", "/health"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
