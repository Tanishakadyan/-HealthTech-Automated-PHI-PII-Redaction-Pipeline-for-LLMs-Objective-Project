from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import re
import html
import logging


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()


limiter = Limiter(key_func=get_remote_address)


app = FastAPI(
    title="PII Redaction API",     
)

app.state.limiter = limiter


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],   
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    
    logger.error(f"Unhandled error: {type(exc).__name__}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error"
        }
    )


EMAIL_PATTERN = re.compile(
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+'  
)

PHONE_PATTERN = re.compile(
    r'\b\d{10}\b'
)

IP_PATTERN = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'           
    r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
)
MRN_PATTERN = re.compile(
    r'\b(?:MRN|Medical Record Number)\s*[:#=]?\s*\d+\b',
    re.IGNORECASE
)


class TextInput(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Input text for PII redaction"
    )

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v):
        v = html.unescape(v)              
        v = re.sub(r'<[^>]+>', '', v)    
        v = v.replace('\x00', '')         
        v = v.strip()
        if not v:
            raise ValueError("Text cannot be empty after sanitization")
        return v



def redact_names(text: str):
    results = analyzer.analyze(
        text=text,
        entities=["PERSON"],
        language="en"
    )

    IGNORE_WORDS = {
        "email",
        "phone",
        "patient",
        "mrn",
        "diagnosis"
    }

    results = [
        r for r in results
        if r.score >= 0.85
        and text[r.start:r.end].lower() not in IGNORE_WORDS
    ]

    names_found = len(results)

    if names_found == 0:
        return text, 0

    anonymized_result = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators={
            "PERSON": OperatorConfig(
                "replace",
                {"new_value": "[NAME_REDACTED]"}
            )
        }
    )

    return anonymized_result.text, names_found



@app.get("/")
def home():
    return {"message": "Backend Working"}



@app.post("/redact")
@limiter.limit("10/minute")
def redact(request: Request, data: TextInput):

    # Email Redaction
    email_count = len(EMAIL_PATTERN.findall(data.text))
    redacted_text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", data.text)

    # Phone Redaction
    phone_count = len(PHONE_PATTERN.findall(redacted_text))
    redacted_text = PHONE_PATTERN.sub("[PHONE_REDACTED]", redacted_text)

    # IP Redaction
    ip_count = len(IP_PATTERN.findall(redacted_text))
    redacted_text = IP_PATTERN.sub("[IP_REDACTED]", redacted_text)

    # Name Redaction (Presidio)
    redacted_text, name_count = redact_names(redacted_text)

    mrn_count = len(MRN_PATTERN.findall(redacted_text))
    redacted_text = MRN_PATTERN.sub(
    "[MRN_REDACTED]",
    redacted_text
)

    return {
        "status": "success",
        "redacted_text": redacted_text,
        "emails_found": email_count,
        "phones_found": phone_count,
        "ips_found": ip_count,
        "names_found": name_count,
        "mrns_found": mrn_count
    }