"""Freeze the evaluation sets before any model, index or copilot exists.

The blind set is two whole sites (new hospitals, new patients) plus every 2025
attendance at the other sites (a later period). Its scenarios, gold actions and
questions are written once, hashed, and recorded in FROZEN.json. Scoring the
blind set appends a timestamp to blind_runs.json so any later run is visible.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .. import config as C
from ..timeline.store import Timeline
from .gold import expected

RARE = {"chest", "neuro", "priapism", "abdominal", "fever"}


def sha(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def sample_scenarios(att: pd.DataFrame, tl: Timeline, n: int, rng) -> list[dict]:
    rare = att[att.complaint.isin(RARE)]
    common = att[~att.complaint.isin(RARE)]
    n_rare = int(n * 0.25)
    pick = pd.concat([rare.sample(n_rare, random_state=int(rng.integers(1 << 30))),
                      common.sample(n - n_rare, random_state=int(rng.integers(1 << 30)))])
    out = []
    for _, a in pick.iterrows():
        adm = tl.admitted_min(a.attendance_id)
        if adm is not None and rng.random() < 0.6 and not a.acs_at_arrival:
            end = adm + min(72 * 60, (a.length_of_stay_h if not np.isnan(a.length_of_stay_h) else 72) * 60)
            if a.acs_72h:
                end = min(end, adm + a.acs_diagnosis_h * 60 - 1)
            now = float(rng.uniform(adm, max(adm + 1, end)))
        else:
            hi = 150 if adm is None else min(150, adm - 1)
            now = float(rng.uniform(3, max(4, hi)))
        out.append({"attendance_id": a.attendance_id, "now_min": round(now, 0), "split": a.split})
    return out


def parse_questions(path=C.KNOWLEDGE / "eval_questions.txt") -> list[dict]:
    rows, seen = [], {}
    for line in open(path, encoding="utf8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        gold, minute, text = [x.strip() for x in line.split("|", 2)]
        key = gold
        seen[key] = seen.get(key, 0) + 1
        rows.append({"qid": f"Q{len(rows) + 1:03d}", "gold": gold.split(","),
                     "minute": float(minute) if minute else None, "text": text,
                     "split": "blind" if seen[key] == 3 else "dev"})
    return rows


def freeze(n_dev: int = 800, n_blind: int = 800) -> dict:
    rng = np.random.default_rng(C.MASTER_SEED + 1)
    att = pd.read_parquet(C.SYNTH / "attendances.parquet")
    tl = Timeline()
    dev = sample_scenarios(att[att.split == "dev"], tl, n_dev, rng)
    blind = (sample_scenarios(att[att.split == "blind_site"], tl, n_blind // 2, rng)
             + sample_scenarios(att[att.split == "blind_temporal"], tl, n_blind // 2, rng))
    files = {}
    for name, sc in (("scenarios_dev", dev), ("scenarios_blind", blind)):
        p = C.EVAL / f"{name}.jsonl"
        with open(p, "w") as f:
            for s in sc:
                snap = tl.snapshot(s["attendance_id"], s["now_min"]).to_dict()
                s["gold"] = expected(snap)
                f.write(json.dumps(s) + "\n")
        files[name] = p
    qs = parse_questions()
    for split in ("dev", "blind"):
        p = C.EVAL / f"questions_{split}.jsonl"
        with open(p, "w") as f:
            for q in qs:
                if q["split"] == split:
                    f.write(json.dumps(q) + "\n")
        files[f"questions_{split}"] = p
    ids = att[["attendance_id", "patient_id", "site", "split"]]
    p = C.EVAL / "split_ids.parquet"
    ids.to_parquet(p, index=False)
    files["split_ids"] = p
    manifest = json.loads((C.SYNTH / "MANIFEST.json").read_text())
    frozen = {
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator_seed": manifest["seed"],
        "attendances_sha256": manifest["tables"]["attendances"]["sha256"],
        "files": {k: sha(v) for k, v in files.items()},
        "blind_definition": {"sites": list(C.BLIND_SITES), "from": C.BLIND_FROM},
        "counts": {"dev_attendances": int((att.split == "dev").sum()),
                   "blind_site_attendances": int((att.split == "blind_site").sum()),
                   "blind_temporal_attendances": int((att.split == "blind_temporal").sum()),
                   "scenarios_dev": len(dev), "scenarios_blind": len(blind),
                   "questions_dev": sum(q["split"] == "dev" for q in qs),
                   "questions_blind": sum(q["split"] == "blind" for q in qs)},
    }
    combined = hashlib.sha256("".join(sorted(frozen["files"].values())).encode()).hexdigest()
    frozen["combined_sha256"] = combined
    (C.EVAL / "FROZEN.json").write_text(json.dumps(frozen, indent=2))
    (C.EVAL / "blind_hash.txt").write_text(combined + "\n")
    runs = C.EVAL / "blind_runs.json"
    if not runs.exists():
        runs.write_text(json.dumps({"frozen_at": frozen["frozen_at"], "runs": []}, indent=2))
    return frozen


def verify() -> bool:
    frozen = json.loads((C.EVAL / "FROZEN.json").read_text())
    names = {"scenarios_dev": "scenarios_dev.jsonl", "scenarios_blind": "scenarios_blind.jsonl",
             "questions_dev": "questions_dev.jsonl", "questions_blind": "questions_blind.jsonl",
             "split_ids": "split_ids.parquet"}
    return all(sha(C.EVAL / names[k]) == v for k, v in frozen["files"].items())


if __name__ == "__main__":
    import sys
    if (C.EVAL / "FROZEN.json").exists() and "--force" not in sys.argv:
        ok = verify()
        print(f"Evaluation sets are already frozen; hashes {'match' if ok else 'DO NOT match'}. Use --force to refreeze, which invalidates the blind run.")
        sys.exit(0 if ok else 1)
    print(json.dumps(freeze(), indent=2))
