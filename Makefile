# Everything a reader needs. `make reproduce` is the one that matters.
PY ?= python3
export PYTHONPATH := src

.PHONY: help install test reproduce record demo trajectory package clean

help:
	@echo "make install    install dependencies"
	@echo "make test       run the harness self-tests (no model needed)"
	@echo "make reproduce  replay the full benchmark offline and print the table"
	@echo "make demo       migrate one case live, with the human approval gate"
	@echo "make record     re-record the response cache against a live provider"
	@echo "make trajectory copy the build session transcript in, redacted"
	@echo "make package    build the submission archive"

install:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest tests/ -q

reproduce:
	$(PY) src/evaluate.py --variants all --replay --checkpoint auto

record:
	$(PY) src/evaluate.py --variants all --checkpoint auto

demo:
	$(PY) src/migrate.py data/cases/case_01_inventory/legacy_app.py

trajectory:
	$(PY) scripts/prepare_build_trajectory.py

package: test trajectory
	@rm -f submission.zip
	zip -qr submission.zip . \
	  -x '.git/*' '.venv/*' '__pycache__/*' '*/__pycache__/*' '*.pyc' \
	     '.pytest_cache/*' '.env' '.env.*' 'HANDOFF.md' 'submission.zip' \
	     'data/cases/case_99_flowintel_misp/legacy_app.py' \
	     'trajectories/cross_model/*'
	@echo "--- verifying the archive, not the working tree ---"
	@if unzip -l submission.zip | grep -qE '(^| |/)\.env($$|[^a-z])' | grep -v '\.env\.example'; then \
	  echo "FAIL: a dotenv file is inside the archive"; rm -f submission.zip; exit 1; fi
	@if unzip -p submission.zip | grep -qE 'sk-[A-Za-z0-9]{24,}'; then \
	  echo "FAIL: an api-key-shaped string is inside the archive"; rm -f submission.zip; exit 1; fi
	@echo "no .env, no key-shaped strings"
	@echo "wrote submission.zip ($$(du -h submission.zip | cut -f1), $$(unzip -l submission.zip | tail -1 | awk '{print $$2}') files)"

clean:
	rm -rf results/migrated trajectories/* .pytest_cache **/__pycache__
