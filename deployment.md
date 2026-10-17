# Deployment

## Local

Requirements: Python 3.11 or later, Node 20 or later, about 2 GB of disk and 4 GB of memory.

```
pip install .
pip install pytest
make all          # generate, freeze, load, index, train, audit, evaluate on development data, draw figures
make bundle web   # export the browser bundle and build the interface
make serve        # API and interface on http://localhost:8000
```

`make evaluate_blind` scores the frozen blind set and appends a timestamp to `data/eval/blind_runs.json`. The repository ships with that run already made; running it again is visible in the log.

## Docker

```
docker compose up                                          # API and interface on port 8000
COMPOSE_PROFILES=llm docker compose up                     # also start Ollama
COMPOSE_PROFILES=llm CRESCENT_LLM=ollama docker compose up # use it for free text answers
```

With `CRESCENT_LLM=ollama` the answer to a free text question is written by a local model (`CRESCENT_LLM_MODEL`, default `llama3.1:8b`) from the top retrieved cards. Its sentences go through the same verifier as the extractive writer, and anything it writes without a valid citation is dropped. Clinical actions are never written by the language model.

## Static hosting

`make artifact` builds a single HTML page with the engine, the model and a 271 attendance bundle embedded and gzip compressed. It needs no server and makes no network calls after loading apart from fonts.

## Configuration

Local protocol parameters (the 30 minute analgesia target, reassessment interval, fever, saturation, respiratory rate and haemoglobin flags) live in `crescent_vigil/config.py`. Changing them changes the actions and the evidence text, and the parity fixture must be rebuilt with `make bundle`.
