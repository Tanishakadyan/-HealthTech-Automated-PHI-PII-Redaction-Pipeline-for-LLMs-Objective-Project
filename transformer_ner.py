from transformers import pipeline

ner_pipeline = pipeline(
    "ner",
    model="dslim/bert-base-NER",
    aggregation_strategy="simple"
)

def detect_names_transformer(text):
    entities = ner_pipeline(text)

    names = []

    current_name = ""
    start_pos = None
    end_pos = None

    for entity in entities:

        if entity["entity_group"] != "PER":
            continue

        word = entity["word"]

        if word.startswith("##"):
            current_name += word.replace("##", "")
            end_pos = entity["end"]

        else:
            if current_name:
                names.append({
                    "name": current_name,
                    "start": start_pos,
                    "end": end_pos
                })

            current_name = word
            start_pos = entity["start"]
            end_pos = entity["end"]

    if current_name:
        names.append({
            "name": current_name,
            "start": start_pos,
            "end": end_pos
        })

    return names