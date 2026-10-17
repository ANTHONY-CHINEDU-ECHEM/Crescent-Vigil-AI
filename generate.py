"""Calibrated synthetic emergency department cohort for sickle cell disease.

No open patient level dataset of sickle cell emergency attendances exists, so the
platform is fed from a generator whose parameters are set from published
distributions (see docs/data_card.md for every source and assumption). The
generator writes eight tables:

    sites          eight synthetic emergency departments
    patients       steady state characteristics of each adult patient
    care_plans     individualised analgesia plans (agent, route, cautions, review date)
    attendances    one row per emergency attendance with arrival vitals and labs,
                   door to analgesia time, reassessment, disposition and outcomes
    events         event sourced timeline of each attendance (minutes from arrival)
    obs            four hourly observations for 72 hours after admission
    labs           laboratory results at admission, 24 h and 48 h
    ground_truth   the parameters the generator used, so audits and models can be
                   checked for parameter recovery

Doses are never generated. Plans record the agent and route only and every
interface shows "dose as written in the signed plan".
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from .. import config as C

GENOTYPES = np.array(["HbSS", "HbSC", "HbSbeta0", "HbSbetaplus", "HbSD"])
GENOTYPE_P = np.array([0.62, 0.25, 0.06, 0.05, 0.02])
SEVERE = {"HbSS", "HbSbeta0", "HbSD"}

COMPLAINTS = np.array(["pain", "fever", "chest", "neuro", "priapism", "abdominal", "other"])
COMPLAINT_P = np.array([0.815, 0.05, 0.065, 0.012, 0.012, 0.026, 0.02])

AGENTS = np.array(["morphine", "diamorphine", "oxycodone"])
AGENT_P = np.array([0.56, 0.22, 0.22])
ROUTES = np.array(["subcutaneous", "intravenous", "oral"])
ROUTE_P = np.array([0.46, 0.34, 0.20])

SITES = pd.DataFrame(
    [
        ("A", "Northgate General", True, 0.86, 0.60, 0.20),
        ("B", "Riverside University", True, 0.80, 0.72, 0.19),
        ("C", "Eastbrook District", False, 0.45, 0.52, 0.09),
        ("D", "Marsh Lane Hospital", False, 0.34, 0.82, 0.10),
        ("E", "Kingsmoor Teaching", True, 0.76, 0.56, 0.16),
        ("F", "Westfield Community", False, 0.40, 0.66, 0.08),
        ("G", "Harbourside Royal", True, 0.72, 0.76, 0.11),
        ("H", "Fenwick Valley", False, 0.30, 0.60, 0.07),
    ],
    columns=["site", "site_name", "specialist_centre", "plan_visibility", "crowding_base", "patient_share"],
)

# Effects injected into door to analgesia (log minutes). The equity audit must
# recover these from the data alone; reports compare estimates to these values.
DTA_EFFECTS = {
    "intercept": np.log(44.0),
    "crowding": 0.48,          # per unit of the crowding index above 0.6
    "triage_cat2": -0.26,
    "triage_cat1": -0.45,
    "plan_visible": -0.34,
    "high_frequency_attender": 0.30,
    "night": 0.13,
    "female": 0.08,
    "age_50_plus": -0.04,
    "site_sd": 0.10,
    "residual_sd": 0.55,
}

# Incident acute chest syndrome within 72 h of admission (logit scale).
ACS_EFFECTS = {
    "intercept": -3.35,
    "severe_genotype": 0.85,
    "prior_acs": 0.32,        # per previous episode, capped at four
    "asthma": 0.45,
    "hydroxyurea": -0.38,
    "hbf_per_5pct": -0.18,
    "wbc_per_5": 0.22,
    "hb_drop": 0.30,          # per g/dL below steady state at admission
    "opioid_intensity": 0.55,  # per SD of the admission opioid intensity
    "spirometry_adherence": -0.55,
    "arrival_fever": 0.40,
    "spo2_gap": 0.12,          # per percentage point below the patient's baseline
    "age_over_40": -0.25,
}


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def make_patients(rng: np.random.Generator) -> pd.DataFrame:
    n = C.COHORT.patients
    share = SITES.patient_share.to_numpy() / SITES.patient_share.sum()
    site = rng.choice(SITES.site.to_numpy(), size=n, p=share)
    genotype = rng.choice(GENOTYPES, size=n, p=GENOTYPE_P)
    severe = np.isin(genotype, list(SEVERE))
    age = np.clip(16 + rng.gamma(2.2, 9.5, size=n), 16, 78).round(0)
    sex = rng.choice(np.array(["F", "M"]), size=n)
    base_hb = np.where(
        genotype == "HbSS", rng.normal(8.4, 1.1, n),
        np.where(genotype == "HbSbeta0", rng.normal(8.3, 1.1, n),
                 np.where(genotype == "HbSC", rng.normal(11.0, 1.2, n),
                          np.where(genotype == "HbSbetaplus", rng.normal(10.6, 1.2, n), rng.normal(9.0, 1.2, n)))))
    base_hb = np.clip(base_hb, 5.8, 14.5).round(1)
    base_spo2 = np.clip(np.where(severe, rng.normal(96.3, 1.8, n), rng.normal(97.8, 1.0, n)), 90, 100).round(0)
    hydroxyurea = rng.random(n) < np.where(severe, 0.52, 0.07)
    hbf = np.clip(np.where(severe, rng.gamma(2.0, 3.2, n), rng.gamma(1.4, 1.5, n)) + hydroxyurea * rng.normal(9, 4, n), 0.2, 38).round(1)
    prior_acs = rng.poisson(np.where(severe, 1.05, 0.35))
    asthma = rng.random(n) < 0.16
    renal = rng.random(n) < np.clip(0.02 + 0.0012 * (age - 16) + 0.03 * severe, 0, 0.3)
    propensity = rng.lognormal(0.0, 0.85, n)
    pid = np.array([f"CV{i:06d}" for i in range(1, n + 1)])
    return pd.DataFrame(dict(
        patient_id=pid, home_site=site, genotype=genotype, severe_genotype=severe, age_2021=age, sex=sex,
        steady_state_hb=base_hb, baseline_spo2=base_spo2, hbf_pct=hbf, hydroxyurea=hydroxyurea,
        prior_acs=prior_acs, asthma=asthma, renal_impairment=renal, attend_propensity=propensity.round(3),
    ))


def make_plans(rng, patients: pd.DataFrame) -> pd.DataFrame:
    spec = patients.home_site.map(SITES.set_index("site").specialist_centre).to_numpy()
    p_plan = np.clip(0.30 + 0.30 * spec + 0.12 * (patients.attend_propensity.to_numpy() > 1.5), 0, 0.92)
    has = rng.random(len(patients)) < p_plan
    pts = patients[has].reset_index(drop=True)
    m = len(pts)
    agent = rng.choice(AGENTS, size=m, p=AGENT_P)
    intolerance = np.where(rng.random(m) < 0.09, np.where(agent == "morphine", "oxycodone", "morphine"), "")
    # A documented intolerance never names the plan's own first line agent.
    intolerance = np.where(intolerance == agent, "", intolerance)
    route = rng.choice(ROUTES, size=m, p=ROUTE_P)
    venous = (route == "subcutaneous") & (rng.random(m) < 0.6)
    # Plans are reviewed on a cycle: most yearly, some less often, so a share are overdue at any time.
    review_cycle = rng.choice(np.array([365, 540, 900]), size=m, p=[0.6, 0.25, 0.15])
    reviewed_days_ago = (rng.random(m) * review_cycle).astype(int)
    notes = []
    for i in range(m):
        n = ["Inform haematology on call at admission."]
        if venous[i]:
            n.append("Difficult venous access; subcutaneous route preferred.")
        if pts.prior_acs.iat[i] >= 2:
            n.append("Previous acute chest syndrome; low threshold for chest imaging if chest symptoms or falling saturation.")
        if pts.asthma.iat[i]:
            n.append("Asthma; review bronchodilator need if wheeze.")
        notes.append(" ".join(n))
    avoid = []
    for i in range(m):
        a = ["pethidine"]
        if pts.renal_impairment.iat[i]:
            a.append("NSAIDs")
        if intolerance[i]:
            a.append(intolerance[i])
        avoid.append(";".join(a))
    adjuncts = np.where(pts.renal_impairment.to_numpy(), "paracetamol", "paracetamol;ibuprofen")
    return pd.DataFrame(dict(
        plan_id=[f"PLAN{i:05d}" for i in range(1, m + 1)], patient_id=pts.patient_id, first_line_agent=agent,
        route=route, adjuncts=adjuncts, avoid=avoid, intolerance=intolerance, reassess_min=30,
        notes=notes, reviewed_days_before_2021=reviewed_days_ago, review_cycle_days=review_cycle,
        dose_text="Dose as written in the signed individual plan",
    ))


def make_attendances(rng, patients: pd.DataFrame, plans: pd.DataFrame) -> pd.DataFrame:
    start = pd.Timestamp(C.START_DATE)
    days = (pd.Timestamp(C.END_DATE) - start).days + 1
    rate = 1.55 * patients.attend_propensity.to_numpy()  # attendances per year
    counts = rng.poisson(np.clip(rate, 0, 25) * days / 365.25)
    idx = np.repeat(np.arange(len(patients)), counts)
    n = len(idx)
    # Seasonal day sampling: winter months roughly 20% busier.
    doy = np.arange(days)
    month = (start + pd.to_timedelta(doy, unit="D")).month.to_numpy()
    w = np.where(np.isin(month, [12, 1, 2]), 1.2, np.where(np.isin(month, [6, 7, 8]), 0.9, 1.0))
    day = rng.choice(doy, size=n, p=w / w.sum())
    hour_w = np.array([3, 2.5, 2, 1.8, 1.6, 1.8, 2.4, 3.2, 4, 4.5, 4.8, 5, 5, 5, 4.9, 4.9, 5, 5.2, 5.4, 5.4, 5, 4.6, 4, 3.4])
    hour = rng.choice(24, size=n, p=hour_w / hour_w.sum())
    minute = rng.integers(0, 60, n)
    arrival = start + pd.to_timedelta(day, unit="D") + pd.to_timedelta(hour, unit="h") + pd.to_timedelta(minute, unit="m")

    P = patients.iloc[idx].reset_index(drop=True)
    df = pd.DataFrame({"patient_id": P.patient_id, "site": P.home_site, "arrival": arrival})
    df = pd.concat([df, P.drop(columns=["patient_id", "home_site"])], axis=1)
    df = df.sort_values(["patient_id", "arrival"]).reset_index(drop=True)
    n = len(df)
    df["age"] = (df.age_2021 + (df.arrival - start).dt.days / 365.25).round(0)
    # Prior attendances in the previous 365 days (observable at arrival).
    t = df.arrival.values.astype("datetime64[m]").astype(np.int64)
    pidc = df.patient_id.to_numpy()
    prior = np.zeros(n, dtype=int)
    j0 = 0
    for i in range(n):
        if i == 0 or pidc[i] != pidc[i - 1]:
            j0 = i
        while t[i] - t[j0] > 365 * 1440:
            j0 += 1
        prior[i] = i - j0
    df["prior_attend_365d"] = prior
    df["high_frequency_attender"] = prior >= 5

    complaint = rng.choice(COMPLAINTS, size=n, p=COMPLAINT_P)
    complaint = np.where((complaint == "priapism") & (df.sex.to_numpy() == "F"), "pain", complaint)
    df["complaint"] = complaint
    is_pain_like = np.isin(complaint, ["pain", "chest", "abdominal", "priapism"])

    site_info = SITES.set_index("site")
    night = (df.arrival.dt.hour >= 22) | (df.arrival.dt.hour < 7)
    evening = df.arrival.dt.hour.between(16, 23)
    winter = df.arrival.dt.month.isin([12, 1, 2])
    crowd = (df.site.map(site_info.crowding_base) + 0.22 * evening + 0.12 * winter + rng.normal(0, 0.16, n)).clip(0.05, 1.6)
    df["night"] = night.to_numpy()
    df["crowding_index"] = crowd.round(3)

    pain = np.where(is_pain_like, np.clip(rng.normal(8.4, 1.1, n), 4, 10), np.clip(rng.normal(4, 2, n), 0, 10)).round(0)
    df["pain_score_arrival"] = pain
    severe = df.severe_genotype.to_numpy()
    df["hr_arrival"] = np.clip(rng.normal(92, 13, n) + 2.2 * (pain - 7), 50, 160).round(0)
    df["rr_arrival"] = np.clip(rng.normal(18, 2.6, n) + 2.5 * (complaint == "chest"), 10, 40).round(0)
    spo2 = df.baseline_spo2.to_numpy() - np.abs(rng.normal(0.6, 1.0, n)) - 3.2 * (complaint == "chest") * rng.random(n)
    df["spo2_arrival"] = np.clip(spo2, 80, 100).round(0)
    temp = rng.normal(37.0, 0.35, n) + np.where(complaint == "fever", rng.normal(1.6, 0.4, n), 0) + np.where(complaint == "chest", rng.normal(0.5, 0.5, n), 0)
    df["temp_arrival"] = np.clip(temp, 35.5, 41).round(1)
    df["sbp_arrival"] = np.clip(rng.normal(124, 15, n), 80, 200).round(0)
    hb_drop = np.abs(rng.normal(0.5, 0.45, n)) + np.where(complaint == "abdominal", rng.gamma(2, 1.0, n), 0) + (rng.random(n) < 0.02) * rng.gamma(3, 0.9, n)
    df["hb_arrival"] = np.clip(df.steady_state_hb.to_numpy() - hb_drop, 3.0, 15).round(1)
    df["wbc_arrival"] = np.clip(rng.normal(12.5 + 1.8 * severe, 3.8, n) + 3 * (complaint == "fever"), 2, 45).round(1)
    df["plt_arrival"] = np.clip(rng.normal(360, 110, n), 40, 900).round(0)
    df["retic_arrival"] = np.clip(rng.normal(np.where(severe, 260, 160), 80, n), 5, 700).round(0)
    df["ldh_arrival"] = np.clip(rng.normal(np.where(severe, 520, 330), 140, n), 120, 2500).round(0)
    df["bili_arrival"] = np.clip(rng.normal(np.where(severe, 55, 30), 18, n), 4, 300).round(0)
    df["crp_arrival"] = np.clip(rng.gamma(1.6, 14, n) + 50 * (complaint == "fever"), 0.5, 400).round(1)

    # Triage: Manchester style categories 1 (immediate) to 5.
    neuro = complaint == "neuro"
    flag = (df.spo2_arrival.to_numpy() < C.PROTOCOL.spo2_flag) | (df.temp_arrival.to_numpy() >= C.PROTOCOL.temp_flag) | neuro
    r = rng.random(n)
    triage = np.where(neuro | (flag & (r < 0.25)), 1,
                      np.where(flag | ((pain >= 8) & (r < 0.48)), 2, np.where(pain >= 5, 3, 4)))
    df["triage_category"] = triage

    plan_by_pt = plans.set_index("patient_id")
    has_plan = df.patient_id.isin(plan_by_pt.index).to_numpy()
    vis = df.site.map(site_info.plan_visibility).to_numpy()
    plan_visible = has_plan & (rng.random(n) < vis)
    df["has_plan"] = has_plan
    df["plan_visible"] = plan_visible

    # Door to analgesia with injected, documented effects.
    E = DTA_EFFECTS
    site_re = {s: rng.normal(0, E["site_sd"]) for s in SITES.site}
    logt = (E["intercept"] + E["crowding"] * (crowd.to_numpy() - 0.6) + E["triage_cat2"] * (triage == 2)
            + E["triage_cat1"] * (triage == 1) + E["plan_visible"] * plan_visible
            + E["high_frequency_attender"] * df.high_frequency_attender.to_numpy() + E["night"] * night.to_numpy()
            + E["female"] * (df.sex.to_numpy() == "F") + E["age_50_plus"] * (df.age.to_numpy() >= 50)
            + df.site.map(site_re).to_numpy() + rng.normal(0, E["residual_sd"], n))
    dta = np.clip(np.exp(logt), 4, 900).round(0)
    left_without = is_pain_like & (rng.random(n) < 0.028)
    dta = np.where(is_pain_like & ~left_without, dta, np.nan)
    df["door_to_analgesia_min"] = dta
    df["left_before_analgesia"] = left_without
    df["site_effect_true"] = df.site.map(site_re).round(4)

    # Which agent was given, against the plan.
    given_agent = np.full(n, "", dtype=object)
    given_route = np.full(n, "", dtype=object)
    pa = df.patient_id.map(plan_by_pt.first_line_agent).to_numpy()
    pr = df.patient_id.map(plan_by_pt.route).to_numpy()
    followed = plan_visible & (rng.random(n) < 0.91)
    default_agent = rng.choice(np.array(["morphine", "morphine", "morphine", "diamorphine", "oxycodone"]), n)
    default_route = rng.choice(np.array(["intravenous", "subcutaneous", "oral"]), n, p=[0.5, 0.3, 0.2])
    spec = df.site.map(site_info.specialist_centre).to_numpy()
    pethidine = (~plan_visible) & (~spec) & (rng.random(n) < 0.025)
    given_agent[:] = np.where(followed, pa, np.where(pethidine, "pethidine", default_agent))
    given_route[:] = np.where(followed, pr, default_route)
    give = ~np.isnan(dta)
    df["first_agent"] = np.where(give, given_agent, "")
    df["first_route"] = np.where(give, given_route, "")
    df["plan_followed"] = give & followed
    p_re = np.clip(0.52 + 0.16 * plan_visible - 0.22 * (crowd.to_numpy() - 0.6) + 0.10 * spec, 0.05, 0.97)
    df["reassessed_within_30"] = give & (rng.random(n) < p_re)

    # Disposition.
    lp = -0.2 + 0.45 * (pain - 8) + 0.8 * flag + 0.5 * (hb_drop > 1.5) + 0.6 * np.isin(complaint, ["chest", "neuro", "abdominal", "priapism"]) + rng.normal(0, 0.6, n)
    admitted = (_sigmoid(lp) > 0.42) & ~left_without
    df["admitted"] = admitted

    # Acute chest syndrome present at arrival (diagnosed in the department).
    acs_at_arrival = (complaint == "chest") & (rng.random(n) < 0.36)
    df["acs_at_arrival"] = acs_at_arrival
    df["admitted"] = df.admitted | acs_at_arrival

    # Incident ACS after admission, from a latent risk model.
    A = ACS_EFFECTS
    adm = df.admitted.to_numpy() & ~acs_at_arrival
    opioid_int = rng.normal(0, 1, n) + 0.35 * (pain - 8) + 0.30 * df.high_frequency_attender.to_numpy()
    spiro = rng.random(n) < np.clip(0.40 + 0.20 * spec, 0, 1)
    df["opioid_intensity_true"] = opioid_int.round(3)
    df["spirometry_adherence"] = spiro
    logit = (A["intercept"] + A["severe_genotype"] * severe + A["prior_acs"] * np.minimum(df.prior_acs.to_numpy(), 4)
             + A["asthma"] * df.asthma.to_numpy() + A["hydroxyurea"] * df.hydroxyurea.to_numpy()
             + A["hbf_per_5pct"] * df.hbf_pct.to_numpy() / 5 + A["wbc_per_5"] * (df.wbc_arrival.to_numpy() - 12) / 5
             + A["hb_drop"] * hb_drop + A["opioid_intensity"] * opioid_int + A["spirometry_adherence"] * spiro
             + A["arrival_fever"] * (df.temp_arrival.to_numpy() >= 37.8)
             + A["spo2_gap"] * (df.baseline_spo2.to_numpy() - df.spo2_arrival.to_numpy())
             + A["age_over_40"] * (df.age.to_numpy() > 40))
    p_acs = _sigmoid(logit)
    acs = adm & (rng.random(n) < p_acs)
    onset = np.clip(rng.gamma(3.0, 10.5, n), 3, 62)
    diag = np.minimum(onset + rng.uniform(3, 10, n), 71.5)
    df["acs_risk_true"] = np.where(adm, p_acs, np.nan).round(4)
    df["acs_72h"] = acs
    df["acs_onset_h"] = np.where(acs, onset.round(1), np.nan)
    df["acs_diagnosis_h"] = np.where(acs, diag.round(1), np.where(acs_at_arrival, rng.uniform(1, 5, n).round(1), np.nan))
    # Length of stay in hours: five to twelve days after acute chest syndrome, otherwise about three days.
    los = np.where(acs, rng.uniform(5, 12, n) * 24, np.where(adm, np.clip(rng.gamma(3.0, 26, n), 18, 400), np.nan))
    df["length_of_stay_h"] = np.round(los, 1)
    df["discharge_h"] = np.where(df.admitted, np.round(los, 1), np.round(rng.uniform(2, 7, n), 1))

    df.insert(0, "attendance_id", [f"ATT{i:07d}" for i in range(1, n + 1)])
    df["split"] = np.where(df.site.isin(C.BLIND_SITES), "blind_site",
                           np.where(df.arrival >= pd.Timestamp(C.BLIND_FROM), "blind_temporal", "dev"))
    return df


def make_obs_and_labs(rng, att: pd.DataFrame):
    a = att[att.admitted & ~att.acs_at_arrival].reset_index(drop=True)
    m = len(a)
    hours = np.arange(0, C.OBS_HORIZON_H + 1, C.OBS_STEP_H)
    T = len(hours)
    H = np.broadcast_to(hours, (m, T)).astype(float)
    acs = a.acs_72h.to_numpy()
    onset = np.nan_to_num(a.acs_onset_h.to_numpy(), nan=999)
    diag = np.nan_to_num(a.acs_diagnosis_h.to_numpy(), nan=999)
    s = np.clip(H - onset[:, None], 0, None)
    pro = np.clip(H - (onset[:, None] - 8), 0, 8) * (H < onset[:, None])
    base = a.baseline_spo2.to_numpy()[:, None]
    # Confounders: transient desaturation in non ACS admissions, opioid related low respiratory rate, other infections.
    dip_t = rng.integers(1, T, m)
    dip = (rng.random(m) < 0.10)[:, None] * (np.abs(np.arange(T)[None, :] - dip_t[:, None]) <= 1) * rng.uniform(2, 4.5, (m, 1))
    hypo = (rng.random(m) < 0.045)[:, None] * (np.abs(np.arange(T)[None, :] - dip_t[:, None]) == 0)
    infect = (rng.random(m) < 0.07)[:, None] * (H >= rng.uniform(8, 48, (m, 1)))
    spo2 = base - 0.6 + rng.normal(0, 0.8, (m, T)) - dip - 0.06 * pro - acs[:, None] * (0.16 * s + 0.002 * s ** 2) - 1.8 * hypo
    rr = 18 + rng.normal(0, 1.8, (m, T)) + acs[:, None] * 0.19 * s + 0.05 * pro - hypo * rng.uniform(7, 10, (m, 1)) + 1.2 * infect
    hr = a.hr_arrival.to_numpy()[:, None] - 9 * (1 - np.exp(-H / 10)) + rng.normal(0, 5, (m, T)) + acs[:, None] * 0.55 * s + 6 * infect
    temp = 37.0 + rng.normal(0, 0.25, (m, T)) + acs[:, None] * np.minimum(0.05 * s, 2.0) + infect * rng.uniform(0.9, 1.8, (m, 1))
    pain0 = a.pain_score_arrival.to_numpy()[:, None]
    pain = 3.8 + (pain0 - 3.8) * np.exp(-H / 18) + rng.normal(0, 0.7, (m, T)) + acs[:, None] * np.minimum(0.06 * s, 2.0)
    intensity = a.opioid_intensity_true.to_numpy()[:, None]
    opioid_rate = np.clip(1.0 + 0.45 * intensity, 0.1, None) * np.exp(-H / 30)
    opioid_load = np.cumsum(opioid_rate * C.OBS_STEP_H, axis=1) / 10
    spiro = (rng.random((m, T)) < np.where(a.spirometry_adherence.to_numpy(), 0.8, 0.25)[:, None])
    alive = H <= a.length_of_stay_h.to_numpy()[:, None]
    obs = pd.DataFrame({
        "attendance_id": np.repeat(a.attendance_id.to_numpy(), T),
        "hour": H.ravel(),
        "spo2": np.clip(spo2, 70, 100).round(0).ravel(),
        "rr": np.clip(rr, 6, 50).round(0).ravel(),
        "hr": np.clip(hr, 40, 180).round(0).ravel(),
        "temp": np.clip(temp, 35, 41.5).round(1).ravel(),
        "pain": np.clip(pain, 0, 10).round(0).ravel(),
        "opioid_load": opioid_load.round(2).ravel(),
        "spirometry_done": spiro.ravel(),
        "acs_diagnosed_by": (H >= diag[:, None]).ravel(),
    })
    obs = obs[alive.ravel()].reset_index(drop=True)

    lab_h = np.array([0, 24, 48])
    L = len(lab_h)
    Hl = np.broadcast_to(lab_h, (m, L)).astype(float)
    sl = np.clip(Hl - onset[:, None], 0, None)
    hb = a.hb_arrival.to_numpy()[:, None] - 0.25 * (Hl / 24) + rng.normal(0, 0.25, (m, L)) - acs[:, None] * np.minimum(0.03 * sl, 1.3)
    plt = a.plt_arrival.to_numpy()[:, None] * (1 - acs[:, None] * np.minimum(0.006 * sl, 0.35)) * rng.normal(1, 0.06, (m, L))
    wbc = a.wbc_arrival.to_numpy()[:, None] + rng.normal(0, 1.2, (m, L)) + acs[:, None] * np.minimum(0.12 * sl, 7)
    crp = a.crp_arrival.to_numpy()[:, None] * rng.normal(1.05, 0.15, (m, L)) + acs[:, None] * 3.0 * sl + infect[:, :L].any(axis=1)[:, None] * 30 * (Hl > 0)
    ldh = a.ldh_arrival.to_numpy()[:, None] * rng.normal(1.0, 0.08, (m, L)) + acs[:, None] * 6 * sl
    alive_l = Hl <= a.length_of_stay_h.to_numpy()[:, None]
    labs = pd.DataFrame({
        "attendance_id": np.repeat(a.attendance_id.to_numpy(), L),
        "hour": Hl.ravel(),
        "hb": np.clip(hb, 3, 15).round(1).ravel(),
        "plt": np.clip(plt, 20, 900).round(0).ravel(),
        "wbc": np.clip(wbc, 1, 60).round(1).ravel(),
        "crp": np.clip(crp, 0.5, 500).round(1).ravel(),
        "ldh": np.clip(ldh, 100, 4000).round(0).ravel(),
    })
    labs = labs[alive_l.ravel()].reset_index(drop=True)
    return obs, labs


def make_events(att: pd.DataFrame) -> pd.DataFrame:
    """Event sourced timeline. Minutes are measured from arrival."""
    rows = []
    def add(mask, minute, etype, payload):
        sub = att.loc[mask]
        mins = minute(sub) if callable(minute) else np.full(len(sub), minute)
        pl = payload(sub) if callable(payload) else [payload] * len(sub)
        rows.append(pd.DataFrame({"attendance_id": sub.attendance_id.to_numpy(), "minute": np.asarray(mins, float),
                                  "event": etype, "payload": pl}))
    allm = np.ones(len(att), bool)
    add(allm, 0, "arrival", lambda s: [json.dumps({"complaint": c, "pain": int(p)}) for c, p in zip(s.complaint, s.pain_score_arrival)])
    add(allm, 6, "triage", lambda s: [json.dumps({"category": int(c)}) for c in s.triage_category])
    add(att.plan_visible.to_numpy(), 9, "plan_viewed", "{}")
    g = att.door_to_analgesia_min.notna().to_numpy()
    add(g, lambda s: s.door_to_analgesia_min, "analgesia_given",
        lambda s: [json.dumps({"agent": a, "route": r}) for a, r in zip(s.first_agent, s.first_route)])
    re = att.reassessed_within_30.to_numpy()
    add(re, lambda s: s.door_to_analgesia_min + 25, "pain_reassessed", "{}")
    add(att.left_before_analgesia.to_numpy(), 95, "left_department", "{}")
    adm = att.admitted.to_numpy()
    add(adm, lambda s: np.nan_to_num(s.door_to_analgesia_min, nan=60) + 150, "admitted", "{}")
    acs_arr = att.acs_at_arrival.to_numpy()
    add(acs_arr, lambda s: s.acs_diagnosis_h * 60, "acs_diagnosed", '{"timing": "in department"}')
    inc = att.acs_72h.to_numpy()
    add(inc, lambda s: np.nan_to_num(s.door_to_analgesia_min, nan=60) + 150 + s.acs_diagnosis_h * 60, "acs_diagnosed", '{"timing": "after admission"}')
    add(~adm, lambda s: s.discharge_h * 60, "discharged", "{}")
    ev = pd.concat(rows, ignore_index=True).sort_values(["attendance_id", "minute"]).reset_index(drop=True)
    ev["minute"] = ev.minute.round(0)
    return ev


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def generate(out=C.SYNTH, seed: int = C.MASTER_SEED) -> dict:
    rng = np.random.default_rng(seed)
    patients = make_patients(rng)
    plans = make_plans(rng, patients)
    att = make_attendances(rng, patients, plans)
    obs, labs = make_obs_and_labs(rng, att)
    events = make_events(att)
    tables = {"sites": SITES, "patients": patients, "care_plans": plans, "attendances": att,
              "obs": obs, "labs": labs, "events": events}
    manifest = {"seed": seed, "tables": {}}
    for name, df in tables.items():
        p = out / f"{name}.parquet"
        df.to_parquet(p, index=False)
        manifest["tables"][name] = {"rows": int(len(df)), "sha256": file_sha256(p)}
    truth = {"door_to_analgesia_log_minutes": DTA_EFFECTS, "acs_logit": ACS_EFFECTS,
             "site_effects": att.groupby("site").site_effect_true.first().to_dict()}
    (out / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
