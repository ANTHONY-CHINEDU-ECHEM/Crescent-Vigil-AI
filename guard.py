"""Input guard: redaction and request classification.

Runs before anything is retrieved or logged. Identifiers are replaced with
typed placeholders, and the request is classified so that dose requests,
attempts to override the plan or the system, crisis disclosures, out of scope
populations and off topic questions follow fixed, safe paths.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

REDACTIONS = [
    ("NHS_NUMBER", re.compile(r"\b\d{3}[ \-]?\d{3}[ \-]?\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+]+@[\w]+(?:\.[\w]+)+\b")),
    ("PHONE", re.compile(r"(?:\+44\s?7\d{3}|\b07\d{3})\s?\d{3}\s?\d{3}\b")),
    ("DATE", re.compile(r"\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b")),
    ("POSTCODE", re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", re.I)),
    ("HOSPITAL_NUMBER", re.compile(r"\b(?:MRN|hospital (?:no|number))[:\s#]*[A-Z0-9]{5,}\b", re.I)),
    ("NAME", re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Mx|Dr)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?")),
    ("NAME", re.compile(r"\b(?:patient(?:'s)? name|name)\s*(?:is|:)\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", re.I)),
]

INJECTION = re.compile(
    r"ignore (?:all |any |the |your )?(?:previous |prior )?(?:instructions|rules|plan|guidance|guidelines)|"
    r"disregard (?:the |your )?(?:plan|guidance|rules|instructions)|override (?:the )?(?:plan|guard|system)|"
    r"you are now|system prompt|developer mode|pretend (?:to be|you)|jailbreak", re.I)
DOSE = re.compile(r"\b(?:what|which|how much|how many|calculate|right|correct|max(?:imum)?)\b[^?.]{0,40}\b(?:dose|dosage|mg|milligrams?|micrograms?|ml)\b|"
                  r"\bmg\s*/\s*kg\b|\bdose of\b|\bdosing\b|\bhow much\b[^?.]{0,30}\b(?:give|run|use|start|infuse|prescribe|draw up)\b", re.I)
CRISIS = re.compile(r"self harm|harm (?:him|her|them)self|kill (?:my|him|her|them)sel|end it all|suicid|end (?:his|her|their|my) life|want to die", re.I)
PAEDS = re.compile(r"\b(?:child|children|paediatric|pediatric|infant|baby|toddler|(?:[1-9]|1[0-5])\s*(?:year|yr)s?\s*old)\b", re.I)
PREGNANCY = re.compile(r"\bpregnan", re.I)
PETHIDINE = re.compile(r"\bpethidine|meperidine\b", re.I)
DOMAIN = re.compile(r"sickle|crisis|pain|analges|opioid|morphine|oxycodone|diamorphine|plan|chest|oxygen|sat|fever|temperature|"
                    r"spleen|haemoglobin|\bhb\b|stroke|priapism|transfus|haematolog|spirometr|discharge|admi|observation|"
                    r"triage|sepsis|reassess|nsaid|ibuprofen|paracetamol|ketamine|pethidine|dose|breath|cough|weakness|seizure|"
                    r"pregnan|child|alert|risk|deteriorat|x ray|xray|blood|fluid|nurse|patient|hydroxyurea|ward|icu|critical care|meperidine|"
                    r"ketamine|naloxone|sedat|spleen|urolog", re.I)


@dataclass
class GuardResult:
    redacted: str
    original_sha256: str
    redactions: list = field(default_factory=list)
    flags: list = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return "injection" in self.flags or "off_topic" in self.flags


def redact(text: str) -> tuple[str, list]:
    found = []
    out = text
    for label, rx in REDACTIONS:
        def sub(m, label=label):
            found.append(label)
            return f"[{label}]"
        out = rx.sub(sub, out)
    return out, found


def check(text: str) -> GuardResult:
    text = text or ""
    red, found = redact(text)
    flags = []
    if INJECTION.search(text):
        flags.append("injection")
    if DOSE.search(text):
        flags.append("dose_request")
    if CRISIS.search(text):
        flags.append("crisis")
    if PAEDS.search(text):
        flags.append("paediatric_scope")
    if PREGNANCY.search(text):
        flags.append("pregnancy_scope")
    if PETHIDINE.search(text):
        flags.append("pethidine")
    if text.strip() and not DOMAIN.search(text) and "crisis" not in flags:
        flags.append("off_topic")
    return GuardResult(red, hashlib.sha256(text.encode()).hexdigest(), found, flags)
