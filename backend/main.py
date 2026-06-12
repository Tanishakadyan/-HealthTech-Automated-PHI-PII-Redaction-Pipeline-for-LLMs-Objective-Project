from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()

@app.get("/")
def home():
    return {"message": "Backend Working"}

class TextInput(BaseModel):
    text: str

@app.post("/redact")
def redact(data: TextInput):
    return {
        "status": "success",
        "received_text": data.text
    }