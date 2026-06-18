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
from transformer_ner import detect_names_transformer
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
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
)


PHONE_PATTERN = re.compile(
    r'\b(?:\+?\d{1,3}[\s\-.])?'
    r'(?:\(?\d{3}\)?[\s\-.])\d{3}[\s\-.]\d{4}\b'
)

IP_PATTERN = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
)

MRN_PATTERN = re.compile(
    r'\b(?:MRN|Medical Record Number)\s*[:#=]?\s*\d+\b',
    re.IGNORECASE
)


DOB_PATTERN = re.compile(
    r'\b(?:'
    r'\d{2}[/-]\d{2}[/-]\d{4}'                                          
    r'|\d{4}[/-]\d{2}[/-]\d{2}'                                        
    r'|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May'
    r'|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?'
    r'|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}'               
    r'|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?'
    r'|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?'
    r'|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}'                            
    r')\b',
    re.IGNORECASE
)

ADDRESS_PATTERN = re.compile(
    r'\b\d{1,5}\s+[A-Za-z0-9\s,.-]+'
    r'(?:Street|St|Road|Rd|Nagar|Colony|Avenue|Ave|Lane|Ln|Block|Blvd|Drive|Dr)\b',
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

    
    transformer_results = detect_names_transformer(text)

    if transformer_results:
        redacted_text = text

        for entity in sorted(
            transformer_results,
            key=lambda x: x["start"],
            reverse=True
        ):
            redacted_text = (
                redacted_text[:entity["start"]]
                + "[NAME_REDACTED]"
                + redacted_text[entity["end"]:]
            )

        return redacted_text, len(transformer_results)

    
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
@limiter.limit("30/minute")
def home(request: Request):
    return {"message": "Backend Working"}


@app.post("/redact")
@limiter.limit("10/minute")
def redact(request: Request, data: TextInput):

    
    email_count = len(EMAIL_PATTERN.findall(data.text))
    phone_count = len(PHONE_PATTERN.findall(data.text))
    ip_count = len(IP_PATTERN.findall(data.text))
    mrn_count = len(MRN_PATTERN.findall(data.text))
    dob_count = len(DOB_PATTERN.findall(data.text))
    address_count = len(ADDRESS_PATTERN.findall(data.text))


    redacted_text, name_count = redact_names(data.text)

    
    redacted_text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", redacted_text)
    redacted_text = PHONE_PATTERN.sub("[PHONE_REDACTED]", redacted_text)
    redacted_text = IP_PATTERN.sub("[IP_REDACTED]", redacted_text)
    redacted_text = MRN_PATTERN.sub("[MRN_REDACTED]", redacted_text)
    redacted_text = DOB_PATTERN.sub("[DOB_REDACTED]", redacted_text)
    redacted_text = ADDRESS_PATTERN.sub("[ADDRESS_REDACTED]", redacted_text)

    return {
        "status": "success",
        "redacted_text": redacted_text,
        "emails_found": email_count,
        "phones_found": phone_count,
        "ips_found": ip_count,
        "names_found": name_count,
        "mrns_found": mrn_count,
        "dobs_found": dob_count,
        "addresses_found": address_count,
    }