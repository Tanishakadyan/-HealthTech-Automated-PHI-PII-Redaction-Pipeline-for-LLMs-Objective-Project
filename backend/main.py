from fastapi import FastAPI
from pydantic import BaseModel, Field
import re

app = FastAPI()

EMAIL_PATTERN = re.compile(
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+'
)
PHONE_PATTERN = re.compile(
    r'\b\d{10}\b'
)

@app.get("/")
def home():
    return {"message": "Backend Working"}

class TextInput(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Input text for PII redaction"
    )

@app.post("/redact")
def redact(data: TextInput):

    email_count = len(
        EMAIL_PATTERN.findall(data.text)
    )

    redacted_text = EMAIL_PATTERN.sub(
        "[EMAIL_REDACTED]",
        data.text
    )
    phone_count = len(
    PHONE_PATTERN.findall(redacted_text)
)

    redacted_text = PHONE_PATTERN.sub(
        "[PHONE_REDACTED]",
    redacted_text
)

    return {
        "status": "success",
        "redacted_text": redacted_text,
        "emails_found": email_count,
        "phones_found": phone_count
    }