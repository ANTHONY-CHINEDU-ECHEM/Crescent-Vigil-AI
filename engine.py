"""Clock and red flag engine.

Turns a snapshot into a list of actions. Each action carries the record facts
that triggered it and a retrieval query; the composer finds the guidance that
supports it, so every action ends up with a citation to the patient's record
and to a guidance card or the signed plan.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .. import config as C

PAIN_LIKE = {"pain", "chest", "abdominal", "priapism"}


@dataclass
class Action:
    code: str
    kind: str              # analgesia | clock | red_flag | plan | model
    text: str
    query: str
    evidence: list = field(default_factory=list)   # record evidence ids
    due_min: float | None = None
    overdue: bool = False
    severity: int = 1      # 3 urgent, 2 soon, 1 routine
    plan_cite: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def fmt(x: float, nd: int = 0) -> str:
    return f"{x:.{nd}f}"


def record_evidence(snap: dict, risk: dict | None = None) -> dict[str, str]:
    """Plain language record facts that sentences can cite and the verifier can check."""
    a, p, d, v, labs = snap["attendance"], snap["patient"], snap["derived"], snap["vitals"], snap["labs"]
    now = snap["now_min"]
    ev = {}
    ev["R.arrival"] = (f"Arrived {fmt(now)} minutes ago with {a['complaint']}; triage category {a['triage_category']}; "
                       f"arrival pain score {fmt(a['pain_score_arrival'])}; genotype {p['genotype']}; age {p['age']}.")
    if d["analgesia_given_min"] is not None:
        interval = snap["plan"]["reassess_min"] if snap.get("plan") else C.PROTOCOL.reassess_interval_min
        ev["R.analgesia"] = (f"First analgesia {d['analgesia_agent']} {d['analgesia_route']} given at minute {fmt(d['analgesia_given_min'])}, "
                             f"{fmt(now - d['analgesia_given_min'])} minutes ago; reassessment due at minute "
                             f"{fmt(d['analgesia_given_min'] + interval)}, {interval} minutes after the dose."
                             + (f" Pain reassessed at minute {fmt(d['reassessed_min'])}." if d["reassessed_min"] is not None else " No pain reassessment recorded since."))
    else:
        ev["R.analgesia"] = f"No analgesia recorded in the {fmt(now)} minutes since arrival."
    if v:
        ev["R.vitals"] = (f"Latest observations at minute {fmt(v['minute'])}: oxygen saturation {fmt(v['spo2'])} percent against a baseline of "
                          f"{fmt(p['baseline_spo2'])}, {fmt(p['baseline_spo2'] - v['spo2'])} points below baseline; respiratory rate {fmt(v['rr'])}; "
                          f"heart rate {fmt(v['hr'])}; temperature {fmt(v['temp'], 1)} degrees; pain score {fmt(v['pain'])}.")
    if labs.get("hb") is not None:
        ev["R.labs"] = (f"Haemoglobin {fmt(labs['hb'], 1)} g/dL against a steady state of {fmt(p['steady_state_hb'], 1)}, "
                        f"a fall of {fmt(p['steady_state_hb'] - labs['hb'], 1)} g/dL; white cells {fmt(labs['wbc'], 1)}; platelets {fmt(labs['plt'])}.")
    if d["admitted_min"] is not None and now >= d["admitted_min"]:
        ev["R.admission"] = f"Admitted at minute {fmt(d['admitted_min'])}; {fmt((now - d['admitted_min']) / 60, 1)} hours on the ward."
    P = C.PROTOCOL
    ev["R.protocol"] = (f"Local protocol parameters: first analgesia target {P.analgesia_target_min} minutes; reassessment every "
                        f"{P.reassess_interval_min} minutes until relief; fever flag {P.temp_flag:.1f} degrees; oxygen saturation flag below "
                        f"{P.spo2_flag:.0f} percent or {P.spo2_drop_flag:.0f} points below baseline; respiratory rate flags {P.rr_flag} and "
                        f"{P.rr_low_flag}; haemoglobin flag {P.hb_drop_flag:.1f} g/dL below steady state.")
    plan = snap.get("plan")
    if plan:
        ev["R.plan"] = f"Signed individual plan {plan['plan_id']} is on the record; last reviewed {plan['days_since_review']} days before this attendance."
    else:
        ev["R.plan"] = "No individual care plan is visible in the emergency department record."
    flags = []
    if p["renal_impairment"]:
        flags.append("renal impairment")
    if p["asthma"]:
        flags.append("asthma")
    if flags:
        ev["R.problems"] = "Problem list includes " + " and ".join(flags) + "."
    if risk:
        ev["M.acs"] = (f"Deterioration model estimate {round(100 * risk['risk_24h'])} percent for acute chest syndrome within 24 hours; "
                       f"alert threshold {round(100 * risk['threshold'])} percent.")
    return ev


def actions_for(snap: dict, risk: dict | None = None, P=C.PROTOCOL) -> list[Action]:
    now = snap["now_min"]
    a, pt, d, v, labs, plan = (snap["attendance"], snap["patient"], snap["derived"], snap["vitals"], snap["labs"], snap["plan"])
    out: list[Action] = []
    if d["left_department"] or d["discharged"]:
        return out
    adm = d["admitted_min"]
    on_ward = adm is not None and now >= adm
    given = d["analgesia_given_min"]

    if a["complaint"] in PAIN_LIKE and given is None:
        late = now > P.analgesia_target_min
        out.append(Action("GIVE_FIRST_ANALGESIA", "clock",
                          (f"First analgesia is overdue: {fmt(now)} minutes since arrival against a target of {P.analgesia_target_min} minutes; give it now."
                           if late else f"Give the first dose of analgesia by minute {P.analgesia_target_min}; {fmt(now)} minutes have passed since arrival."),
                          "first dose analgesia within 30 minutes of arrival target", ["R.arrival", "R.analgesia"],
                          P.analgesia_target_min, late, 3 if late else 2))
        out.append(Action("ASK_HOME_ANALGESIA", "clock", "Ask what analgesia was taken at home for this episode before the first dose.",
                          "analgesia already taken at home before arrival", ["R.analgesia"], None, False, 1))
        if plan:
            out.append(Action("FOLLOW_PLAN", "analgesia",
                              f"Use the signed plan: {plan['first_line_agent']} by the {plan['route']} route, dose as written in the signed individual plan.",
                              "individual care plan agent route dose", ["R.plan"], None, False, 3, [f"{plan['plan_id']}.A"]))
        else:
            out.append(Action("USE_DEPARTMENT_PROTOCOL", "analgesia",
                              "No individual plan is visible, so use the department protocol for a strong opioid in severe pain and ask haematology whether a plan exists.",
                              "strong opioid severe pain bolus no plan", ["R.plan"], None, False, 3))
        out.append(Action("AVOID_PETHIDINE", "analgesia", "Do not use pethidine.", "pethidine avoid", [], None, False, 2,
                          [f"{plan['plan_id']}.B"] if plan else []))
        out.append(Action("ADJUNCT_PARACETAMOL", "analgesia", "Offer regular paracetamol as an adjunct.", "paracetamol adjunct", [], None, False, 1,
                          [f"{plan['plan_id']}.C"] if plan else []))
        blocked = pt["renal_impairment"] or (plan is not None and "NSAIDs" in plan["avoid"])
        if blocked:
            ev = ["R.problems"] if pt["renal_impairment"] else []
            out.append(Action("NO_NSAID", "analgesia", "Do not give an NSAID adjunct: renal impairment or the plan rules it out.",
                              "NSAID contraindicated renal impairment", ev, None, False, 2, [f"{plan['plan_id']}.B"] if plan else []))
        else:
            out.append(Action("ADJUNCT_NSAID", "analgesia", "An NSAID such as ibuprofen can be added as an adjunct; no contraindication is recorded.",
                              "NSAID ibuprofen adjunct unless contraindicated", [], None, False, 1))

    if given is not None and not on_ward:
        since = now - given
        interval = plan["reassess_min"] if plan else P.reassess_interval_min
        if since <= 120:
            out.append(Action("MONITOR_AFTER_OPIOID", "clock",
                              "Record pain, sedation, respiratory rate and oxygen saturation every 30 minutes until pain is controlled.",
                              "monitoring after opioid respiratory rate sedation every 30 minutes", ["R.analgesia"], None, False, 2))
            if d["reassessed_min"] is None:
                due = given + interval
                late = now >= due
                out.append(Action("REASSESS_PAIN", "clock",
                                  (f"Pain reassessment is overdue: due at minute {fmt(due)}, {fmt(since)} minutes after the first dose."
                                   if late else f"Reassess pain by minute {fmt(due)}, {interval} minutes after the first dose."),
                                  "reassess pain every 30 minutes after first dose", ["R.analgesia"], due, late, 3 if late else 2))
    if on_ward:
        hrs = (now - adm) / 60
        if hrs <= 24:
            out.append(Action("INFORM_HAEMATOLOGY", "clock", "Tell the haematology team about this admission if not already done.",
                              "inform haematology specialist team on admission", ["R.admission"], None, False, 2,
                              [f"{plan['plan_id']}.D"] if plan else []))
        out.append(Action("INCENTIVE_SPIROMETRY", "clock", "Encourage incentive spirometry while awake to lower the risk of acute chest syndrome.",
                          "incentive spirometry prevent acute chest syndrome admitted", ["R.admission"], None, False, 1))
        out.append(Action("FOUR_HOURLY_OBS", "clock", "Continue observations at least every four hours, including oxygen saturation and respiratory rate.",
                          "observations four hourly stable oxygen saturation respiratory rate", ["R.admission"], None, False, 1))

    if v:
        if v["temp"] >= P.temp_flag:
            out.append(Action("SEPSIS_SCREEN", "red_flag",
                              f"Temperature {fmt(v['temp'], 1)} degrees meets the local fever flag of {P.temp_flag:.1f}: start a sepsis screen with blood cultures and prompt antibiotics.",
                              "fever temperature sepsis screen blood culture antibiotics", ["R.vitals", "R.protocol"], None, False, 3))
        gap = pt["baseline_spo2"] - v["spo2"]
        if v["spo2"] < P.spo2_flag or gap >= P.spo2_drop_flag:
            out.append(Action("REVIEW_CHEST", "red_flag",
                              f"Oxygen saturation {fmt(v['spo2'])} percent is {fmt(gap)} points below baseline: review the chest promptly and consider a chest X ray for acute chest syndrome.",
                              "falling oxygen saturation below baseline acute chest syndrome review", ["R.vitals", "R.protocol"], None, False, 3))
        elif v["rr"] >= P.rr_flag:
            out.append(Action("REVIEW_CHEST", "red_flag",
                              f"Respiratory rate {fmt(v['rr'])} is raised: review the chest for acute chest syndrome.",
                              "rising respiratory rate acute chest syndrome review", ["R.vitals"], None, False, 3))
        if v["rr"] <= P.rr_low_flag:
            out.append(Action("OPIOID_TOXICITY_REVIEW", "red_flag",
                              f"Respiratory rate {fmt(v['rr'])} is low: review now for opioid toxicity, hold further doses and follow the opioid safety policy.",
                              "low respiratory rate sedation opioid toxicity naloxone", ["R.vitals"], None, False, 3))
    if a["complaint"] == "chest" and now <= 240 and not on_ward:
        out.append(Action("CHEST_XRAY_AT_ARRIVAL", "red_flag", "Chest symptoms at presentation: arrange an early chest X ray and inform haematology.",
                          "chest pain breathlessness cough at presentation chest X ray", ["R.arrival"], None, False, 3))
    if a["complaint"] == "neuro":
        out.append(Action("STROKE_PATHWAY", "red_flag", "Neurological symptoms: start the stroke pathway with urgent brain imaging and immediate haematology involvement.",
                          "neurological weakness speech stroke urgent imaging exchange transfusion", ["R.arrival"], None, False, 3))
    if a["complaint"] == "priapism":
        out.append(Action("UROLOGY_REVIEW", "red_flag", "Priapism: ask how long it has lasted and seek urgent urology review alongside analgesia.",
                          "priapism four hours urology aspiration", ["R.arrival"], None, False, 3))
    if labs.get("hb") is not None and pt["steady_state_hb"] - labs["hb"] >= P.hb_drop_flag:
        out.append(Action("ACUTE_ANAEMIA_REVIEW", "red_flag",
                          f"Haemoglobin has fallen {fmt(pt['steady_state_hb'] - labs['hb'], 1)} g/dL below steady state: check reticulocytes and the spleen and discuss with haematology.",
                          "haemoglobin fall below steady state reticulocytes sequestration", ["R.labs", "R.protocol"], None, False, 3))
    if plan and plan["days_since_review"] > 365:
        out.append(Action("PLAN_REVIEW_DUE", "plan", f"The plan was last reviewed {plan['days_since_review']} days ago; follow it but confirm with haematology.",
                          "care plan review out of date annual", ["R.plan"], None, False, 1))
    if risk and risk.get("alert"):
        out.append(Action("DETERIORATION_ALERT", "model",
                          f"The deterioration model estimates a {round(100 * risk['risk_24h'])} percent chance of acute chest syndrome within 24 hours, above the {round(100 * risk['threshold'])} percent alert threshold: review at the bedside.",
                          "deterioration model alert acute chest syndrome 24 hours review", ["M.acs"], None, False, 3))
    order = {"red_flag": 0, "model": 1, "clock": 2, "analgesia": 3, "plan": 4}
    out.sort(key=lambda x: (-x.severity, order[x.kind]))
    return out
