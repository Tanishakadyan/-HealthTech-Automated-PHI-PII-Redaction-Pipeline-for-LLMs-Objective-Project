from transformer_ner import detect_names_transformer

text = "Dr. Arun Raj reviewed patient Sathish Kumar"

results = detect_names_transformer(text)

print(results)