# PHI/PII Redaction Pipeline
## Infotact Technical Internship Program — HealthTech Cybersecurity Project

> A healthcare data privacy tool that automatically detects and anonymizes Protected Health
> Information (PHI) and Personally Identifiable Information (PII) from clinical text before
> it is processed by any external AI system.

---

## System Architecture

```
┌─────────────────────────────────────┐
│  FRONTEND  (Suvajit Ray)            │
│  HTML + Bootstrap + JavaScript      │
│  User enters text → sees result     │
└────────────────┬────────────────────┘
                 │ HTTP POST /redact
                 ▼
┌─────────────────────────────────────┐
│  BACKEND API  (Sathish)             │
│  Python FastAPI                     │
│  /redact  →  /restore               │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  PHI DETECTION ENGINE  (Emmanuel)   │
│  Microsoft Presidio + spaCy NER     │
│  Detects: Names, Phones, Emails,    │
│  Addresses, MRN, Dates              │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  TOKEN STORAGE  (Tanisha)           │
│  Redis Database                     │
│  PATIENT_001 ↔ John Smith           │
│  PHONE_001   ↔ +1-555-123-4567      │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  REDACTED OUTPUT                    │
│  Safe anonymized text + entity JSON │
│  Returned to frontend for display   │
└─────────────────────────────────────┘
```

---

## Team

| Member | Role | Technologies |
|--------|------|-------------|
| Member 1 | Backend API | Python, FastAPI, Uvicorn |
| Member 2 | PHI Detection | Microsoft Presidio, spaCy, Regex |
| Member 3 | Token Storage | Redis, Python redis-py |
| Member 4 | Frontend + Documentation | HTML5, CSS3, Bootstrap 5, JavaScript |

---

## Features

- Paste any clinical text and detect PHI in real time
- Color-coded entity badges: Name (blue), Phone (green), Email (teal), Address (red), MRN (purple), Date (yellow)
- Toggle between redacted and original text view
- Copy redacted output to clipboard
- Download result as a `.txt` file
- Entity breakdown panel showing count per type
- Three pre-loaded sample clinical notes for demo
- Mobile responsive design
- Error handling for API connection issues

---

## Project Files (Member 4)

```
phi-redaction-frontend/
├── index.html          ← Main webpage (DAY 1-20)
├── style.css           ← All styling and colors (DAY 1-20)
├── script.js           ← All JavaScript and API calls (DAY 5-20)
├── architecture.html   ← System architecture diagram (DAY 13)
├── API_DOCS.md         ← Backend API documentation (DAY 14)
├── COMPONENTS.md       ← Frontend component guide (DAY 19)
└── README.md           ← This file (DAY 7, 14, 20)
```

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/YOUR-USERNAME/phi-redaction-frontend.git
cd phi-redaction-frontend

# 2. Open the frontend
# Simply open index.html in any browser (Chrome, Edge, Firefox)
# Double-click the file OR right-click → Open With → Browser

# 3. Start the backend (Member 1 runs this)
cd backend/
pip install fastapi uvicorn
uvicorn main:app --reload --port 8000

# 4. Start Redis (Member 3 runs this)
redis-server

# 5. Open browser at http://localhost (or just open index.html)
```

---

## API Endpoints Used by Frontend

### POST /redact
Sends clinical text → receives redacted text with entity list.

**Request:**
```json
{ "text": "Patient John Smith, DOB 12/05/1985, MRN 100234..." }
```

**Response:**
```json
{
  "redacted_text": "Patient PATIENT_001, DOB DATE_001, MRN MRN_001...",
  "entities": [
    { "text": "John Smith",  "label": "NAME",  "replacement": "PATIENT_001" },
    { "text": "12/05/1985",  "label": "DATE",  "replacement": "DATE_001" },
    { "text": "100234",      "label": "MRN",   "replacement": "MRN_001" }
  ]
}
```

### POST /restore
Sends redacted text → receives original text back using Redis mappings.

---

## HIPAA Safe Harbor Compliance

The HIPAA Safe Harbor method defines **18 specific identifiers** that must be removed from
patient data before it can be considered de-identified. This pipeline targets these identifiers:

| # | Identifier | Status |
|---|-----------|--------|
| 1 | Patient names | ✅ Detected (NAME entity) |
| 2 | Geographic data (address, zip) | ✅ Detected (ADDRESS entity) |
| 3 | Dates (DOB, admission, discharge) | ✅ Detected (DATE entity) |
| 4 | Phone numbers | ✅ Detected (PHONE entity) |
| 5 | Fax numbers | ⚠️ Partial (Regex in Member 2) |
| 6 | Email addresses | ✅ Detected (EMAIL entity) |
| 7 | Social Security Numbers | ⚠️ Requires Presidio extension |
| 8 | Medical record numbers | ✅ Detected (MRN entity) |
| 9 | Health plan beneficiary numbers | ⚠️ Requires Presidio extension |
| 10 | Account numbers | ⚠️ Requires Presidio extension |
| 11 | Certificate/license numbers | ⚠️ Requires Presidio extension |
| 12 | Vehicle identifiers / serial numbers | ⚠️ Not yet implemented |
| 13 | Device identifiers | ⚠️ Not yet implemented |
| 14 | Web URLs | ⚠️ Partial (Regex in Member 2) |
| 15 | IP addresses | ⚠️ Requires Presidio extension |
| 16 | Biometric identifiers | ⚠️ Not yet implemented |
| 17 | Full face photographs | ⚠️ Not applicable (text only) |
| 18 | Any other unique identifying number | ⚠️ Partial |

**Current coverage: 6 of 18 identifiers fully implemented.**
Expanding coverage requires extending the Presidio configuration in Member 2's module.

---


## Important Note on Data Privacy

All sample clinical notes in this project use **completely fabricated patient data**.
No real patient names, dates, addresses, or medical record numbers are used anywhere
in this codebase. Never commit real PHI to a public GitHub repository.

---

*Infotact Solutions — Electronic City, Bengaluru, Karnataka — support@infotact.in*
