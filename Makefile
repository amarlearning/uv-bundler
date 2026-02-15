UV ?= uv
UV_ENV ?= .venv

.PHONY: install
install:
	@echo "Use 'make setup' to create env via uv lock/sync"

.PHONY: clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -exec rm -f {} +
	rm -rf .ruff_cache
	rm -rf .coverage
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	find . -type d -name "*.egg-info" -exec rm -rf {} +

.PHONY: setup
setup:
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "Error: 'uv' is required. Install via 'brew install uv' or see https://docs.astral.sh/uv/"; \
		exit 1; \
	fi
	UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) sync --all-extras

.PHONY: lock
lock:
	$(UV) lock

.PHONY: ensure-uv
ensure-uv:
	@if ! command -v $(UV) >/dev/null 2>&1; then \
		echo "Error: 'uv' is required. Install via 'brew install uv' or see https://docs.astral.sh/uv/"; \
		exit 1; \
	fi

.PHONY: ensure-sync
ensure-sync: ensure-uv
	@if [ ! -x "$(UV_ENV)/bin/ruff" ] || [ ! -x "$(UV_ENV)/bin/black" ] || [ ! -x "$(UV_ENV)/bin/mypy" ] || [ ! -x "$(UV_ENV)/bin/pytest" ]; then \
		echo "Syncing dev environment in $(UV_ENV) via uv (--all-extras) ..."; \
		UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) sync --all-extras; \
	fi

.PHONY: fmt
fmt: ensure-sync
	UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) run ruff check --select I --fix .
	UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) run black .

.PHONY: lint
lint: ensure-sync
	UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) run ruff check .
	UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) run black --check .

.PHONY: type
type: ensure-sync
	UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) run mypy src

.PHONY: test
test: ensure-sync
	UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) run pytest -q

.PHONY: cov
cov: ensure-sync
	UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) run pytest -q --cov=uv_pack --cov-report=term-missing

.PHONY: pre-commit
pre-commit: ensure-sync
	UV_PROJECT_ENVIRONMENT=$(UV_ENV) $(UV) run pre-commit run --all-files
