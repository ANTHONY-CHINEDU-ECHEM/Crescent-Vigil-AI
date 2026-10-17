import json

import numpy as np
import pandas as pd

from crescent_vigil import config as C
from crescent_vigil.eval.splits import verify


def test_frozen_files_unchanged():
    assert verify()
    runs = json.loads((C.EVAL / "blind_runs.json").read_text())
    assert "runs" in runs


def test_blind_is_held_out():
    att = pd.read_parquet(C.SYNTH / "attendances.parquet")
    assert set(att[att.split == "blind_site"].site) == set(C.BLIND_SITES)
    dev = att[att.split == "dev"]
    assert not dev.site.isin(C.BLIND_SITES).any()
    assert (dev.arrival < pd.Timestamp(C.BLIND_FROM)).all()
    # Patients at blind sites never appear in development data.
    assert not set(att[att.split == "blind_site"].patient_id) & set(dev.patient_id)


def test_generator_rates_are_plausible():
    att = pd.read_parquet(C.SYNTH / "attendances.parquet")
    adm = att[att.admitted & ~att.acs_at_arrival]
    assert 0.06 < adm.acs_72h.mean() < 0.14
    d = att.door_to_analgesia_min.dropna()
    assert 30 < d.median() < 60
    assert 0.15 < (d <= 30).mean() < 0.45


def test_plans_never_carry_doses_or_contradict_themselves():
    plans = pd.read_parquet(C.SYNTH / "care_plans.parquet")
    assert not plans.dose_text.str.contains(r"\d").any()
    assert (plans.intolerance != plans.first_line_agent).all()
    assert plans.avoid.str.contains("pethidine").all()


def test_snapshot_never_shows_the_future(timeline):
    att = timeline.f["attendances"]
    rng = np.random.default_rng(0)
    for aid in rng.choice(att[att.admitted].attendance_id.to_numpy(), 40, replace=False):
        adm = timeline.admitted_min(aid)
        now = adm + 600
        s = timeline.snapshot(aid, now)
        assert all(e["minute"] <= now for e in s.events)
        assert all(v["minute"] <= now for v in s.vitals_series)
        assert all(l["minute"] <= now for l in s.labs["series"])
