from transformers import pipeline

ner = pipeline(
    "ner",
    model="dslim/bert-base-NER",
    aggregation_strategy="simple"
)

texts = [
    "My name is Sathish Kumar",
    "Dr. Arun Raj works at Apollo Hospital",
    "Patient Name: Priya Sharma",
    "Karthi Kumar reviewed the report"
]

for text in texts:
    print("\nText:", text)
    print(ner(text))