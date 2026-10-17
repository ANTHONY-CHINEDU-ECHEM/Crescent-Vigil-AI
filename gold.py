"""Reference decision table for scenario evaluation.

This is an independent, deliberately plain implementation of what the guidance
cards require at a given moment of an attendance. It shares only the snapshot
reader with the copilot. It is frozen together with the scenarios before the
copilot is built, and the copilot is scored against it.

Each action code also lists the guidance cards that may legitimately be cited
for it, so citation correctness can be scored.
"""
from __future__ import annotations

from .. import config as C

PAIN_LIKE = {"pain", "chest", "abdominal", "priapism"}

# action code -> cards acceptable as its citation
ACTION_CARDS = {
    "GIVE_FIRST_ANALGESIA": {"G001", "G002", "G006", "G049", "G050"},
    "FOLLOW_PLAN": {"G003", "G064"},
    "USE_DEPARTMENT_PROTOCOL": {"G006", "G001", "G038"},
    "AVOID_PETHIDINE": {"G007"},
    "ADJUNCT_PARACETAMOL": {"G008"},
    "ADJUNCT_NSAID": {"G009"},
    "NO_NSAID": {"G009"},
    "REASSESS_PAIN": {"G010", "G013"},
    "MONITOR_AFTER_OPIOID": {"G011", "G012"},
    "INFORM_HAEMATOLOGY": {"G015", "G037"},
    "INCENTIVE_SPIROMETRY": {"G018", "G057"},
    "FOUR_HOURLY_OBS": {"G044", "G010", "G045"},
    "SEPSIS_SCREEN": {"G027", "G028", "G029"},
    "REVIEW_CHEST": {"G021", "G020", "G046", "G047", "G022"},
    "CHEST_XRAY_AT_ARRIVAL": {"G022", "G019"},
    "OPIOID_TOXICITY_REVIEW": {"G012", "G026"},
    "STROKE_PATHWAY": {"G030", "G031"},
    "UROLOGY_REVIEW": {"G032"},
    "ACUTE_ANAEMIA_REVIEW": {"G033", "G034", "G035"},
    "PLAN_REVIEW_DUE": {"G039", "G040"},
    "ASK_HOME_ANALGESIA": {"G004"},
}

RED_FLAG_CODES = {"SEPSIS_SCREEN", "REVIEW_CHEST", "CHEST_XRAY_AT_ARRIVAL", "OPIOID_TOXICITY_REVIEW",
                  "STROKE_PATHWAY", "UROLOGY_REVIEW", "ACUTE_ANAEMIA_REVIEW"}


def expected(snap: dict, P=C.PROTOCOL) -> dict:
    now = snap["now_min"]
    d = snap["derived"]
    a = snap["attendance"]
    pt = snap["patient"]
    plan = snap["plan"]
    v = snap["vitals"]
    labs = snap["labs"]
    codes: set[str] = set()
    overdue: set[str] = set()
    complaint = a["complaint"]
    gone = d["left_department"] or d["discharged"]
    if gone:
        return {"codes": [], "overdue": [], "agent": None, "route": None, "forbidden": ["pethidine"]}

    given = d["analgesia_given_min"]
    if complaint in PAIN_LIKE and given is None:
        codes.add("GIVE_FIRST_ANALGESIA")
        codes.add("ASK_HOME_ANALGESIA")
        codes.add("AVOID_PETHIDINE")
        if now > P.analgesia_target_min:
            overdue.add("GIVE_FIRST_ANALGESIA")
        if plan:
            codes.add("FOLLOW_PLAN")
        else:
            codes.add("USE_DEPARTMENT_PROTOCOL")
        codes.add("ADJUNCT_PARACETAMOL")
        nsaid_blocked = pt["renal_impairment"] or (plan and "NSAIDs" in plan["avoid"])
        codes.add("NO_NSAID" if nsaid_blocked else "ADJUNCT_NSAID")

    adm = d["admitted_min"]
    on_ward = adm is not None and now >= adm
    if given is not None and not on_ward:
        since = now - given
        if since <= 120:
            codes.add("MONITOR_AFTER_OPIOID")
            if d["reassessed_min"] is None:
                codes.add("REASSESS_PAIN")
                if since >= P.reassess_interval_min:
                    overdue.add("REASSESS_PAIN")
    if on_ward:
        hrs = (now - adm) / 60
        if hrs <= 24:
            codes.add("INFORM_HAEMATOLOGY")
        codes.add("INCENTIVE_SPIROMETRY")
        codes.add("FOUR_HOURLY_OBS")

    # Red flags from the latest observations and results.
    if v:
        if v["temp"] >= P.temp_flag:
            codes.add("SEPSIS_SCREEN")
        if v["spo2"] < P.spo2_flag or (pt["baseline_spo2"] - v["spo2"]) >= P.spo2_drop_flag:
            codes.add("REVIEW_CHEST")
        if v["rr"] >= P.rr_flag:
            codes.add("REVIEW_CHEST")
        if v["rr"] <= P.rr_low_flag:
            codes.add("OPIOID_TOXICITY_REVIEW")
    if complaint == "chest" and now <= 240 and not on_ward:
        codes.add("CHEST_XRAY_AT_ARRIVAL")
    if complaint == "neuro":
        codes.add("STROKE_PATHWAY")
    if complaint == "priapism":
        codes.add("UROLOGY_REVIEW")
    if labs.get("hb") is not None and pt["steady_state_hb"] - labs["hb"] >= P.hb_drop_flag:
        codes.add("ACUTE_ANAEMIA_REVIEW")
    if plan and plan["days_since_review"] > 365:
        codes.add("PLAN_REVIEW_DUE")

    forbidden = {"pethidine"}
    if plan:
        forbidden |= {x for x in plan["avoid"] if x != "NSAIDs"}
    return {
        "codes": sorted(codes),
        "overdue": sorted(overdue),
        "agent": plan["first_line_agent"] if plan and "FOLLOW_PLAN" in codes else None,
        "route": plan["route"] if plan and "FOLLOW_PLAN" in codes else None,
        "forbidden": sorted(forbidden),
    }
