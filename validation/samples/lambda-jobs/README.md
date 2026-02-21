# lambda-jobs

AWS Lambda style project demonstrating how uv-pack can prepare a Lambda ZIP
target using the `zip` packaging driver.

## Overview

This example defines a single Lambda entry point:

- `lambda_jobs.handler:handler`

The handler normalizes an incoming event and returns a simple JSON-like
response structure expected by API Gateway style integrations.

## Prerequisites

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
validation/samples/lambda-jobs/
  pyproject.toml
  lambda_jobs/
    __init__.py
    handler.py
    utils.py
```

## uv-pack configuration

The `lambda-zip` target in `pyproject.toml`:

- Uses the `zip` format
- Targets `linux-x86_64` for AWS Lambda
- Uses Python 3.10 and manylinux2014 wheels
- Sets `lambda_jobs.handler:handler` as the entry point

## Building with uv-pack

Change into the sample directory (where this README and `pyproject.toml` live):

```bash
cd /path/to/validation/samples/lambda-jobs
```

Run a dry-run build using the default `lambda-zip` target:

```bash
uv-pack --dry-run
```

This command:

- Validates the entry point
- Computes a target-specific lockfile using uv
- Prints the configuration that would be used for packaging

You can override resolution attributes to validate alternate Lambda platforms:

```bash
uv-pack \
  --target lambda-zip \
  --platform linux \
  --arch x86_64 \
  --python-version 3.11 \
  --manylinux 2014 \
  --dry-run
```

## Expected outputs

- A `.uv-pack` directory containing a lockfile for the Lambda target
- Dry-run console output summarizing the Lambda configuration and target
  resolution parameters

## Using the handler locally

You can invoke the handler directly with Python:

```bash
cd /path/to/lambda-jobs
python -c "from lambda_jobs.handler import handler; print(handler({'message': 'hello', 'request_id': 'abc'}, None))"
```

## Troubleshooting

- If `uv-pack` is not found, ensure it is installed globally (for example with
  `pip install uv-pack` or `uv tool install uv-pack`) and available on PATH.
- If uv reports network issues while resolving dependencies, retry the command
  or configure a local package mirror for boto3 wheels.
- This example project does not depend on the uv-pack source repository; you
  can copy the directory to any location and run the commands above there.
