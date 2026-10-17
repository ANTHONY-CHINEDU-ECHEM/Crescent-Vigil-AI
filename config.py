"""Central configuration: paths, seeds and the parameters that every layer shares.

Each layer reads only the outputs of the layer before it. Paths are resolved
relative to the repository root so the package works from any directory.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(os.environ.get("CRESCENT_ROOT", Path(__file__).resolve().parents[1]))
DATA = ROOT / "data"
SYNTH = DATA / "synthetic"
EVAL = DATA / "eval"
INDEX = DATA / "index"
MODELS = DATA / "models"
KNOWLEDGE = ROOT / "knowledge"
CARDS = KNOWLEDGE / "cards"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
AUDIT_LOG = DATA / "audit" / "copilot_audit.jsonl"
TIMELINE_DB = DATA / "timeline.duckdb"

for _p in (SYNTH, EVAL, INDEX, MODELS, FIGURES, AUDIT_LOG.parent):
    _p.mkdir(parents=True, exist_ok=True)

MASTER_SEED = 20261017

# Study window of the synthetic cohort.
START_DATE = "2021-01-01"
END_DATE = "2025-12-31"

# The blind set is defined before any data exists: two whole sites that the
# models never see, plus every attendance at any site during 2025.
BLIND_SITES = ("G", "H")
BLIND_FROM = "2025-01-01"

# Observation grid for admitted attendances (hours after admission).
OBS_STEP_H = 4
OBS_HORIZON_H = 72
# Rolling alert horizon for the deterioration model.
ALERT_HORIZON_H = 24

# Local protocol parameters. They are configuration, not facts the model learns.
@dataclass(frozen=True)
class Protocol:
    analgesia_target_min: int = 30          # NICE CG143 target from presentation
    analgesia_target_ash_min: int = 60      # ASH 2020 suggests within one hour
    reassess_interval_min: int = 30         # until satisfactory relief
    reassess_stable_interval_min: int = 240  # thereafter at least every 4 hours
    spo2_flag: float = 94.0                  # oxygen saturation red flag (percent)
    spo2_drop_flag: float = 3.0              # fall from the patient's baseline
    temp_flag: float = 38.0                  # fever threshold (Celsius)
    rr_flag: int = 24                        # respiratory rate red flag
    rr_low_flag: int = 10                    # possible opioid related hypoventilation
    hb_drop_flag: float = 2.0                # g/dL below steady state
    # The deterioration alert threshold is not set here: it is fixed on development data during
    # training and stored with the model (data/models/acs_model.json).

PROTOCOL = Protocol()

@dataclass(frozen=True)
class CohortSize:
    patients: int = 16000
    sites: tuple = ("A", "B", "C", "D", "E", "F", "G", "H")

COHORT = CohortSize()
