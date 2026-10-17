# API

Start the service with `make serve`. Interactive documentation is at `http://localhost:8000/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | version, whether the model and index are built, audit chain status |
| POST | `/api/copilot` | run the copilot for one attendance at one minute, with an optional question |
| GET | `/api/attendances` | list attendances, filtered by `split`, `site`, `complaint`, `admitted`, `acs` |
| GET | `/api/attendance/{id}` | the raw event timeline, ward observations and bloods for one attendance |
| GET | `/api/cards` | the guidance cards and their sources |
| GET | `/api/equity` | the equity audit report |
| GET | `/api/evaluation` | the evaluation summary |
| GET | `/api/model` | the deterioration model training report |
| GET | `/api/audit` | recent audit records and chain verification |

## Copilot request

```json
{ "attendance_id": "ATT0000123", "now_min": 45, "question": "which painkiller should we give first" }
```

## Copilot response, abridged

```json
{
  "phase": "early",
  "actions": [
    { "code": "GIVE_FIRST_ANALGESIA", "kind": "clock", "overdue": true, "due_min": 30, "card": "G001" },
    { "code": "FOLLOW_PLAN", "kind": "analgesia", "plan_cite": ["PLAN00412.A"], "card": "G003" }
  ],
  "sentences": [
    { "text": "First analgesia is overdue: 45 minutes since arrival against a target of 30 minutes; give it now.",
      "cites": ["R.arrival", "R.analgesia", "G001"], "verified": true, "section": "actions" }
  ],
  "risk": null,
  "guard": { "redacted": "which painkiller should we give first", "flags": [] },
  "sources": [ { "id": "G001", "kind": "guidance", "title": "Analgesia within 30 minutes of presentation", "source": "NICE CG143 ..." } ],
  "trace": [ { "node": "guard", "ms": 0.1 } ]
}
```

Citation identifiers: `G` followed by three digits is a guidance card; `PLAN` identifiers ending in `.A` to `.D` are sections of the patient's signed plan; `H.` identifiers are previous attendances; `R.` identifiers are facts from the live record; `M.acs` is the deterioration model's output.
