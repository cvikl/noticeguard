PY ?= python
PORT ?= 8000

.PHONY: run test bench seed install

install:
	$(PY) -m pip install -r requirements.txt

run:
	$(PY) -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

test:
	$(PY) -m pytest -q

# Populate the committed LLM cache for the demo document sets (Maya, Leo, Leo+email).
seed:
	$(PY) -m app.seed

bench:
	$(PY) -m bench.run_benchmark

bench-generate:
	$(PY) data/benchmark/generate_variants.py
