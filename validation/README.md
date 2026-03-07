## uv-pack validation guide

All commands assume the repo root unless stated otherwise.

---

## Phase 1 – local smoke test

```bash
# Sync dev environment
make setup

# Dry-run against the single-spark-job sample
cd validation/samples/single-spark-job
uv-pack --dry-run
```

Expected output:

```
uv-pack dry run
- target: spark-jar
- format: jar
- entry_point: app.main:run
- platform: linux, arch: x86_64
- python: 3.10, manylinux: 2014
```

---

## Phase 2 – build artifacts locally (no Docker required)

uv-pack uses "Ghost Resolution" — `uv pip compile` and `uv pip install --python-platform`
resolve and download the correct target-platform wheels on any host OS. No Docker
or Linux build environment is needed to produce Linux artifacts from macOS or Windows.

```bash
cd validation/samples/single-spark-job

# Build all three formats for linux/x86_64
uv-pack --target spark-jar
uv-pack --target spark-zip
uv-pack --target spark-pex

# Cross-arch: build for linux/aarch64 from any host
uv-pack --target spark-jar --arch aarch64
uv-pack --target spark-zip --arch aarch64
uv-pack --target spark-pex --arch aarch64
```

Artifacts land in `dist/` (or the directory set by `OUT_DIR` / `output_base`):

```
validation/samples/single-spark-job/dist/
  single-spark-job-linux-x86_64.jar
  single-spark-job-linux-x86_64.zip
  single-spark-job-linux-x86_64.pex
```

---

## Phase 3 – runtime validation in Docker

Artifacts are fat/self-contained — no packages need to be pre-installed in the
container. Each format is run directly inside a `python:3.10-slim` container
(the target environment) and the output is verified:

```bash
# Copy artifacts to the validation output directory first
mkdir -p validation/out/single-spark-job
cp validation/samples/single-spark-job/dist/* validation/out/single-spark-job/

STEM="single-spark-job-linux-x86_64"
IMAGE="python:3.10-slim"

# Run JAR
docker run --rm \
  -v "$(pwd)/validation/out/single-spark-job:/artifacts" \
  "$IMAGE" \
  sh -c "python /artifacts/$STEM.jar | grep 'Running single Spark job with pyspark'"

# Run ZIP
docker run --rm \
  -v "$(pwd)/validation/out/single-spark-job:/artifacts" \
  "$IMAGE" \
  sh -c "python /artifacts/$STEM.zip | grep 'Running single Spark job with pyspark'"

# Run PEX
docker run --rm \
  -v "$(pwd)/validation/out/single-spark-job:/artifacts" \
  "$IMAGE" \
  sh -c "python /artifacts/$STEM.pex | grep 'Running single Spark job with pyspark'"
```

All three commands should print:

```
Running single Spark job with pyspark 3.5.0
```

Or use the Makefile shortcut (uses `validate_artifacts.py` for content + runtime checks):

```bash
make -C validation test-artifacts-linux TARGET_OS=linux TARGET_ARCH=x86_64
```

---

## Phase 4 – CI workflow

Artifacts are built and validated automatically in CI via `.github/workflows/artifacts.yml`.

**Build jobs** (`build-linux` matrix):
- `ubuntu-latest` (x86_64 host) → builds for `linux/aarch64` (Ghost Resolution cross-arch)
- `ubuntu-24.04-arm` (aarch64 host) → builds for `linux/x86_64` (Ghost Resolution cross-arch)
- Uses native `uv-pack` CLI; no Docker needed for building
- PEX downloads cached via `~/.pex` (keyed by target arch + pyproject hash)

**Validate jobs** (`validate-linux` matrix):
- `ubuntu-latest` → validates `linux/x86_64` artifacts inside `python:3.10-slim` Docker
- `ubuntu-24.04-arm` → validates `linux/aarch64` artifacts inside `python:3.10-slim` Docker
- Each format (JAR, ZIP, PEX) runs as a separate step; output verified with `grep`
- No packages pre-installed: fat artifacts are self-contained

The cross-arch build-then-validate design proves that uv-pack's Ghost Resolution
produces artifacts that actually run on their intended target platform.
