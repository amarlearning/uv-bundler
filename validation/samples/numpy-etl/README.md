# numpy-etl

Demonstrates uv-pack's cross-arch native extension wheel resolution using NumPy and Pandas.

## What this showcases

NumPy and Pandas ship as compiled C extensions — each platform (x86_64, aarch64) gets a
different `.so` binary. A naive `pip install` on macOS downloads macOS wheels, which crash
with `ImportError` when deployed to Linux. A plain ZIP bundling your local venv would embed
the wrong binaries.

uv-pack's Ghost Resolution (`uv pip install --python-platform`) fetches the correct
`manylinux2014_x86_64` or `manylinux2014_aarch64` wheels regardless of your build host.

Because numpy/pandas are C extensions, the **PEX format** is used — PEX extracts `.so`
files to disk before importing, which plain JAR/ZIP cannot do.

## Project layout

```
validation/samples/numpy-etl/
  pyproject.toml
  etl/
    __init__.py
    main.py        # run() entry point
    transform.py   # pandas + numpy computation
```

## Targets

| Target        | Format | Platform      |
|---------------|--------|---------------|
| `etl-x86_64`  | PEX    | linux/x86_64  |
| `etl-aarch64` | PEX    | linux/aarch64 |

## Build

```bash
cd validation/samples/numpy-etl

# Verify config
uv-pack --dry-run

# Build for linux/x86_64 (from any host OS)
uv-pack --target etl-x86_64

# Build for linux/aarch64 — Ghost Resolution fetches aarch64 numpy/pandas wheels
uv-pack --target etl-aarch64
```

Artifacts land in `dist/`:

```
dist/numpy-etl-linux-x86_64.pex
dist/numpy-etl-linux-aarch64.pex
```

## Validate (Docker)

```bash
# Run on native x86_64 Linux
docker run --rm \
  -v "$(pwd)/dist:/artifacts" \
  python:3.10-slim \
  python /artifacts/numpy-etl-linux-x86_64.pex
# ETL complete: mean_sales=1080.0 peak_region=eu-west
```

No packages are pre-installed — numpy and pandas are fully bundled inside the PEX.
