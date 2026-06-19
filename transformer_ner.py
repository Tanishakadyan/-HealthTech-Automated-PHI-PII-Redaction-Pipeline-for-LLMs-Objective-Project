from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("PHI_NER_MODEL", "dslim/bert-base-NER")
NAME_REDACTION_TOKEN = "[NAME_REDACTED]"

_NER_PIPELINE = None


TITLE_WORDS = {
    "dr",
    "doctor",
    "mr",
    "mrs",
    "ms",
    "miss",
    "prof",
    "professor",
}

IGNORE_WORDS = {
    "admission",
    "admitted",
    "address",
    "age",
    "allergy",
    "appointment",
    "blood",
    "bp",
    "clinic",
    "contact",
    "diagnosis",
    "discharge",
    "dob",
    "doctor",
    "dose",
    "drug",
    "email",
    "female",
    "follow",
    "hospital",
    "hypertension",
    "id",
    "lab",
    "laboratory",
    "male",
    "medication",
    "medicine",
    "mri",
    "mrn",
    "name",
    "nurse",
    "patient",
    "phone",
    "physician",
    "prescription",
    "provider",
    "review",
    "reviewed",
    "signed",
    "surgery",
    "symptom",
    "treatment",
    "ward",
}

MONTHS_AND_DAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "jan",
    "january",
    "feb",
    "february",
    "mar",
    "march",
    "apr",
    "april",
    "may",
    "jun",
    "june",
    "jul",
    "july",
    "aug",
    "august",
    "sep",
    "sept",
    "september",
    "oct",
    "october",
    "nov",
    "november",
    "dec",
    "december",
}

STOP_WORDS = IGNORE_WORDS | MONTHS_AND_DAYS | TITLE_WORDS
NAME_TOKEN_PATTERN = r"(?:[A-Z]\.|[A-Z][A-Za-z'-]*)"
NAME_SEQUENCE_PATTERN = rf"{NAME_TOKEN_PATTERN}(?:\s+{NAME_TOKEN_PATTERN}){{0,3}}"

TITLE_NAME_PATTERN = re.compile(
    r"\b(?P<title>(?i:Dr|Doctor|Mr|Mrs|Ms|Miss|Prof|Professor))\.?\s*"
    rf"(?P<name>{NAME_SEQUENCE_PATTERN})\b"
)

CONTEXT_NAME_PATTERN = re.compile(
    r"\b(?i:"
    r"patient(?:\s+name)?|pt|name|doctor\s+name|provider|physician|clinician|"
    r"guardian|contact|attending|surgeon|consultant|referred\s+by|seen\s+by|"
    r"reviewed\s+by|signed\s+by|sent\s+to|send\s+to|email\s+to|to|by"
    r")\b\s*(?i:is|was|:|-)?\s+"
    rf"(?P<name>{NAME_SEQUENCE_PATTERN})\b",
)

NAME_BEFORE_ROLE_PATTERN = re.compile(
    rf"\b(?P<name>{NAME_TOKEN_PATTERN}(?:\s+{NAME_TOKEN_PATTERN}){{0,2}})\s+"
    r"(?i:is|was)\s+(?i:the\s+)?"
    r"(?i:patient|referring\s+physician|physician|doctor|surgeon|consultant)\b",
)

NAME_BEFORE_ACTION_PATTERN = re.compile(
    rf"(?<![\w@.])(?P<name>{NAME_TOKEN_PATTERN}(?:\s+{NAME_TOKEN_PATTERN}){{0,2}})\s+"
    r"(?=visited|was\s+admitted|was\s+referred|consulted|met|called|reported)\b"
)

TITLE_PREFIX_PATTERN = re.compile(
    r"^(?P<title>(?i:Dr|Doctor|Mr|Mrs|Ms|Miss|Prof|Professor))"
    r"(?P<separator>\.?\s*)"
)


@dataclass(frozen=True)
class NameEntity:
    text: str
    start: int
    end: int
    score: float = 1.0
    source: str = "unknown"

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.text,
            "start": self.start,
            "end": self.end,
            "score": self.score,
            "source": self.source,
        }


def get_ner_pipeline():
    """Load the Hugging Face NER pipeline lazily so app imports stay fast."""
    global _NER_PIPELINE
    if _NER_PIPELINE is None:
        from transformers import pipeline

        _NER_PIPELINE = pipeline(
            "ner",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            aggregation_strategy="simple",
        )
    return _NER_PIPELINE


def _clean_name_text(value: str) -> str:
    value = value.replace("##", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n,;:()[]{}")


def _is_valid_name_text(value: str) -> bool:
    cleaned = _clean_name_text(value)
    if not cleaned or len(cleaned) < 2:
        return False
    if any(char.isdigit() for char in cleaned):
        return False
    if "@" in cleaned or "/" in cleaned or "\\" in cleaned:
        return False

    tokens = [token.strip(".") for token in re.split(r"\s+", cleaned) if token.strip(".")]
    if not tokens or len(tokens) > 4:
        return False

    meaningful_tokens = [token for token in tokens if token.lower() not in TITLE_WORDS]
    if not meaningful_tokens:
        return False

    for token in meaningful_tokens:
        normalized = token.lower().strip(".'-")
        if normalized in STOP_WORDS:
            return False
        if len(normalized) < 2:
            return False
        if token.isupper() and len(token) > 1:
            return False

    return True


def _coerce_entity(entity: NameEntity | Mapping[str, object]) -> NameEntity:
    if isinstance(entity, NameEntity):
        return entity

    text_value = str(entity.get("name") or entity.get("text") or entity.get("word") or "")
    start = int(entity["start"])
    end = int(entity["end"])
    score = float(entity.get("score", 1.0))
    source = str(entity.get("source", "unknown"))
    return NameEntity(text=_clean_name_text(text_value), start=start, end=end, score=score, source=source)


def _iter_chunks(text: str, max_chars: int = 1200) -> Iterable[tuple[int, str]]:
    if len(text) <= max_chars:
        yield 0, text
        return

    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            split_at = max(
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
                text.rfind(" ", start, end),
            )
            if split_at > start + 200:
                end = split_at + 1

        yield start, text[start:end]
        start = end


def _detect_with_transformer(text: str) -> list[NameEntity]:
    if os.getenv("DISABLE_TRANSFORMER_NER", "").lower() in {"1", "true", "yes"}:
        return []

    detected: list[NameEntity] = []
    try:
        ner = get_ner_pipeline()
        for offset, chunk in _iter_chunks(text):
            for entity in ner(chunk):
                entity_group = str(entity.get("entity_group") or entity.get("entity") or "")
                if entity_group.upper() not in {"PER", "PERSON", "B-PER", "I-PER"}:
                    continue

                start = offset + int(entity["start"])
                end = offset + int(entity["end"])
                value = _clean_name_text(text[start:end] or str(entity.get("word", "")))
                if _is_valid_name_text(value):
                    detected.append(
                        NameEntity(
                            text=value,
                            start=start,
                            end=end,
                            score=float(entity.get("score", 0.0)),
                            source="transformer",
                        )
                    )
    except Exception as exc:
        logger.warning("Transformer NER unavailable; continuing with rule-based name detection: %s", exc)

    return detected


def _detect_title_names(text: str) -> list[NameEntity]:
    entities: list[NameEntity] = []
    for match in TITLE_NAME_PATTERN.finditer(text):
        name = _clean_name_text(match.group("name"))
        if _is_valid_name_text(name):
            entities.append(
                NameEntity(
                    text=name,
                    start=match.start("name"),
                    end=match.end("name"),
                    score=0.99,
                    source="title_rule",
                )
            )
    return entities


def _detect_context_names(text: str) -> list[NameEntity]:
    entities: list[NameEntity] = []
    for pattern, source, score in (
        (CONTEXT_NAME_PATTERN, "context_rule", 0.9),
        (NAME_BEFORE_ROLE_PATTERN, "role_rule", 0.88),
        (NAME_BEFORE_ACTION_PATTERN, "action_rule", 0.86),
    ):
        for match in pattern.finditer(text):
            name = _clean_name_text(match.group("name"))
            if _is_valid_name_text(name):
                entities.append(
                    NameEntity(
                        text=name,
                        start=match.start("name"),
                        end=match.end("name"),
                        score=score,
                        source=source,
                    )
                )
    return entities


def _can_merge(text: str, left: NameEntity, right: NameEntity) -> bool:
    if right.start < left.end:
        return True

    gap = text[left.end:right.start]
    if len(gap) > 3:
        return False
    if not re.fullmatch(r"[\s.'-]*", gap):
        return False

    left_text = _clean_name_text(left.text)
    right_text = _clean_name_text(right.text)
    if left_text.lower().rstrip(".") in TITLE_WORDS:
        return True
    return _is_valid_name_text(left_text) and _is_valid_name_text(right_text)


def _merge_adjacent(text: str, entities: Sequence[NameEntity | Mapping[str, object]]) -> list[NameEntity]:
    ordered = sorted((_coerce_entity(entity) for entity in entities), key=lambda item: (item.start, item.end))
    merged: list[NameEntity] = []

    for entity in ordered:
        if entity.start < 0 or entity.end > len(text) or entity.start >= entity.end:
            continue

        if not merged:
            merged.append(entity)
            continue

        current = merged[-1]
        if _can_merge(text, current, entity):
            start = min(current.start, entity.start)
            end = max(current.end, entity.end)
            merged[-1] = NameEntity(
                text=_clean_name_text(text[start:end]),
                start=start,
                end=end,
                score=max(current.score, entity.score),
                source=f"{current.source}+{entity.source}",
            )
        else:
            merged.append(entity)

    return merged


def _strip_title_from_span(text: str, entity: NameEntity) -> NameEntity:
    raw_span = text[entity.start:entity.end]
    match = TITLE_PREFIX_PATTERN.match(raw_span)
    if not match:
        return entity

    new_start = entity.start + match.end()
    while new_start < entity.end and text[new_start].isspace():
        new_start += 1

    if new_start >= entity.end:
        return entity

    cleaned = _clean_name_text(text[new_start:entity.end])
    return NameEntity(
        text=cleaned,
        start=new_start,
        end=entity.end,
        score=entity.score,
        source=entity.source,
    )


def _post_process(text: str, entities: Sequence[NameEntity | Mapping[str, object]]) -> list[NameEntity]:
    normalized: list[NameEntity] = []
    for raw_entity in entities:
        entity = _coerce_entity(raw_entity)
        entity = _strip_title_from_span(text, entity)
        value = _clean_name_text(text[entity.start:entity.end] or entity.text)
        if not _is_valid_name_text(value):
            continue
        normalized.append(
            NameEntity(
                text=value,
                start=entity.start,
                end=entity.end,
                score=entity.score,
                source=entity.source,
            )
        )

    merged = _merge_adjacent(text, normalized)
    return [_strip_title_from_span(text, entity) for entity in merged if _is_valid_name_text(entity.text)]


def post_process_name_entities(
    text: str,
    entities: Sequence[NameEntity | Mapping[str, object]],
) -> list[NameEntity]:
    """Public wrapper for span cleanup used by the API layer."""
    return _post_process(text, entities)


def build_redacted_text(
    text: str,
    entities: Sequence[NameEntity | Mapping[str, object]],
    replacement: str = NAME_REDACTION_TOKEN,
) -> str:
    processed = _post_process(text, entities)
    redacted = text
    for entity in sorted(processed, key=lambda item: (item.start, item.end), reverse=True):
        redacted = redacted[: entity.start] + replacement + redacted[entity.end :]
    return redacted


def detect_name_entities(text: str) -> list[NameEntity]:
    """
    Detect likely person-name spans using transformer NER plus conservative
    healthcare-specific title and context rules.
    """
    if not text:
        return []

    candidates: list[NameEntity] = []
    candidates.extend(_detect_with_transformer(text))
    candidates.extend(_detect_title_names(text))
    candidates.extend(_detect_context_names(text))
    return _post_process(text, candidates)


def detect_names_transformer(text: str) -> list[dict[str, object]]:
    """
    Backward-compatible public API used by the FastAPI app and evaluation script.

    Returns:
    [
        {"name": "John Smith", "start": 12, "end": 22, "score": 0.98, "source": "..."}
    ]
    """
    return [entity.as_dict() for entity in detect_name_entities(text)]


if __name__ == "__main__":
    sample_text = "Patient John Smith visited Dr. Ashwin on 12/03/2025. Email: john@gmail.com"
    for item in detect_names_transformer(sample_text):
        print(item)
