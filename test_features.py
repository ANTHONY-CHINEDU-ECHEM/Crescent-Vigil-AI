import numpy as np
import pandas as pd

from crescent_vigil import config as C
from crescent_vigil.models.features import FEATURES, person_period_table, snapshot_features


def test_training_and_live_features_agree(timeline):
    att = timeline.f["attendances"]
    rng = np.random.default_rng(1)
    ids = rng.choice(att[att.admitted & ~att.acs_at_arrival & (att.split == "dev")].attendance_id.to_numpy(), 25, replace=False)
    sub = att[att.attendance_id.isin(ids)]
    obs = timeline.f["obs"][timeline.f["obs"].attendance_id.isin(ids)]
    labs = timeline.f["labs"][timeline.f["labs"].attendance_id.isin(ids)]
    # history_acs needs the full patient history, so build static features on all attendances of these patients.
    pts = att[att.patient_id.isin(sub.patient_id)]
    pp = person_period_table(pts, obs, labs)
    pp = pp[pp.attendance_id.isin(ids)]
    checked = 0
    for r in pp.itertuples():
        adm = timeline.admitted_min(r.attendance_id)
        snap = timeline.snapshot(r.attendance_id, adm + r.hours * 60).to_dict()
        f = snapshot_features(snap)
        for k in FEATURES:
            assert abs(f[k] - getattr(r, k)) < 1e-6, (r.attendance_id, r.hours, k, f[k], getattr(r, k))
        checked += 1
    assert checked > 100
