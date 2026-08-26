"""Deterministic (non-LLM) extraction of common tender fields from a
document's extracted text.

This is regex/heuristic pattern matching, not an agent call: every field
in the result was literally found in the source text via a matched
pattern, or is left null/empty. Nothing here is inferred or generated —
that discipline matters because Tender.extracted_requirements is shown to
users as "what this tender document says", not "what an AI thinks this
tender document says".
"""

import json
import re
from dataclasses import asdict, dataclass

_CLOSING_DATE_PATTERN = re.compile(
    r"(?:last date|closing date|due date|submission deadline|bid submission end date)"
    r"\s*(?:for submission)?\s*[:\-]?\s*"
    r"([0-9]{1,2}[-/. ][A-Za-z0-9]{2,9}[-/. ][0-9]{2,4})",
    re.IGNORECASE,
)

_EMD_PATTERN = re.compile(
    r"(?:EMD|Earnest Money Deposit)\s*(?:\(Rs\.?\))?\s*[:\-]?\s*(?:Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    re.IGNORECASE,
)

_TENDER_REF_PATTERN = re.compile(
    r"(?:tender\s*(?:no\.?\b|number\b|ref\.?(?:erence)?\b)\s*[:\-]?\s*)([A-Za-z0-9/_\-]{4,40})",
    re.IGNORECASE,
)

_ELIGIBILITY_KEYWORDS = (
    "eligib",
    "pre-qualification",
    "prequalification",
    "qualifying criteria",
    "minimum turnover",
    "shall have experience",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

MAX_ELIGIBILITY_SNIPPETS = 5


@dataclass
class ExtractedTenderFields:
    closing_date_text: str | None
    emd_amount_text: str | None
    tender_ref: str | None
    eligibility_snippets: list[str]

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> "ExtractedTenderFields":
        data = json.loads(raw)
        return cls(**data)


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _eligibility_snippets(text: str) -> list[str]:
    snippets: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(text):
        sentence = sentence.strip()
        if not sentence:
            continue
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in _ELIGIBILITY_KEYWORDS):
            snippets.append(sentence)
        if len(snippets) >= MAX_ELIGIBILITY_SNIPPETS:
            break
    return snippets


def extract_tender_fields(text: str) -> ExtractedTenderFields:
    """Pure function: same input always yields the same output, and any
    field the patterns don't find comes back null/empty rather than guessed.
    """
    return ExtractedTenderFields(
        closing_date_text=_first_match(_CLOSING_DATE_PATTERN, text),
        emd_amount_text=_first_match(_EMD_PATTERN, text),
        tender_ref=_first_match(_TENDER_REF_PATTERN, text),
        eligibility_snippets=_eligibility_snippets(text),
    )
