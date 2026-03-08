# uv-bundler

**Build deployment-ready Python artifacts for Linux — from any machine. No Docker, no Linux build server.**

Data pipelines (Spark, Flink, Lambda) run on Linux. Your laptop runs macOS. Getting the right platform wheels into a deployment artifact has always required a dedicated Linux build environment — until now.

---

## The problem

- **You need Linux wheels, but you're on macOS.** A plain `pip install` fetches the wrong binaries for your host machine, not your target.
- **Switching to ARM (AWS Graviton, Apple Silicon) is painful.** Build pipelines are hard-coded to x86_64 and fail silently on aarch64.
- **ZIP hacks break in production.** Native extensions (NumPy, Pandas) crash with `ImportError` when bundled without the correct platform wheels.

---

## The solution

`uv-bundler` uses **Ghost Resolution** — `uv pip compile` + `uv pip install --python-platform` — to resolve and download the correct Linux wheels on any host OS. No Docker, no cross-compilation, no remote build environment.

One command produces a self-contained artifact that runs on Linux x86_64 or aarch64:

```bash
uv-bundler --target spark-prod
# → dist/my-spark-job-linux-x86_64.jar
```

Run it on Linux with zero pre-installed packages:

```bash
python my-spark-job-linux-x86_64.jar
# Running single Spark job with pyspark 3.5.0
```

---

## Quick start

**1. Add a target to `pyproject.toml`:**

```toml
[tool.uv-bundler]
project_name = "my-spark-job"
default_target = "spark-prod"

[tool.uv-bundler.targets.spark-prod]
format = "jar"
entry_point = "app.main:run"
platform = "linux"
arch = "x86_64"
python_version = "3.10"
manylinux = "2014"
```

**2. Build from any machine:**

```bash
# Verify config without building
uv-bundler --dry-run

# Build the artifact
uv-bundler --target spark-prod
```

**3. Validate it works — no packages needed inside the container:**

```bash
docker run --rm \
  -v "$(pwd)/dist:/artifacts" \
  python:3.10-slim \
  python /artifacts/my-spark-job-linux-x86_64.jar
# Running single Spark job with pyspark 3.5.0
```

---

## Cross-arch builds

Build for a different architecture without any additional tooling:

```bash
# Build for ARM from any host (macOS, Linux x86_64, ...)
uv-bundler --target spark-prod --arch aarch64
# → dist/my-spark-job-linux-aarch64.jar
```

Ghost Resolution fetches `manylinux2014_aarch64` wheels and bundles them directly — the host arch is irrelevant.

---

## How it works

`uv-bundler` follows a 5-step lifecycle:

1. **Context hydration** — reads `pyproject.toml`, merges CLI overrides, validates the entry point module path.
2. **Ghost Resolution** — runs `uv pip compile --python-platform <target>` to pin platform-specific wheel hashes for the *target* OS, not the build host.
3. **Staging** — runs `uv pip install --target` to extract wheels into a staging directory alongside your source code.
4. **Bootstrap generation** — generates a `__main__.py` that correctly loads `site-packages` at runtime, including when executed directly from inside a zip archive (zipapp mode).
5. **Assembly** — bundles everything into the requested format.

---

## Artifact formats

### JAR — Spark / Flink

- Self-contained zipapp, runnable with `python app.jar`
- Includes `META-INF/MANIFEST.MF` for JVM tooling compatibility
- Dependencies bundled under `site-packages/` inside the archive
- Build fails if `.dylib` or `.dll` binaries are detected (Linux targets only)

### ZIP — AWS Lambda / general deployment

- Same internal layout as JAR (bootstrap + `site-packages/` + sources)
- Suited for Lambda Layers and generic zip-based deployments

### PEX — Airflow / schedulers

- Single-file executable Python environment via the `pex` CLI
- Uses a platform tag (e.g. `manylinux2014_x86_64-cp-310-cp310`) for cross-platform resolution
- First build downloads packages from PyPI; subsequent builds use the cache
- Cache `$PEX_ROOT` (default `~/.pex`) in CI to avoid repeated downloads

---

## Configuration reference

```toml
[tool.uv-bundler]
project_name = "analytics-engine"    # Used in artifact filename
default_target = "spark-prod"         # Target used when --target is omitted
output_base = "./dist"                # Output directory (override via OUT_DIR env var)

[tool.uv-bundler.targets.spark-prod]
# Core
format = "jar"                        # "jar" | "pex" | "zip"
entry_point = "app.main:run"          # module.submodule:function

# Resolution (cross-platform)
platform = "linux"                    # "linux" | "macos" | "windows"
arch = "x86_64"                       # "x86_64" | "aarch64"
python_version = "3.10"
manylinux = "2014"                    # "2010" | "2014" | numeric (e.g. "31")

# Packaging
compression = "deflated"              # "stored" | "deflated"

# Advanced
exclude = ["tests/*", "**/__pycache__", "*.pyc", ".git*"]
extra_files = { "config/prod.yaml" = "resources/config.yaml" }
```

> **`OUT_DIR`** environment variable overrides `output_base` and takes precedence over the TOML value.

---

## CLI reference

```
uv-bundler [OPTIONS]

Options:
  --target TEXT           Target name from [tool.uv-bundler.targets.*]
  --platform TEXT         Override platform  (linux | macos | windows)
  --arch TEXT             Override arch      (x86_64 | aarch64)
  --python-version TEXT   Override Python version (e.g. 3.10)
  --manylinux TEXT        Override manylinux tag  (e.g. 2014)
  --dry-run               Print resolved config without building
```

---

## Installation

```bash
pip install uv-bundler
# or
uv tool install uv-bundler   # installs uv-bundler as an isolated global CLI
```

---

## Installation (development)

```bash
git clone https://github.com/amarlearning/uv-bundler.git
cd uv-bundler

# Install uv — https://docs.astral.sh/uv/
brew install uv   # macOS

make setup        # creates .venv and installs all dev deps

make fmt          # format
make lint         # ruff + mypy
make test         # unit + integration tests
```

---

## Contributing

- Branch: `feature/<desc>` or `fix/<desc>`
- Commit: imperative mood, ≤ 50 chars summary
- Quality gate: `make fmt && make lint && make type && make test`
- PR: include rationale; update docs if behavior changes

---

## License

[Apache License 2.0](./LICENSE)
