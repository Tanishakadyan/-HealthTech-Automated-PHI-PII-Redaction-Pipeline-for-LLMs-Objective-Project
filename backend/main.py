from fastapi import FastAPI
from pydantic import BaseModel, Field
import re

app = FastAPI()

# Pre-compiled regex pattern
EMAIL_PATTERN = re.compile(
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
)

@app.get("/")
def home():
    return {"message": "Backend Working"}

class TextInput(BaseModel):
    text: str = Field(
        ...,
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

    return {
        "status": "success",
        "redacted_text": redacted_text,
        "emails_found": email_count
    }