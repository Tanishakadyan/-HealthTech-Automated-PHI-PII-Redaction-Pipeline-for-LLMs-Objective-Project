# PHI Redaction Backend

## Features
- Email Redaction
- Phone Redaction
- IP Redaction
- MRN Redaction
- DOB Redaction
- Address Redaction
- Hybrid NER (Transformer + Presidio)

## Run

uv run uvicorn backend.main:app --reload

## API

GET /

POST /redact
