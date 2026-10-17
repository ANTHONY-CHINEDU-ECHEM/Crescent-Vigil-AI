PY ?= python3

.PHONY: all data freeze db index train audit evaluate evaluate_blind figures bundle web artifact test serve clean

all: data freeze db index train audit evaluate figures

data:            ## generate the synthetic cohort
	$(PY) -m crescent_vigil.synth.generate

freeze:          ## freeze and hash scenarios, gold actions and questions (run once, before any model)
	$(PY) -m crescent_vigil.eval.splits

db:              ## load the event store
	$(PY) -c "from crescent_vigil.timeline.store import build_db; build_db()"

index:           ## build the retrieval index and fit the ranker on development questions
	$(PY) -m crescent_vigil.retrieval.index

train:           ## train the deterioration models on development attendances
	$(PY) -m crescent_vigil.models.acs
	$(PY) -c "from crescent_vigil.models.acs import write_export; write_export()"

audit:           ## run the analgesia equity audit
	$(PY) -m crescent_vigil.equity.audit

evaluate:        ## development evaluation only
	$(PY) -m crescent_vigil.eval.evaluate

evaluate_blind:  ## score the frozen blind set once; the run is appended to data/eval/blind_runs.json
	$(PY) -m crescent_vigil.eval.evaluate --blind

figures:
	$(PY) -m crescent_vigil.eval.figures

bundle:          ## export the browser bundle and the parity fixture
	$(PY) -m crescent_vigil.export.bundle

web:             ## build the interface into web/dist
	cd web && npm install && npm run build

artifact:        ## single self contained page with the bundle embedded
	cd web && npm run build:single && node scripts/inline.mjs

test:
	$(PY) -m pytest -q
	cd web && npx vitest run

serve:
	$(PY) -m uvicorn crescent_vigil.api.app:app --host 0.0.0.0 --port 8000

clean:
	rm -rf web/dist web/dist_single data/timeline.duckdb
