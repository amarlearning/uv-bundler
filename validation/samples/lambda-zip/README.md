# lambda-zip

Demonstrates uv-bundler building a self-contained AWS Lambda ZIP for both x86_64 and
aarch64 (Graviton) from any host OS.

## What this showcases

AWS Lambda supports ARM-based Graviton processors, which offer better price-performance
than x86_64. Switching to Graviton means your build pipeline must produce `aarch64`
artifacts — hard if your CI is locked to Intel runners.

uv-bundler's Ghost Resolution builds the correct `linux/aarch64` ZIP from any host:

```bash
# From a macOS laptop or x86_64 CI runner
uv-bundler --target lambda-aarch64
# → dist/lambda-zip-linux-aarch64.zip  (ready for Lambda Graviton)
```

boto3 and its dependencies are all pure Python — ZIP format works perfectly and
produces a single, self-contained archive with no packages pre-installed at runtime.

## Project layout

```
validation/samples/lambda-zip/
  pyproject.toml
  lambda_jobs/
    __init__.py
    handler.py   # AWS Lambda handler(event, context) — the actual Lambda entrypoint
    utils.py     # event normalisation
    main.py      # run() — smoke-test entry point used by uv-bundler bootstrap
```

## Targets

| Target           | Format | Platform      | Use case             |
|------------------|--------|---------------|----------------------|
| `lambda-x86_64`  | ZIP    | linux/x86_64  | Standard Lambda      |
| `lambda-aarch64` | ZIP    | linux/aarch64 | Lambda Graviton (ARM)|

## Build

```bash
cd validation/samples/lambda-zip

# Verify config
uv-bundler --dry-run

# Standard Lambda (x86_64)
uv-bundler --target lambda-x86_64

# Lambda Graviton — built from any host via Ghost Resolution
uv-bundler --target lambda-aarch64
```

Artifacts land in `dist/`:

```
dist/lambda-zip-linux-x86_64.zip
dist/lambda-zip-linux-aarch64.zip
```

## Validate (Docker)

```bash
# Run on native x86_64 Linux — no packages pre-installed
docker run --rm \
  -v "$(pwd)/dist:/artifacts" \
  python:3.10-slim \
  python /artifacts/lambda-zip-linux-x86_64.zip
# lambda ok: status=200 body=test-123:hello
```

## Lambda deployment

Deploy the ZIP to AWS Lambda with `lambda_jobs.handler.handler` as the handler string
and `python3.10` runtime. The entry point for uv-bundler (`lambda_jobs.main:run`) is only
used for local validation — the real Lambda handler is `handler.py:handler`.
