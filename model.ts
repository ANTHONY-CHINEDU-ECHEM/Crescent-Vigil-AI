// Deterioration model inference: a port of the exported gradient boosted trees, the isotonic
// calibration, the occlusion explanation and models/features.py snapshot_features.
import type { Snapshot } from "./snapshot";

export interface Trees { baseline: number; trees: { f: number[]; t: number[]; l: number[]; r: number[]; leaf: number[]; v: number[]; m: number[] }[] }
export interface ModelExport {
  features: string[]; admission_features: string[]; rolling: Trees; admission: Trees;
  calibration: { x: number[]; y: number[] }; admission_calibration: { x: number[]; y: number[] };
  medians: number[]; explain_features: number[]; threshold: number;
}

export function rawPredict(t: Trees, x: number[]): number {
  let out = t.baseline;
  for (const tr of t.trees) {
    let n = 0;
    while (!tr.leaf[n]) {
      const v = x[tr.f[n]];
      if (v === null || Number.isNaN(v)) n = tr.m[n] ? tr.l[n] : tr.r[n];
      else n = v <= tr.t[n] ? tr.l[n] : tr.r[n];
    }
    out += tr.v[n];
  }
  return 1 / (1 + Math.exp(-out));
}

export function interp(x: number, xp: number[], fp: number[]): number {
  if (x <= xp[0]) return fp[0];
  const n = xp.length;
  if (x >= xp[n - 1]) return fp[n - 1];
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (xp[mid] <= x) lo = mid; else hi = mid;
  }
  const slope = (fp[lo + 1] - fp[lo]) / (xp[lo + 1] - xp[lo]);
  return slope * (x - xp[lo]) + fp[lo];
}

export function predict(m: ModelExport, feats: Record<string, number>) {
  const x = m.features.map((f) => feats[f]);
  const cal = (row: number[]) => interp(rawPredict(m.rolling, row), m.calibration.x, m.calibration.y);
  const p = cal(x);
  const drivers = m.explain_features.map((j) => {
    const alt = x.slice();
    alt[j] = m.medians[j];
    return { feature: m.features[j], value: x[j], typical: m.medians[j], effect: p - cal(alt) };
  });
  const top = drivers.map((d, i) => ({ d, i })).sort((a, b) => (Math.abs(b.d.effect) - Math.abs(a.d.effect)) || (a.i - b.i)).slice(0, 4).map((z) => z.d);
  return { risk_24h: p, alert: p >= m.threshold, threshold: m.threshold, drivers: top };
}

export function snapshotFeatures(snap: Snapshot): Record<string, number> | null {
  const d = snap.derived;
  if (d.admitted_min === null || snap.now_min < d.admitted_min) return null;
  const ward = snap.vitals_series.filter((v) => v.source === "ward");
  if (!ward.length) return null;
  const pt = snap.patient, at = snap.attendance, h = snap.history;
  const tri = snap.vitals_series.find((v) => v.source === "triage");
  const al = snap.labs.series[0];
  const f: Record<string, number> = {
    age: at.age ?? pt.age, female: pt.sex === "F" ? 1 : 0,
    severe_genotype: ["HbSS", "HbSbeta0", "HbSD"].includes(pt.genotype) ? 1 : 0, hbf_pct: pt.hbf_pct,
    hydroxyurea: pt.hydroxyurea ? 1 : 0, prior_acs_capped: Math.min(pt.prior_acs, 4), asthma: pt.asthma ? 1 : 0,
    history_acs: h.acs_after_admission + h.acs_at_arrival, high_frequency_attender: at.high_frequency_attender ? 1 : 0,
    renal_impairment: pt.renal_impairment ? 1 : 0, complaint_abdominal: at.complaint === "abdominal" ? 1 : 0,
    complaint_fever: at.complaint === "fever" ? 1 : 0, complaint_other: ["pain", "abdominal", "fever"].includes(at.complaint) ? 0 : 1,
    pain_arrival: at.pain_score_arrival, spo2_gap_arrival: pt.baseline_spo2 - tri.spo2, temp_arrival: tri.temp, rr_arrival: tri.rr,
    hr_arrival: tri.hr, hb_drop_arrival: pt.steady_state_hb - al.hb, wbc_arrival: al.wbc, plt_arrival: al.plt, retic_arrival: al.retic,
    ldh_arrival: al.ldh, crp_arrival: al.crp,
  };
  const cur = ward[ward.length - 1];
  const hours = cur.hour;
  const lag = ward.find((v) => v.hour === hours - 8) || tri;
  const allv = [tri, ...ward];
  const mean = ward.reduce((a, v) => a + (v.spirometry_done ? 1 : 0), 0) / ward.length;
  Object.assign(f, {
    hours, spo2: cur.spo2, spo2_gap: pt.baseline_spo2 - cur.spo2, spo2_change_8h: cur.spo2 - lag.spo2,
    spo2_min: Math.min(...allv.map((v) => v.spo2)), rr: cur.rr, rr_change_8h: cur.rr - lag.rr, hr: cur.hr, hr_change_8h: cur.hr - lag.hr,
    temp: cur.temp, temp_max: Math.max(...allv.map((v) => v.temp)), pain: cur.pain, pain_change_8h: cur.pain - lag.pain,
    opioid_load: cur.opioid_load, opioid_8h: cur.opioid_load - (lag.source === "ward" ? lag.opioid_load : 0.0), spirometry_frac: mean,
  });
  const adm = d.admitted_min;
  const later = snap.labs.series.slice(1).filter((l: any) => l.minute <= adm + hours * 60);
  if (later.length) {
    const l = later[later.length - 1];
    Object.assign(f, { lab_available: 1.0, lab_hb_change: l.hb - al.hb, lab_plt_ratio: l.plt / al.plt, lab_wbc_change: l.wbc - al.wbc,
      lab_crp_change: l.crp - al.crp, lab_ldh_ratio: l.ldh / al.ldh });
  } else {
    Object.assign(f, { lab_available: 0.0, lab_hb_change: 0.0, lab_plt_ratio: 1.0, lab_wbc_change: 0.0, lab_crp_change: 0.0, lab_ldh_ratio: 1.0 });
  }
  return f;
}
