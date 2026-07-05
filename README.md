# PHI/PII Pseudonymization Backend

FastAPI service for detecting healthcare PHI/PII and replacing it with
reversible pseudonyms before sending content to downstream systems or LLM
workflows.

This project supports HIPAA de-identification workflows, but the code alone
does not make a deployment HIPAA compliant. Production use still needs access
controls, TLS, audit controls that do not log PHI, encryption, retention
policy, monitoring, incident response, and business-associate/vendor controls.

## What Changed

The backend now performs reversible pseudonymization instead of irreversible
token replacement.

Example:

```text
Patient John Smith called +91 98765 43210.
```

becomes:

```text
Patient [NAME_001] called [PHONE_001].
```

Each request gets a random UUID `session_id`. Server-side mappings are stored
only for that session and expire after 30 minutes.

## Features

- Reversible pseudonymization with per-entity counters: `[NAME_001]`,
  `[PHONE_001]`, `[EMAIL_001]`, `[MRN_001]`, `[SSN_001]`, and related tokens
- Names: transformer NER, title/context rules, and optional Presidio PERSON fallback
- Emails, URLs, phone numbers, fax numbers, IPv4/IPv6 addresses
- MRN, SSN, account numbers, health plan/member IDs, device/serial IDs
- DOB/full dates, ages over 89, addresses, labeled locations, hospitals/clinics
- VINs and driver's license/government ID formats
- Duplicate values reuse the same placeholder inside a request
- Request size validation, input sanitization, rate limiting, no-store headers
- Optional API-key protection with `REDACTION_API_KEY`
- Swagger/OpenAPI documentation

## Architecture

- `backend/main.py`
  - FastAPI application
  - Input validation and security headers
  - Existing regex PHI/PII detection
  - Existing Presidio PERSON fallback
  - Pseudonym token generation
  - `/redact` and `/restore` endpoints
- `backend/mapping_store.py`
  - In-memory server-side session store
  - `create_session()`
  - `store_mapping()`
  - `get_mapping()`
  - `delete_session()`
  - `cleanup_expired_sessions()`
- `transformer_ner.py`
  - Existing transformer and rule-based name detection
  - Existing NER logic is preserved

## Run

```powershell
python -m uvicorn backend.main:app --reload
```

or, if you use `uv`:

```powershell
uv run uvicorn backend.main:app --reload
```

## API

### Health

- `GET /`
- `GET /health`

### POST /redact

Pseudonymizes PHI/PII and creates a new mapping session.

Request:

```json
{
  "text": "Patient John Smith visited Apollo Hospital. MRN: 1234567."
}
```

Response:

```json
{
  "status": "success",
  "session_id": "8b2e7a20-4ce8-42c3-83d0-4d49b9a9c0f1",
  "redacted_text": "Patient [NAME_001] visited [FACILITY_001]. [MRN_001].",
  "emails_found": 0,
  "phones_found": 0,
  "faxes_found": 0,
  "ips_found": 0,
  "names_found": 1,
  "mrns_found": 1,
  "ssns_found": 0,
  "dobs_found": 0,
  "ages_found": 0,
  "addresses_found": 0,
  "locations_found": 0,
  "facilities_found": 1,
  "urls_found": 0,
  "account_numbers_found": 0,
  "health_plan_ids_found": 0,
  "device_ids_found": 0,
  "vins_found": 0,
  "licenses_found": 0
}
```

Mappings are never returned in this response.

### POST /restore

Restores placeholders using server-side mappings for an active session.

Request:

```json
{
  "session_id": "8b2e7a20-4ce8-42c3-83d0-4d49b9a9c0f1",
  "text": "Patient [NAME_001] visited [FACILITY_001]."
}
```

Response:

```json
{
  "status": "success",
  "text": "Patient John Smith visited Apollo Hospital."
}
```

If the session does not exist or has expired, `/restore` returns `404`.

## Session Management

Every `/redact` request creates a random UUID session ID. The in-memory mapping
store keeps placeholder-to-original mappings server-side:

```python
SESSION_STORE = {
    "8b2e7a20-4ce8-42c3-83d0-4d49b9a9c0f1": {
        "NAME_001": "John Smith",
        "PHONE_001": "+91 98765 43210",
        "EMAIL_001": "john@example.com",
    }
}
```

Sessions expire after 30 minutes. Expired sessions are removed when new sessions
are created, mappings are read, or cleanup is called directly.

## Security Notes

- Mappings are stored only server-side.
- Mappings are never returned by `/redact` or `/restore`.
- Session IDs are generated with UUID4 randomness.
- Responses include `Cache-Control: no-store`.
- API-key protection is enabled when `REDACTION_API_KEY` is configured.
- Use TLS, authentication, authorization, audit controls, encryption, and a
  retention policy in production.
- The default in-memory store is process-local. Use an encrypted external store
  such as Redis with TTLs for multi-worker or multi-instance deployments.

If `REDACTION_API_KEY` is set, call `/redact` and `/restore` with either:

- `Authorization: Bearer <key>`
- `X-API-Key: <key>`

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `MAX_REDACTION_CHARS` | `50000` | Maximum accepted input size |
| `CORS_ALLOW_ORIGINS` | `https://yourdomain.com` | Comma-separated allowed origins |
| `REDACTION_API_KEY` | unset | Enables API-key enforcement when set |
| `DISABLE_TRANSFORMER_NER` | unset | Set to `1`, `true`, or `yes` to use rules/Presidio only |
| `PHI_NER_MODEL` | `dslim/bert-base-NER` | Hugging Face NER model |
| `DISABLE_PRESIDIO` | unset | Set to `1`, `true`, or `yes` to skip Presidio |
| `PRESIDIO_LANGUAGE` | `en` | Presidio language |
| `PRESIDIO_SPACY_MODEL` | unset | spaCy model name for Presidio NLP engine |
| `PRESIDIO_PERSON_THRESHOLD` | `0.80` | Minimum Presidio PERSON score |

## Tests

Run the deterministic rule/regex/API suite without loading the transformer:

```powershell
$env:DISABLE_TRANSFORMER_NER = "1"
$env:DISABLE_PRESIDIO = "1"
python test_transformer.py
python test_hybrid.py
```

Run without those environment variables when you want to exercise the local
transformer and Presidio model stack.
