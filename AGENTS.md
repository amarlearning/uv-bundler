# AGENTS.md — uv-bundler

> Context for AI coding agents working in this repository.

---

## What this project does

**uv-bundler** builds deployment-ready Python artifacts (JAR, ZIP, PEX) for Linux targets from any host OS (macOS, Windows, Linux). It solves the cross-platform wheel problem by using **Ghost Resolution**: `uv pip compile` + `uv pip install --python-platform` fetches the correct Linux wheels without Docker or a Linux build server.

**Core use cases:**
- Spark / Flink jobs packaged as fat JARs with bundled `manylinux` wheels
- AWS Lambda ZIPs targeting Graviton (aarch64) built from macOS
- PEX executables for Airflow / schedulers with native C extensions (NumPy, Pandas)
- **Slim mode**: source-only artifacts for environments where deps are pre-installed (EMR, Lambda Layers)

---

## Repository layout

```
src/uv_bundler/
├── cli.py              # Entry point + build orchestration (Typer app)
├── domain/
│   ├── config.py       # Pydantic config models (UvPackConfig, TargetConfig, GlobalConfig)
│   └── platforms.py    # PEP 508 platform tag generation
├── services/
│   ├── config_loader.py  # TOML parsing, target resolution, CLI override merging
│   ├── resolver.py       # uv pip compile + install command builders
│   ├── staging.py        # StagingPaths dataclass
│   ├── packager.py       # Archive builders: JAR, ZIP, PEX
│   └── bootstrap.py      # __main__.py code generation (sys.path setup)
└── adapters/
    ├── fs.py             # Filesystem helpers (create/clean staging dir)
    └── process.py        # Subprocess runner (Runner protocol)

tests/
├── unit/               # Pure unit tests — all subprocess calls mocked via Runner
├── integration/        # Real builds, no mocks (use actual uv/pip/pex)
└── benchmarks/         # Performance tests (only run on push to main)

validation/samples/     # End-to-end sample projects used in CI artifact validation
  ├── single-spark-job/ # JAR + ZIP + PEX, with slim variants
  ├── numpy-etl/        # PEX, native extensions (x86_64 + aarch64)
  └── lambda-zip/       # ZIP for Lambda Graviton
```

---

## Development setup

```bash
# Requires: uv installed (brew install uv)
make setup        # uv sync --all-extras → creates .venv
make fmt          # ruff --fix + black
make lint         # ruff check + black --check
make type         # mypy src
make test         # pytest tests/unit + tests/integration
make cov          # pytest with coverage report
make build        # uv build (wheel + sdist)
```

All four must pass before a PR: `make fmt && make lint && make type && make test`

---

## Build lifecycle (the 5 steps)

Understanding this helps when touching any part of the code:

1. **Context hydration** — `config_loader.py` reads `[tool.uv-bundler]` from `pyproject.toml`, resolves the target, merges CLI overrides
2. **Ghost Resolution** — `resolver.py` runs `uv pip compile --python-platform <target>` to produce a lockfile for the *target* OS, not the build host. **Skipped in slim mode.**
3. **Staging** — `resolver.py` runs `uv pip install --target` to extract wheels into `.uv-bundler/staging/site-packages/`. **Skipped in slim mode.**
4. **Bootstrap generation** — `bootstrap.py` renders a `__main__.py` that sets up `sys.path` correctly both inside a zip archive and when extracted
5. **Assembly** — `packager.py` builds JAR/ZIP/PEX from staged sources + site-packages

---

## Key abstractions to know

### Runner protocol (`adapters/process.py`)
```python
Runner = Callable[[list[str], Path | None], int]
```
All subprocess calls (uv, pip, pex) flow through a `Runner`. Unit tests inject a fake runner to avoid real subprocess calls. Never call `subprocess` directly — always accept and use a `Runner` parameter.

### Platform tag generation (`domain/platforms.py`)
`pep508_platform(platform, arch, manylinux)` converts config values to uv/pip `--python-platform` strings:
- `("linux", "x86_64", "2014")` → `"x86_64-manylinux2014"`
- `("linux", "aarch64", "31")` → `"aarch64-manylinux_2_31"`
- `("macos", "aarch64", None)` → `"aarch64-apple-darwin"`

### StagingPaths (`services/staging.py`)
Immutable dataclass — single source of truth for where files land during a build:
- `root` → `.uv-bundler/staging/`
- `site_packages` → `.uv-bundler/staging/site-packages/`
- `sources` → `.uv-bundler/staging/src/`

### Config models (`domain/config.py`)
Pydantic models with `frozen=True`. Entry point must be `"module.submodule:function"` — the validator calls `assert_module_path_exists()` to confirm the module is importable. Config is immutable once loaded.

---

## Artifact formats

| Format | Use case | Binary safety check | Extra tooling |
|--------|----------|--------------------|-|
| **JAR** | Spark, Flink | Fails on `.dylib`/`.dll` in Linux targets | None |
| **ZIP** | Lambda, generic | None | None |
| **PEX** | Airflow, schedulers | Via pex itself | `pex` must be on PATH |

PEX is the only format that handles C extensions safely from inside a zip (it extracts `.so` files before import). For NumPy/Pandas use PEX, not JAR/ZIP.

---

## Slim mode

`--slim` / `slim = true` skips Ghost Resolution and staging entirely. Source files only are bundled. Artifact names gain a `-slim` infix: `my-job-linux-x86_64-slim.jar`. Use when the runtime already provides dependencies (EMR, Lambda Layer, Airflow DAG environment).

`slim_exclude` patterns stack on top of `exclude` — only applied during slim builds.

---

## Configuration (`pyproject.toml`)

```toml
[tool.uv-bundler]
project_name = "my-app"       # → artifact filename prefix
default_target = "prod"
output_base = "./dist"         # overridden by OUT_DIR env var

[tool.uv-bundler.targets.prod]
format = "jar"                 # jar | zip | pex
entry_point = "app.main:run"   # module.submodule:function
platform = "linux"             # linux | macos | windows
arch = "x86_64"                # x86_64 | aarch64
python_version = "3.10"
manylinux = "2014"             # 2010 | 2014 | numeric (e.g. 31)
compression = "deflated"       # deflated | stored
slim = false
slim_exclude = ["tests/**", "*.pyi"]
exclude = ["tests/*", "*.pyc"]
extra_files = { "config/prod.yaml" = "resources/config.yaml" }
```

CLI flags (`--arch`, `--platform`, `--python-version`, `--manylinux`, `--slim`) override TOML values at runtime.

---

## Testing approach

**Unit tests** (`tests/unit/`) mock all subprocess calls via fake `Runner` — fast, no external tools needed.

**Integration tests** (`tests/integration/`) perform real builds — require `uv` (and `pex` for PEX tests) on PATH. These run on Ubuntu only in CI.

**Benchmarks** (`tests/benchmarks/`) only run on `push` to `main`, not on PRs.

When adding a feature:
- Add unit test covering the new code path (use a fake Runner)
- Add/extend integration test if a new subprocess command or file layout is introduced
- Do **not** mock `uv`/`pex` in integration tests — that defeats their purpose

---

## Common pitfalls

- **Don't call subprocess directly.** Always thread a `Runner` through so tests can inject fakes.
- **Don't mutate config objects.** `TargetConfig` / `GlobalConfig` are Pydantic frozen models.
- **Binary safety:** `build_jar()` / `build_zip()` for Linux targets call `_ensure_no_incompatible_binaries()`. Keep this check in place.
- **Slim mode skips resolver entirely.** Any code touching `staging.site_packages` must be guarded by `not config.slim`.
- **`OUT_DIR` env var beats `output_base` in config.** Check `_output_root()` in `cli.py:_output_root` before touching output path logic.
- **PEX caching:** PEX downloads are cached in `$PEX_ROOT` (`~/.pex`). CI artifact workflow caches this between runs — don't change the cache key without updating `.github/workflows/artifacts.yml`.
- **manylinux numeric tags:** `"31"` → `manylinux_2_31`, `"2014"` → `manylinux2014` (legacy alias). Logic lives in `platforms.py`.

---

## Adding a new artifact format

1. Add the format literal to `TargetConfig.format` in `domain/config.py`
2. Implement `build_<format>()` in `services/packager.py` — accept `Runner` for any subprocess calls
3. Dispatch in `cli.py:_assemble()`
4. Add unit test in `tests/unit/test_packager_<format>.py`
5. Add integration test in `tests/integration/test_packager_<format>_integration.py`
6. Add a validation sample in `validation/samples/` and wire it into `artifacts.yml`

---

## CI workflows

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `ci.yml` | PR + push | Lint → unit tests (4 Python versions) → integration tests → benchmarks (main only) |
| `artifacts.yml` | PR + push | Cross-arch builds on real hardware (x86_64 + aarch64), Docker validation |
| `release.yml` | `git tag v*` | Build wheel + sdist, publish to PyPI via OIDC trusted publishing |

---

## PR and commit conventions

- Branch: `feature/<desc>` or `fix/<desc>`
- Commit: imperative mood, ≤ 50 chars subject line
- Quality gate before opening PR: `make fmt && make lint && make type && make test`
- Update `README.md` if user-visible behavior changes
- Bump version in `src/uv_bundler/__init__.py` and `pyproject.toml` for releases

---

## External tool dependencies (not Python packages)

These must be on PATH at build time — they are not listed as Python dependencies:

| Tool | Purpose | Required for |
|------|---------|-------------|
| `uv` | Ghost Resolution (compile + install) | All normal (non-slim) builds |
| `pip` | Wheel pre-download for PEX offline builds | PEX format only |
| `pex` | PEX assembly | PEX format only |
