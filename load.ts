// Loads the bundle: embedded (single file build) or fetched from data/bundle.json.
import { initText } from "../engine/text";
import { Copilot } from "../engine/copilot";

export async function loadBundle(): Promise<any> {
  const el = document.getElementById("cv-bundle");
  let data: any;
  if (el && el.textContent && el.textContent.trim().length > 10) {
    const bin = Uint8Array.from(atob(el.textContent.trim()), (c) => c.charCodeAt(0));
    const stream = new Blob([bin]).stream().pipeThrough(new DecompressionStream("gzip"));
    data = JSON.parse(await new Response(stream).text());
  } else {
    const r = await fetch("data/bundle.json");
    if (!r.ok) throw new Error(`Could not load data/bundle.json (${r.status}). Run make bundle first.`);
    data = await r.json();
  }
  initText(data.synonyms, data.stop);
  return data;
}

export function makeCopilot(data: any): Copilot {
  return new Copilot({ protocol: data.protocol, index: data.index, ranker: data.ranker, situation_terms: data.situation_terms,
    model: data.model, sources: data.sources });
}

export const FEATURE_LABELS: Record<string, string> = {
  spo2: "oxygen saturation", spo2_gap: "saturation below baseline", spo2_change_8h: "saturation change over 8 h", spo2_min: "lowest saturation",
  rr: "respiratory rate", rr_change_8h: "respiratory rate change over 8 h", hr: "heart rate", hr_change_8h: "heart rate change over 8 h",
  temp: "temperature", temp_max: "highest temperature", pain: "pain score", pain_change_8h: "pain change over 8 h", opioid_load: "cumulative opioid load",
  opioid_8h: "opioid in last 8 h", spirometry_frac: "incentive spirometry done", lab_available: "ward bloods available", lab_hb_change: "haemoglobin change",
  lab_plt_ratio: "platelet ratio to arrival", lab_wbc_change: "white cell change", lab_crp_change: "CRP change", lab_ldh_ratio: "LDH ratio to arrival",
  hours: "hours since admission", age: "age", female: "female", severe_genotype: "HbSS or HbS beta zero", hbf_pct: "foetal haemoglobin",
  hydroxyurea: "on hydroxyurea", prior_acs_capped: "previous acute chest syndrome", asthma: "asthma", history_acs: "acute chest syndrome in this record",
  high_frequency_attender: "frequent attender", renal_impairment: "renal impairment", complaint_abdominal: "abdominal presentation",
  complaint_fever: "fever presentation", complaint_other: "other presentation", pain_arrival: "arrival pain score", spo2_gap_arrival: "arrival saturation gap",
  temp_arrival: "arrival temperature", rr_arrival: "arrival respiratory rate", hr_arrival: "arrival heart rate", hb_drop_arrival: "arrival haemoglobin fall",
  wbc_arrival: "arrival white cells", plt_arrival: "arrival platelets", retic_arrival: "arrival reticulocytes", ldh_arrival: "arrival LDH", crp_arrival: "arrival CRP",
};

export function hm(min: number): string {
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return h ? `${h} h ${String(m).padStart(2, "0")} min` : `${m} min`;
}
