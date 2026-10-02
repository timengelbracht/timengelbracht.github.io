PY ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: help install sync build serve preview test lint clean

help:  ## list commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*## "}{printf "  make %-9s %s\n", $$1, $$2}'

$(BIN)/sitegen: pyproject.toml
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -e ".[dev]"
	@touch $@

install: $(BIN)/sitegen  ## create .venv and install everything

sync: install  ## pull papers, abstracts, links and teasers
	$(BIN)/sitegen sync

build: install  ## render site/
	$(BIN)/sitegen build

serve: build  ## serve site/ on http://localhost:8000
	$(BIN)/sitegen serve

preview: install  ## sync + build + serve
	$(BIN)/sitegen preview

test: install  ## run the tests (no network needed)
	$(BIN)/pytest -q

lint: install  ## check code style
	$(BIN)/ruff check src tests

clean:  ## remove generated site/ and caches
	rm -rf site .pytest_cache .ruff_cache
