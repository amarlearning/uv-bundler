# single-spark-job

Minimal Spark job demonstrating how to configure and validate a single target with uv-bundler.

## Overview

This example represents a simple Spark application packaged as a JAR-style artifact.
The project defines one target, `spark-jar`, that builds for `linux-x86_64` with
Python 3.10 and manylinux2014 wheels.

The `app.main:run` entry point prints the detected pyspark version and exits.

## Prerequisites

- Java and pyspark-compatible environment (optional, for running the job locally)
- `uv` installed globally on your system
- `uv-bundler` installed globally on your system

Install `uv` (if not already installed). For example:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install `uv-bundler` as a global CLI tool (one of):

```bash
pip install uv-bundler
# or
uv tool install uv-bundler
```

## Project layout

```text
validation/samples/single-spark-job/
  pyproject.toml
  app/
    __init__.py
    main.py
```

## Building with uv-bundler

Change into the sample directory (where this README and `pyproject.toml` live):

```bash
cd /path/to/validation/samples/single-spark-job
```

Run a dry-run build using the default target:

```bash
uv-bundler --dry-run
```

This command:

- Reads `pyproject.toml` in this directory
- Resolves the `spark-jar` target as the default
- Validates the entry point `app.main:run`
- Asks `uv` to compute a Linux-specific lockfile (ghost resolution)

### Explicit target selection

You can also select the target explicitly:

```bash
uv-bundler --target spark-jar --dry-run
```

### Cross-platform experiments

Override resolution settings to simulate different Python versions and architectures:

```bash
uv-bundler \
  --target spark-jar \
  --platform linux \
  --arch aarch64 \
  --python-version 3.11 \
  --manylinux 2014 \
  --dry-run
```

These commands do not require the uv-bundler source repository. They only use the
globally installed `uv` and `uv-bundler` binaries to validate configuration and
produce lockfiles for the requested target platform.

## Expected outputs

- A `.uv-bundler` directory containing a lockfile for the target platform
- Dry-run console output describing the chosen target and resolution parameters

## Troubleshooting

- If `uv-bundler` is not found, ensure it is installed globally (for example with
  `pip install uv-bundler` or `uv tool install uv-bundler`) and available on PATH.
- If `uv` is missing, install it from https://docs.astral.sh/uv/.
- If you want to run the Spark job locally (not just dry-run builds), install
  `pyspark` into a virtual environment in this directory (`uv venv && uv pip
  install pyspark`), then run `python -m app.main` manually.
