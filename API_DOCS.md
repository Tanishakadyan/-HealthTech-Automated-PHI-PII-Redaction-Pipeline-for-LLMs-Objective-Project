# API Documentation
## PHI/PII Redaction Pipeline — Backend Endpoints

<!--
  FILE: API_DOCS.md
  MEMBER 4: Frontend + Documentation
  DAY 14 → Created full API documentation
  DAY 20 → Final review and cleanup
-->

> Written by Member 4 (Frontend & Documentation).
> These endpoints are implemented by **Member 1** (FastAPI Backend).

---

## Base URL

```
http://localhost:8000
```

When deployed to production, replace with the actual server URL.

---

## POST /redact

Accepts raw clinical text and returns the redacted version with entity metadata.

### Request

**Method:** `POST`
**URL:** `http://localhost:8000/redact`
**Content-Type:** `application/json`

**Body:**
```json
{
  "text": "Patient John Smith, DOB 12/05/1985, MRN 100234, called on +1-555-123-4567. Email: john.smith@email.com. Address: 45 Oak Street, Boston MA 02101."
}
```

| Field | Type   | Required | Description |
|-------|--------|----------|-------------|
| text  | string | Yes      | Raw clinical text to be redacted. Max 5000 characters. |

### Response

**Status:** `200 OK`
**Content-Type:** `application/json`

```json
{
  "redacted_text": "Patient PATIENT_001, DOB DATE_001, MRN MRN_001, called on PHONE_001. Email: EMAIL_001. Address: ADDRESS_001.",
  "entities": [
    {
      "text": "John Smith",
      "label": "NAME",
      "replacement": "PATIENT_001",
      "start": 8,
      "end": 18
    },
    {
      "text": "12/05/1985",
      "label": "DATE",
      "replacement": "DATE_001",
      "start": 24,
      "end": 34
    },
    {
      "text": "100234",
      "label": "MRN",
      "replacement": "MRN_001",
      "start": 40,
      "end": 46
    },
    {
      "text": "+1-555-123-4567",
      "label": "PHONE",
      "replacement": "PHONE_001",
      "start": 58,
      "end": 73
    },
    {
      "text": "john.smith@email.com",
      "label": "EMAIL",
      "replacement": "EMAIL_001",
      "start": 82,
      "end": 102
    },
    {
      "text": "45 Oak Street, Boston MA 02101",
      "label": "ADDRESS",
      "replacement": "ADDRESS_001",
      "start": 113,
      "end": 143
    }
  ]
}
```

| Field         | Type   | Description |
|---------------|--------|-------------|
| redacted_text | string | Original text with PHI replaced by tokens |
| entities      | array  | List of detected PHI entities |
| entities[].text | string | Original PHI text that was detected |
| entities[].label | string | Entity type (NAME, PHONE, EMAIL, ADDRESS, MRN, DATE) |
| entities[].replacement | string | Token that replaced the original text |
| entities[].start | integer | Character position where entity starts |
| entities[].end | integer | Character position where entity ends |

### Error Responses

**422 Unprocessable Entity** — Missing or invalid `text` field
```json
{ "detail": "text field is required" }
```

**500 Internal Server Error** — Server-side processing error
```json
{ "detail": "Internal server error" }
```

---

## POST /restore

Converts redacted text back to the original using the Redis token mappings.

### Request

**Method:** `POST`
**URL:** `http://localhost:8000/restore`
**Content-Type:** `application/json`

**Body:**
```json
{
  "redacted_text": "Patient PATIENT_001, DOB DATE_001, called on PHONE_001."
}
```

| Field         | Type   | Required | Description |
|---------------|--------|----------|-------------|
| redacted_text | string | Yes      | Text with token placeholders to be restored |

### Response

**Status:** `200 OK`

```json
{
  "original_text": "Patient John Smith, DOB 12/05/1985, called on +1-555-123-4567."
}
```

| Field         | Type   | Description |
|---------------|--------|-------------|
| original_text | string | Text with all tokens replaced by their original values from Redis |

### Note
If a token is not found in Redis (e.g. session expired), it remains as-is in the output.

---

## Supported Entity Labels

| Label | Example Detected | Badge Color |
|-------|-----------------|-------------|
| NAME | John Smith, Dr. Adams | Blue |
| PHONE | +1-555-123-4567, 617-555-8899 | Green |
| EMAIL | john@email.com | Teal |
| ADDRESS | 45 Oak Street, Boston MA 02101 | Red |
| MRN | MRN-100234, MRN100234 | Purple |
| DATE | 12/05/1985, June 1 2026 | Yellow |

---

## How the Frontend Uses These APIs

```javascript
// Frontend (script.js) calls /redact like this:
const response = await fetch("http://localhost:8000/redact", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: userInput })
});
const data = await response.json();
// data.redacted_text → shown in result card
// data.entities      → used to render colored badges
```

---

*API implementation: Member 1 (FastAPI)*
*API documentation: Member 4 (Frontend & Docs)*
