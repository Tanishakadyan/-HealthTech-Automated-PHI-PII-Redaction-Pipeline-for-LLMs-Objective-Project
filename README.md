# PHI / PII Redaction Pipeline
### Infotact Solutions — Cybersecurity Internship 2026
### Project 2: HealthTech — Automated PHI/PII Redaction Pipeline for LLMs

---

## What This Project Does

Doctors and hospitals are adopting AI tools to help write clinical notes. But sending
real patient data (names, phone numbers, dates of birth, medical record numbers) to
an external AI system violates HIPAA. This tool sits in the middle:

1. Doctor pastes a clinical note into the web UI
2. The system detects all sensitive information (PHI/PII)
3. Replaces it with anonymous tokens like `PATIENT_001`, `PHONE_001`
4. The safe, anonymized text can be sent to any AI model
5. The original text can be restored anytime using the stored token mapping

---

## How to Run (Step by Step)

### Step 1 — Make sure Python is installed
Open a terminal / command prompt and type:
```
python --version
```
You need Python 3.10 or higher. Download from https://python.org if needed.

### Step 2 — Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 3 — Start the backend server

**On Mac or Linux:**
```bash
./START.sh
```
Or manually:
```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**On Windows:**
Double-click `START.bat`
Or in Command Prompt:
```
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
INFO:  Uvicorn running on http://127.0.0.1:8000
```

### Step 4 — Open the frontend
Open `frontend/index.html` in Chrome, Edge, or Firefox.
(Just double-click the file — no web server needed for the frontend.)

### Step 5 — Use the tool
1. Click one of the **Sample** buttons to load a test clinical note, or type your own
2. Click **Redact PHI** — the backend detects and anonymizes all sensitive data
3. See the result with **color-coded badges** for each entity type
4. Click **Show Original Text** to restore the original
5. Click **Copy Text** or **Download .txt** to export the redacted version

---

## Project Structure

```
phi-redaction-project/
│
├── START.sh                ← Start script (Mac/Linux) — double-click or run in terminal
├── START.bat               ← Start script (Windows) — double-click to run
│
├── backend/
│   ├── main.py             ← FastAPI backend — ALL server logic lives here
│   └── requirements.txt    ← Python packages to install
│
├── frontend/
│   ├── index.html          ← The webpage (Member 4)
│   ├── style.css           ← All styles and colors (Member 4)
│   ├── script.js           ← All button/API logic (Member 4)
│   └── architecture.html   ← System diagram — open in browser to view (Member 4)
│
└── README.md               ← This file
```

---

## API Endpoints

The backend runs at `http://127.0.0.1:8000`. You can also open
`http://127.0.0.1:8000/docs` in your browser to see the interactive API explorer.

### POST `/redact`
Send clinical text, get back anonymized text + list of detected entities.

**Request:**
```json
{ "text": "Patient John Smith, DOB 12/05/1985, called on 555-123-4567." }
```
**Response:**
```json
{
  "redacted_text": "Patient PATIENT_001, DOB DATE_001, called on PHONE_001.",
  "entities": [
    { "text": "John Smith",  "label": "NAME",  "replacement": "PATIENT_001" },
    { "text": "12/05/1985",  "label": "DATE",  "replacement": "DATE_001"   },
    { "text": "555-123-4567","label": "PHONE", "replacement": "PHONE_001"  }
  ]
}
```

### POST `/restore`
Send redacted text, get back original text using stored token mapping.

**Request:**
```json
{ "redacted_text": "Patient PATIENT_001, DOB DATE_001, called on PHONE_001." }
```
**Response:**
```json
{ "original_text": "Patient John Smith, DOB 12/05/1985, called on 555-123-4567." }
```

### GET `/health`
Check if the server is running.
```json
{ "status": "ok", "storage_backend": "in-memory (fallback)" }
```

---

## Entity Types Detected

| Label | What it finds | Badge Color |
|-------|--------------|-------------|
| `NAME` | Patient names, doctor names (`Dr. X`, `Mr. X`, `Patient: X`) | Blue |
| `DATE` | Dates of birth, visit dates (`12/05/1985`, `06/01/2026`) | Amber |
| `MRN` | Medical record numbers (`MRN 100234`, `MRN-200456`) | Purple |
| `PHONE` | Phone numbers (`555-123-4567`, `+1-617-555-8899`) | Green |
| `EMAIL` | Email addresses (`john@email.com`) | Teal |
| `ADDRESS` | Street addresses (`45 Oak Street, Boston MA 02101`) | Red |

---

## Real Output from This System

**Input:**
```
Patient John Smith, DOB 12/05/1985, MRN 100234, called on 555-123-4567.
Email: john.smith@email.com. Address: 45 Oak Street, Boston MA 02101.
Diagnosed with Parkinson's disease in 2019. Attending: Dr. Sarah Adams.
```

**Output (redacted):**
```
Patient PATIENT_001, DOB DATE_001, MRN_001, called on PHONE_001.
Email: EMAIL_001. Address: ADDRESS_001.
Diagnosed with Parkinson's disease in 2019. Attending: PATIENT_002.
```

**Entities found (7):**
```
[NAME   ]  John Smith                      → PATIENT_001
[DATE   ]  12/05/1985                      → DATE_001
[MRN    ]  MRN 100234                      → MRN_001
[PHONE  ]  555-123-4567                    → PHONE_001
[EMAIL  ]  john.smith@email.com            → EMAIL_001
[ADDRESS]  45 Oak Street, Boston MA 02101  → ADDRESS_001
[NAME   ]  Dr. Sarah Adams                 → PATIENT_002
```

**Restore:** Calling `/restore` brings back the original text exactly — confirmed correct ✓

Note: "Parkinson's disease" is intentionally NOT redacted — the system correctly
distinguishes medical condition names from actual patient/doctor names.

---

## Token Storage

By default the system uses **in-memory storage** (a Python dictionary). This means:
- No Redis installation needed
- Tokens are stored in RAM while the server is running
- If you restart the server, old tokens are cleared

To use **Redis** for persistent storage:
1. Install Redis: https://redis.io/docs/getting-started/
2. Start Redis: `redis-server`
3. The backend auto-detects Redis and switches to it — no code changes needed

---

## Team

| Member | Role | Files |
|--------|------|-------|
| Member 1 | Backend API | `backend/main.py` |
| Member 2 | PHI Detection | `backend/main.py` (detection engine section) |
| Member 3 | Token Storage | `backend/main.py` (storage layer section) |
| Member 4 | Frontend + Documentation | `frontend/index.html`, `frontend/style.css`, `frontend/script.js`, all `.md` files |

---

## GitHub — Daily Commit Requirement

The project evaluation requires commits on **every single day** across all 4 weeks.
See `frontend/DAILY_COMMIT_GUIDE.md` for the exact commit message to use each day.

Quick reference:
```bash
git add .
git commit -m "feat: your message here"
git push origin member-4-frontend
```

---

