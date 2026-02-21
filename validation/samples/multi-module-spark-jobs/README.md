# multi-module-spark-jobs

Multi-module Spark jobs demonstrating how uv-pack handles shared utilities and
multiple coordinated Spark entry points.

## Overview

This example defines two Spark jobs:

- `jobs.daily_sales:run` for production reporting
- `jobs.hourly_metrics:run` for operational monitoring

Both jobs share utilities from the `common` package. uv-pack targets map each
job to a distinct build target with its own platform and Python version.

## Prerequisites

- Java and a pyspark-compatible environment (optional, for running jobs locally)
- `uv` installed globally on your system
- `uv-pack` installed globally on your system

Install `uv` (if not already installed). For example:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install `uv-pack` as a global CLI tool (one of):

```bash
pip install uv-pack
# or
uv tool install uv-pack
```

## Project layout

```text
validation/samples/multi-module-spark-jobs/
  pyproject.toml
  common/
    __init__.py
    io.py
  jobs/
    __init__.py
    daily_sales.py
    hourly_metrics.py
```

## uv-pack configuration

Targets are defined in `pyproject.toml`:

- `spark-prod`
  - JAR format for `linux-x86_64`
  - Entry point `jobs.daily_sales:run`
- `spark-dev`
  - JAR format for `linux-aarch64`
  - Entry point `jobs.hourly_metrics:run`

The default target is `spark-prod`.

## Building with uv-pack

Change into the sample directory (where this README and `pyproject.toml` live):

```bash
cd /path/to/validation/samples/multi-module-spark-jobs
```

Run a dry-run build for the default production target:

```bash
uv-pack --dry-run
```

This command:

- Resolves `spark-prod` as the default target
- Validates the entry point `jobs.daily_sales:run`
- Uses uv to compute a lockfile for `linux-x86_64` and Python 3.10

### Dev target for alternate architecture

To validate the `spark-dev` target, which uses `linux-aarch64` and Python 3.11:

```bash
uv-pack --target spark-dev --dry-run
```

You can further override resolution attributes at the CLI:

```bash
uv-pack \
  --target spark-dev \
  --platform linux \
  --arch aarch64 \
  --python-version 3.11 \
  --manylinux 2014 \
  --dry-run
```

## Expected outputs

For each target, uv-pack and uv will:

- Generate a `.uv-pack` lockfile specific to the target platform
- Print a summary of the selected target, entry point, and resolution settings

The shared `common` package is included once in the staging area and reused by
both jobs, demonstrating how uv-pack works with multiple modules in a single
project. The example does not depend on the uv-pack source repository and can
be copied and used from any location.

## Troubleshooting

- If Spark sessions fail to start, verify that Java is installed and compatible.
- If `uv-pack` is not found, ensure it is installed globally (for example with
  `pip install uv-pack` or `uv tool install uv-pack`) and available on PATH.
- If uv reports network issues while resolving dependencies, retry the command
  or configure a local package mirror for pyspark wheels.
- To run jobs locally (beyond dry-run builds), install `pyspark` into a virtual
  environment in this directory and run the `jobs.*` entry points using Python.
