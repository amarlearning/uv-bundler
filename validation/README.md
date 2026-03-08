## uv-bundler validation guide

All commands assume the repo root unless stated otherwise.

---

## Samples

Three samples demonstrate different uv-bundler capabilities:

| Sample             | Format(s)     | Deps                   | Showcases                                        |
|--------------------|---------------|------------------------|--------------------------------------------------|
| `single-spark-job` | JAR, ZIP, PEX | pyspark (pure Python)  | All three formats; Linux wheels from any host    |
| `numpy-etl`        | PEX           | numpy, pandas (C exts) | Native extension arch resolution; x86_64+aarch64 |
| `lambda-zip`       | ZIP           | boto3 (pure Python)    | Lambda deployment; Graviton (aarch64) support    |

> **Why PEX for numpy-etl?** Python's zipimport cannot `dlopen` compiled `.so` files from
> inside a zip archive. PEX extracts `.so` files to disk before importing, making it the
> correct format for packages with C extensions (numpy, pandas, scikit-learn, etc.).

---

## Phase 1 – local smoke test

```bash
# Sync dev environment
make setup

# Dry-run against each sample
cd validation/samples/single-spark-job && uv-bundler --dry-run
cd validation/samples/numpy-etl        && uv-bundler --dry-run
cd validation/samples/lambda-zip       && uv-bundler --dry-run
```

Expected output for single-spark-job:

```
uv-bundler dry run
- target: spark-jar
- format: jar
- entry_point: app.main:run
- platform: linux, arch: x86_64
- python: 3.10, manylinux: 2014
```

---

## Phase 2 – build artifacts locally (no Docker required)

uv-bundler uses Ghost Resolution — `uv pip compile` and `uv pip install --python-platform`
resolve and download the correct target-platform wheels on any host OS. No Docker or
Linux build environment is needed to produce Linux artifacts from macOS or Windows.

```bash
# single-spark-job — all three formats for linux/x86_64
cd validation/samples/single-spark-job
uv-bundler --target spark-jar
uv-bundler --target spark-zip
uv-bundler --target spark-pex

# numpy-etl — PEX for x86_64 and aarch64 (Ghost Resolution fetches the right arch wheel)
cd validation/samples/numpy-etl
uv-bundler --target etl-x86_64
uv-bundler --target etl-aarch64

# lambda-zip — ZIP for x86_64 and Lambda Graviton (aarch64)
cd validation/samples/lambda-zip
uv-bundler --target lambda-x86_64
uv-bundler --target lambda-aarch64
```

Artifacts land in each sample's `dist/` directory:

```
validation/samples/single-spark-job/dist/
  single-spark-job-linux-x86_64.jar
  single-spark-job-linux-x86_64.zip
  single-spark-job-linux-x86_64.pex

validation/samples/numpy-etl/dist/
  numpy-etl-linux-x86_64.pex
  numpy-etl-linux-aarch64.pex

validation/samples/lambda-zip/dist/
  lambda-zip-linux-x86_64.zip
  lambda-zip-linux-aarch64.zip
```

---

## Phase 3 – runtime validation in Docker

Artifacts are fat/self-contained — no packages need to be pre-installed in the container.
Each format is run directly inside a `python:3.10-slim` container and the output is verified:

```bash
IMAGE="python:3.10-slim"

# single-spark-job
STEM="single-spark-job-linux-x86_64"
docker run --rm -v "$(pwd)/validation/samples/single-spark-job/dist:/artifacts" "$IMAGE" \
  sh -c "python /artifacts/$STEM.jar | grep 'Running single Spark job with pyspark'"
docker run --rm -v "$(pwd)/validation/samples/single-spark-job/dist:/artifacts" "$IMAGE" \
  sh -c "python /artifacts/$STEM.zip | grep 'Running single Spark job with pyspark'"
docker run --rm -v "$(pwd)/validation/samples/single-spark-job/dist:/artifacts" "$IMAGE" \
  sh -c "python /artifacts/$STEM.pex | grep 'Running single Spark job with pyspark'"

# numpy-etl (PEX — numpy/pandas C extensions loaded correctly via PEX)
STEM="numpy-etl-linux-x86_64"
docker run --rm -v "$(pwd)/validation/samples/numpy-etl/dist:/artifacts" "$IMAGE" \
  sh -c "python /artifacts/$STEM.pex | grep 'ETL complete'"

# lambda-zip
STEM="lambda-zip-linux-x86_64"
docker run --rm -v "$(pwd)/validation/samples/lambda-zip/dist:/artifacts" "$IMAGE" \
  sh -c "python /artifacts/$STEM.zip | grep 'lambda ok'"
```

Expected outputs:

```
Running single Spark job with pyspark 3.5.0
ETL complete: mean_sales=1080.0 peak_region=eu-west
lambda ok: status=200 body=test-123:hello
```

Or use the Makefile shortcut (validates all three samples at once):

```bash
make -C validation test-artifacts TARGET_OS=linux TARGET_ARCH=x86_64
```

---

## Phase 4 – CI workflow

Artifacts are built and validated automatically in CI via `.github/workflows/artifacts.yml`.

**Build jobs** (`build-linux` matrix):
- `ubuntu-latest` (x86_64 host) → builds all three samples for `linux/aarch64`
- `ubuntu-24.04-arm` (aarch64 host) → builds all three samples for `linux/x86_64`
- Ghost Resolution: `uv pip compile/install --python-platform` — no Docker needed for building
- PEX downloads cached via `~/.pex` (keyed by target arch + pyproject hash)

**Validate jobs** (`validate-linux` matrix):
- `ubuntu-latest` → validates `linux/x86_64` artifacts inside `python:3.10-slim` Docker
- `ubuntu-24.04-arm` → validates `linux/aarch64` artifacts inside `python:3.10-slim` Docker
- Separate step per format and sample — failures are immediately visible
- No packages pre-installed: all samples must be fully self-contained fat artifacts

The cross-arch build-then-validate design proves that Ghost Resolution produces artifacts
that actually run on their intended target platform.
