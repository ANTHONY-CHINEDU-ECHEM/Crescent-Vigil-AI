"""Passages the copilot can cite.

Three kinds of passage share one schema:

    guidance  cards paraphrasing published recommendations (knowledge/guidance_cards.md)
    plan      the sections of the patient's own signed care plan
    history   summaries of the patient's previous attendances

Guidance cards are static and indexed once. Plan and history passages are made
per snapshot, so retrieval always sees the patient's own record first.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from .. import config as C

PHASES = ("arrival", "early", "ward", "late", "discharge")
SOURCES = {}


@dataclass
class Passage:
    pid: str
    kind: str
    title: str
    body: str
    source: str = ""
    phases: list = field(default_factory=list)
    situations: list = field(default_factory=list)
    entities: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @property
    def text(self) -> str:
        return f"{self.title}. {self.body}"


def parse_cards(path=C.KNOWLEDGE / "guidance_cards.md") -> list[Passage]:
    text = open(path, encoding="utf8").read()
    head, _, body = text.partition("\n---\n")
    for m in re.finditer(r"^(S\d+)\s+(.+)$", head, flags=re.M):
        SOURCES[m.group(1)] = m.group(2).strip()
    cards = []
    for block in re.split(r"\n(?=## G\d{3} )", body):
        block = block.strip()
        if not block.startswith("## G"):
            continue
        lines = block.splitlines()
        m = re.match(r"## (G\d{3}) (.+)", lines[0])
        meta, rest = {}, []
        for ln in lines[1:]:
            mm = re.match(r"^(source|phase|situations|entities):\s*(.*)$", ln)
            if mm and not rest:
                meta[mm.group(1)] = mm.group(2).strip()
            elif ln.strip() or rest:
                rest.append(ln)
        phases = [p.strip() for p in meta.get("phase", "any").split(",")]
        if "any" in phases:
            phases = list(PHASES)
        cards.append(Passage(
            pid=m.group(1), kind="guidance", title=m.group(2).strip(), body=" ".join(x.strip() for x in rest if x.strip()),
            source=meta.get("source", ""), phases=phases,
            situations=[s.strip() for s in meta.get("situations", "").split(",") if s.strip()],
            entities=[s.strip() for s in meta.get("entities", "").split(",") if s.strip()],
        ))
    return cards


def source_text(code: str) -> str:
    if not SOURCES:
        parse_cards()
    return "; ".join(SOURCES.get(c.strip(), c.strip()) for c in code.split(","))


def plan_passages(plan: dict | None) -> list[Passage]:
    if not plan:
        return []
    pid = plan["plan_id"]
    out = [
        Passage(f"{pid}.A", "plan", "First line analgesia in the individual plan",
                f"The signed plan names {plan['first_line_agent']} by the {plan['route']} route as first line analgesia. "
                f"{plan['dose_text']}.", "individual care plan", list(PHASES[:3]), ["pain", "plan"],
                ["care plan", plan["first_line_agent"], plan["route"], "analgesia", "first line"]),
        Passage(f"{pid}.B", "plan", "Agents to avoid in the individual plan",
                "The plan says to avoid " + ", ".join(plan["avoid"]) + "."
                + (f" Documented intolerance of {plan['intolerance']}." if plan.get("intolerance") else ""),
                "individual care plan", list(PHASES), ["pain", "plan", "safety"],
                ["avoid", "contraindication"] + plan["avoid"]),
        Passage(f"{pid}.C", "plan", "Adjuncts and reassessment in the individual plan",
                "The plan lists " + " and ".join(plan["adjuncts"]) + f" as adjuncts and asks for pain reassessment every {plan['reassess_min']} minutes.",
                "individual care plan", list(PHASES[:3]), ["pain", "plan", "monitoring"],
                ["adjunct", "reassessment"] + plan["adjuncts"]),
        Passage(f"{pid}.D", "plan", "Clinical notes in the individual plan", plan["notes"],
                "individual care plan", list(PHASES), ["plan", "admission", "chest"],
                ["haematology", "notes", "route preference"]),
    ]
    return out


def history_passages(history: dict, patient_id: str) -> list[Passage]:
    out = []
    if history["attendances"]:
        out.append(Passage(
            f"H.{patient_id}.S", "history", "Summary of previous attendances",
            f"{history['attendances']} previous attendances with {history['admissions']} admissions; acute chest syndrome "
            f"after admission {history['acs_after_admission']} times and at arrival {history['acs_at_arrival']} times."
            + (f" Median previous door to analgesia {history['median_door_to_analgesia_min']:.0f} minutes."
               if history.get("median_door_to_analgesia_min") is not None else ""),
            "patient record", list(PHASES), ["history", "chest"], ["previous attendances", "acute chest syndrome", "history"]))
    for i, r in enumerate(history.get("recent", [])):
        parts = [f"Attendance on {r['arrival']} with {r['complaint']}"]
        if r["first_agent"]:
            parts.append(f"first analgesia {r['first_agent']} {r['first_route']} at {r['door_to_analgesia_min']:.0f} minutes")
        parts.append("admitted" if r["admitted"] else "discharged from the department")
        if r["acs"]:
            parts.append(f"acute chest syndrome diagnosed {r['acs_diagnosis_h']:.0f} hours into the episode" if r["acs_diagnosis_h"] else "acute chest syndrome diagnosed")
        out.append(Passage(f"H.{patient_id}.{i + 1}", "history", f"Previous attendance {r['arrival']}",
                           "; ".join(parts) + ".", "patient record", list(PHASES), ["history"],
                           ["previous attendance", r["complaint"]]))
    return out


def write_cards_json(path=C.INDEX / "guidance_cards.json") -> list[Passage]:
    cards = parse_cards()
    path.write_text(json.dumps({"cards": [c.to_dict() for c in cards], "sources": SOURCES}, indent=1))
    return cards
