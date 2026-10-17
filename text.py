"""Tokeniser shared by indexing, querying and the TypeScript port.

Rules are intentionally simple and fully specified so the browser engine can
reproduce them exactly: canonicalise with the synonym list, lower case, split
on anything that is not a letter or digit, drop stop words, strip a small set
of English suffixes.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from .. import config as C

STOP = set("""a an and are as at be been but by can could do does doing done for from had has have how i if in into is it its
just me my no nor not of on or our out over should so some such than that the their them then there these they this to too
under until up us very was we were what when where which while who why will with would you your yet any all also may might
must shall about after before again further once here both each few more most other own same only s t now get got still
being been ok okay""".split())


@lru_cache(maxsize=1)
def synonym_rules():
    rules = json.loads((C.KNOWLEDGE / "synonyms.json").read_text())["rules"]
    return [(re.compile(r"\b(?:" + pat + r")\b", re.I), rep) for pat, rep in rules]


def canonical(text: str) -> str:
    t = text.lower().replace("-", " ")
    for rx, rep in synonym_rules():
        t = rx.sub(rep, t)
    return t


def stem(w: str) -> str:
    if len(w) <= 4 or w.isdigit():
        return w
    if w.endswith("ies") and len(w) > 5:
        return w[:-3] + "y"
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def tokens(text: str) -> list[str]:
    t = canonical(text)
    return [stem(w) for w in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", t) if w not in STOP]
