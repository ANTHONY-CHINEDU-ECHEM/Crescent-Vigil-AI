// Input guard: a port of crescent_vigil/agent/guard.py.
const REDACTIONS: [string, RegExp][] = [
  ["NHS_NUMBER", /\b\d{3}[ \-]?\d{3}[ \-]?\d{4}\b/g],
  ["EMAIL", /\b[\w.+]+@[\w]+(?:\.[\w]+)+\b/g],
  ["PHONE", /(?:\+44\s?7\d{3}|\b07\d{3})\s?\d{3}\s?\d{3}\b/g],
  ["DATE", /\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b/g],
  ["POSTCODE", /\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b/gi],
  ["HOSPITAL_NUMBER", /\b(?:MRN|hospital (?:no|number))[:\s#]*[A-Z0-9]{5,}\b/gi],
  ["NAME", /\b(?:Mr|Mrs|Ms|Miss|Mx|Dr)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?/g],
  ["NAME", /\b(?:patient(?:'s)? name|name)\s*(?:is|:)\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?/gi],
];

const INJECTION = /ignore (?:all |any |the |your )?(?:previous |prior )?(?:instructions|rules|plan|guidance|guidelines)|disregard (?:the |your )?(?:plan|guidance|rules|instructions)|override (?:the )?(?:plan|guard|system)|you are now|system prompt|developer mode|pretend (?:to be|you)|jailbreak/i;
const DOSE = /\b(?:what|which|how much|how many|calculate|right|correct|max(?:imum)?)\b[^?.]{0,40}\b(?:dose|dosage|mg|milligrams?|micrograms?|ml)\b|\bmg\s*\/\s*kg\b|\bdose of\b|\bdosing\b|\bhow much\b[^?.]{0,30}\b(?:give|run|use|start|infuse|prescribe|draw up)\b/i;
const CRISIS = /self harm|harm (?:him|her|them)self|kill (?:my|him|her|them)sel|end it all|suicid|end (?:his|her|their|my) life|want to die/i;
const PAEDS = /\b(?:child|children|paediatric|pediatric|infant|baby|toddler|(?:[1-9]|1[0-5])\s*(?:year|yr)s?\s*old)\b/i;
const PREGNANCY = /\bpregnan/i;
const PETHIDINE = /\bpethidine|meperidine\b/i;
const DOMAIN = /sickle|crisis|pain|analges|opioid|morphine|oxycodone|diamorphine|plan|chest|oxygen|sat|fever|temperature|spleen|haemoglobin|\bhb\b|stroke|priapism|transfus|haematolog|spirometr|discharge|admi|observation|triage|sepsis|reassess|nsaid|ibuprofen|paracetamol|ketamine|pethidine|dose|breath|cough|weakness|seizure|pregnan|child|alert|risk|deteriorat|x ray|xray|blood|fluid|nurse|patient|hydroxyurea|ward|icu|critical care|meperidine|ketamine|naloxone|sedat|spleen|urolog/i;

export interface GuardResult { redacted: string; redactions: string[]; flags: string[] }

export function redact(text: string): [string, string[]] {
  const found: string[] = [];
  let out = text;
  for (const [label, rx] of REDACTIONS) {
    out = out.replace(rx, () => { found.push(label); return `[${label}]`; });
  }
  return [out, found];
}

export function check(text: string): GuardResult {
  text = text || "";
  const [red, found] = redact(text);
  const flags: string[] = [];
  if (INJECTION.test(text)) flags.push("injection");
  if (DOSE.test(text)) flags.push("dose_request");
  if (CRISIS.test(text)) flags.push("crisis");
  if (PAEDS.test(text)) flags.push("paediatric_scope");
  if (PREGNANCY.test(text)) flags.push("pregnancy_scope");
  if (PETHIDINE.test(text)) flags.push("pethidine");
  if (text.trim() && !DOMAIN.test(text) && !flags.includes("crisis")) flags.push("off_topic");
  return { redacted: red, redactions: found, flags };
}
