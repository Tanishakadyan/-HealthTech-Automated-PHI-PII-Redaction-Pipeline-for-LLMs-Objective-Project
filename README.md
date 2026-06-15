# PHI/PII Redaction Pipeline
## Infotact Technical Internship Program — HealthTech Cybersecurity Project

> A healthcare data privacy tool that automatically detects and anonymizes Protected Health
> Information (PHI) and Personally Identifiable Information (PII) from clinical text before
> it is processed by any external AI system.

---

## System Architecture
```
┌─────────────────────────────────────┐
│  FRONTEND  (Member 4)               │
│  HTML + Bootstrap + JavaScript      │
│  User enters text → sees result     │
└────────────────┬────────────────────┘
                 │ HTTP POST /redact
                 ▼
┌─────────────────────────────────────┐
│  BACKEND API  (Member 1)            │
│  Python FastAPI                     │
│  /redact  →  /restore               │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  PHI DETECTION ENGINE  (Member 2)   │
│  Microsoft Presidio + spaCy NER     │
│  Detects: Names, Phones, Emails,    │
│  Addresses, MRN, Dates              │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  TOKEN STORAGE  (Member 3)          │
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
