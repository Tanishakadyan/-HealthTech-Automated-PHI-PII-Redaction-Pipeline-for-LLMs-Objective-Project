# PHI/PII Redaction Backend

FastAPI service for redacting text-based healthcare PHI/PII before sending
content to downstream systems or LLM workflows.

This project supports HIPAA de-identification workflows, but the code alone
does not make a deployment HIPAA compliant. Production use still needs access
controls, TLS, audit controls that do not log PHI, encryption, retention
policy, monitoring, incident response, and business-associate/vendor controls.

## Features

- Names: transformer NER, title/context rules, and optional Presidio PERSON fallback
- Emails, URLs, phone numbers, fax numbers, IPv4/IPv6 addresses
- MRN, SSN, account numbers, health plan/member IDs, device/serial IDs
- DOB/full dates, ages over 89, addresses, labeled locations, hospitals/clinics
- VINs and driver's license/government ID formats
- Request size validation, input sanitization, rate limiting, no-store headers
- Optional API-key protection with `REDACTION_API_KEY`

## Run

```powershell
uv run uvicorn backend.main:app --reload
```

## API

- `GET /` health check
- `GET /health` machine-readable health check
- `POST /redact` redacts PHI/PII from a JSON body:

```json
{
  "text": "Patient JOHN SMITH visited Apollo Hospital. MRN: 1234567."
}
```

If `REDACTION_API_KEY` is set, call `/redact` with either:

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

Run the deterministic rule/regex suite without loading the transformer:

```powershell
$env:DISABLE_TRANSFORMER_NER = "1"
$env:DISABLE_PRESIDIO = "1"
uv run python test_transformer.py
uv run python test_hybrid.py
```

Run without those environment variables when you want to exercise the local
transformer and Presidio model stack.
