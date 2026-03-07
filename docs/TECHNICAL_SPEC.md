# Technical Specification: uv-pack (v1.0)

## 1. Project Objective

uv-pack is a specialized build-orchestration tool designed to produce platform-agnostic, deployment-ready Python artifacts (JAR, PEX, ZIP) from any host OS. It leverages uv for high-speed, cross-platform dependency resolution and provides a "Standardized Build" contract for Data Engineering pipelines.

## 2. Configuration Schema (pyproject.toml)

The tool uses a hierarchical configuration. Global settings provide fallbacks, while target-specific settings allow for platform overrides.

```toml
[tool.uv-pack]
# --- Global Defaults ---
project_name = "analytics-engine"
default_target = "spark-prod"
output_base = "./dist"          # Global output directory

[tool.uv-pack.targets.spark-prod]
# --- Core Settings ---
format = "jar"                  # Options: "jar", "pex", "zip"
entry_point = "app.main:run"    # Callable string: module.submodule:function

# --- Resolution Settings (Cross-Platform) ---
platform = "linux"              # Options: "linux", "macos", "windows"
arch = "x86_64"                 # Options: "x86_64", "aarch64" (ARM)
python_version = "3.10"         # Specific Python version for the target
manylinux = "2014"              # glibc version (Options: "2010", "2014", or numeric e.g. "31")

# --- Packaging Options ---
compression = "deflated"        # Options: "stored", "deflated"

# --- Advanced Options ---
# Paths to exclude from the final artifact (Glob patterns)
exclude = ["tests/*", "**/__pycache__", "*.pyc", ".git*"]
# Additional files to inject (e.g., config files outside the source tree)
extra_files = { "config/prod.yaml" = "resources/config.yaml" }
```

> **Note on `OUT_DIR`:** The output directory can also be overridden via the `OUT_DIR` environment variable, which takes precedence over `output_base`.

## 3. The Execution Lifecycle (Step-by-Step)

### Step 1: Context Hydration

The engine reads `pyproject.toml` and merges it with CLI overrides.

- **Validation**: checks that the `entry_point` module path exists in the local source tree.
- **Platform Mapping**: translates `platform + arch + manylinux` into a PEP 508 platform string.
  For example, `linux + x86_64 + manylinux=2014` → `x86_64-manylinux2014`.
  Without a manylinux constraint, falls back to the generic triple: `x86_64-unknown-linux-gnu`.

### Step 2: The "Ghost" Resolution

uv-pack invokes `uv pip compile` to resolve dependencies for the **target environment** — not the local host. This produces a pinned lockfile with the correct platform-specific wheel hashes.

```bash
uv pip compile pyproject.toml \
  --python-platform x86_64-manylinux2014 \
  --python-version 3.10 \
  --output-file .uv-pack/resolved.lock
```

Why: ensures the lockfile contains manylinux-compatible wheel hashes even when building from macOS or Windows.

### Step 3: Staging & Wheel Extraction

The engine creates a temporary `.uv-pack/staging/` directory and installs the resolved dependencies into it using `uv pip install --target`, which extracts `.whl` files directly into `staging/site-packages/`:

```bash
uv pip install \
  -r .uv-pack/resolved.lock \
  --target .uv-pack/staging/site-packages \
  --python-platform x86_64-manylinux2014 \
  --python-version 3.10
```

The local project source code is then copied into `staging/src/`.

### Step 4: The Bootstrap Generation

For JAR and ZIP formats, uv-pack generates a `__main__.py` bootstrap script that:

1. Detects whether it is running from inside a zip archive (zipapp mode) by checking `sys.path[0].is_file()`.
2. In zipapp mode, inserts `<archive>/site-packages` into `sys.path` — Python's zipimport resolves this sub-path within the archive without a filesystem presence.
3. In extracted/development mode, looks for `site-packages/` relative to `__file__`.
4. Dynamically imports and calls the configured entry point function.

```python
import importlib, sys
from pathlib import Path

def _setup_path():
    archive = Path(sys.path[0]) if sys.path else None
    if archive is not None and archive.is_file():
        # zipapp mode: archive/site-packages is resolved by zipimport
        sys.path.insert(0, str(archive) + '/site-packages')
    else:
        root = Path(__file__).parent
        site_packages = root / 'site-packages'
        if site_packages.exists():
            sys.path.insert(0, str(site_packages))

def _run():
    _setup_path()
    mod = importlib.import_module('app.main')
    fn = getattr(mod, 'run')
    res = fn()
    return res if isinstance(res, int) else 0

if __name__ == '__main__':
    raise SystemExit(_run())
```

This makes JAR and ZIP artifacts **truly self-contained** — no packages need to be pre-installed on the runtime host.

### Step 5: Final Assembly (Target Specifics)

Depending on the `format` field, the engine performs the final wrap:

- **JAR**: Adds `META-INF/MANIFEST.MF` for JVM tooling compatibility. Validates that no `.dylib`/`.dll` binaries are present (Linux targets only). Runs as `python app.jar`.
- **ZIP**: Same internal layout as JAR (bootstrap + `site-packages/` + sources). Suited for AWS Lambda Layers or general deployment. Runs as `python app.zip`.
- **PEX**: Invokes the `pex` CLI with `-r resolved.lock --platform <canonical-tag> --sources-directory staging/src`. The canonical tag format is `manylinux2014_x86_64-cp-310-cp310`. PEX manages its own wheel cache (`~/.pex`); first build downloads from PyPI, subsequent builds use the cache.

## 4. Key Decisions & Decision Log

| Decision Point | Selection | Technical Justification |
| :---- | :---- | :---- |
| Glibc Compatibility | Default to manylinux2014 | Matches older Linux kernels found in Enterprise Spark (EMR 6.x) and Databricks. |
| Dependency Location | `/site-packages` subdir | Keeps the root of the JAR clean and prevents source modules from being overwritten by dependency files. |
| Resolution Tool | `uv pip compile` + `uv pip install --target` | Fastest resolver available; `--target` extracts wheels directly without a venv. |
| Cross-Arch | Ghost Resolution (no Docker) | `uv pip compile/install --python-platform` resolves for the target OS entirely on the build host, eliminating Docker as a build dependency. |
| Bootstrap path injection | `sys.path[0]` (zipapp-aware) | `Path(__file__).parent.exists()` fails inside zip archives; `sys.path[0]` is always the zip file when running as a zipapp, and Python's zipimport handles `zipfile/subdir` sys.path entries. |

## 5. Artifact Directory Structure (Inside the JAR/ZIP)

```
artifact.jar
├── __main__.py               # Generated bootstrap
├── app/                      # User source code
│   └── main.py
├── site-packages/            # Extracted wheels (installed by uv pip install --target)
│   ├── pyspark/
│   ├── py4j/
│   └── ...
└── META-INF/
    └── MANIFEST.MF           # JVM Metadata (JAR only)
```

## 6. Module Overview

| Module | Responsibility |
| :---- | :---- |
| `config_loader` | Parses `pyproject.toml`, validates the `[tool.uv-pack]` section, merges CLI overrides |
| `resolver` | Builds and invokes `uv pip compile` (lock) and `uv pip install --target` (extract) commands |
| `packager` | Assembles JAR, ZIP, and PEX artifacts from the staging directory |
| `bootstrap` | Generates the `__main__.py` entry point script embedded in JAR/ZIP artifacts |
| `staging` | Defines and manages the temporary `.uv-pack/staging/` directory layout |
| `cli` | Typer-based CLI: `uv-pack [--target] [--dry-run] [--platform] [--arch] [--python-version] [--manylinux]` |
