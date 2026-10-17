// Snapshot replay: a port of crescent_vigil/timeline/store.py (Timeline.snapshot and derive).
export const ARRIVAL_VITALS_MIN = 6;
export const ARRIVAL_LABS_MIN = 60;
export const LATER_LAB_DELAY_MIN = 60;

export interface AttRecord {
  id: string;
  patient: any;
  attendance: any;
  plan: any | null;
  arrival_vitals: { spo2: number; rr: number; hr: number; temp: number; pain: number };
  arrival_labs: Record<string, number>;
  events: any[];
  obs: any[];
  labs: any[];
  history: any;
  meta: any;
}

export interface Snapshot {
  attendance_id: string; now_min: number; patient: any; attendance: any; plan: any | null; events: any[];
  vitals: any; vitals_series: any[]; labs: any; history: any; derived: any;
}

export function admittedMin(r: AttRecord): number | null {
  const e = r.events.find((x) => x.event === "admitted");
  return e ? e.minute : null;
}

export function snapshot(r: AttRecord, now: number): Snapshot {
  const events = r.events.filter((e) => e.minute <= now);
  const series: any[] = [];
  if (now >= ARRIVAL_VITALS_MIN) {
    const a = r.arrival_vitals;
    series.push({ minute: ARRIVAL_VITALS_MIN, spo2: a.spo2, rr: a.rr, hr: a.hr, temp: a.temp, pain: a.pain, opioid_load: 0.0, source: "triage" });
  }
  const adm = admittedMin(r);
  if (adm !== null) {
    for (const o of r.obs) {
      const m = adm + o.hour * 60;
      if (m <= now) series.push({ minute: m, spo2: o.spo2, rr: o.rr, hr: o.hr, temp: o.temp, pain: o.pain, opioid_load: o.opioid_load,
        spirometry_done: o.spirometry_done, source: "ward", hour: o.hour });
    }
  }
  const vitals = series.length ? series[series.length - 1] : {};
  let labs: any = {};
  if (now >= ARRIVAL_LABS_MIN) labs = { minute: ARRIVAL_LABS_MIN, ...r.arrival_labs };
  const labSeries: any[] = Object.keys(labs).length ? [{ ...labs }] : [];
  if (adm !== null) {
    for (const l of r.labs) {
      const m = adm + l.hour * 60 + LATER_LAB_DELAY_MIN;
      if (l.hour > 0 && m <= now) {
        const d = { minute: m, hb: l.hb, wbc: l.wbc, plt: l.plt, crp: l.crp, ldh: l.ldh };
        labSeries.push(d);
        labs = { ...labs, ...d };
      }
    }
  }
  labs.series = labSeries;
  return { attendance_id: r.id, now_min: now, patient: r.patient, attendance: r.attendance, plan: r.plan, events,
    vitals, vitals_series: series, labs, history: r.history, derived: derive(events, now) };
}

export function derive(events: any[], now: number) {
  const first = events.find((e) => e.event === "analgesia_given");
  const re = events.filter((e) => e.event === "pain_reassessed");
  const adm = events.find((e) => e.event === "admitted");
  const acs = events.find((e) => e.event === "acs_diagnosed");
  return {
    analgesia_given_min: first ? first.minute : null,
    analgesia_agent: first ? first.agent ?? null : null,
    analgesia_route: first ? first.route ?? null : null,
    reassessed_min: re.length ? re[0].minute : null,
    admitted_min: adm ? adm.minute : null,
    hours_since_admission: adm ? (now - adm.minute) / 60 : null,
    acs_diagnosed_min: acs ? acs.minute : null,
    left_department: events.some((e) => e.event === "left_department"),
    discharged: events.some((e) => e.event === "discharged"),
  };
}
