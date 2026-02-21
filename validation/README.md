## uv-pack validation quick guide

All commands assume the repo root:

```bash
cd /Users/amarpandey/Github/uv-pack
```

---

## Phase 1 – local wheel + smoke test

```bash
# clean previous artifacts
make clean

# build wheel
UV_PROJECT_ENVIRONMENT=.venv uv build

# fresh validation venv
python3 -m venv .venv_validation
source .venv_validation/bin/activate
pip install --upgrade pip

# install wheel
pip install dist/uv_pack-*-py3-none-any.whl

# smoke test against single-spark sample
cd validation/samples/single-spark-job
uv-pack --help
uv-pack --dry-run
```

Key checks:

- Wheel exists in `dist/uv_pack-*-py3-none-any.whl`
- `uv-pack --help` and `uv-pack --dry-run` exit with code `0`

---

## Phase 2 – Linux base image

```bash
# ensure wheel exists (Phase 1)
UV_PROJECT_ENVIRONMENT=.venv uv build

# build base image (uv-pack + uv + pex)
make -C validation docker-base-linux

# smoke test base image
docker run --rm uv-pack:base-linux --help
```

Key results:

- Image `uv-pack:base-linux` exists locally
- Running it prints `uv-pack` help

---

## Phase 3 – sample app in containers (jar, zip, pex)

Builder image is defined in `validation/docker/Dockerfile.linux.builder` and uses:

- Source: `/workspace/validation/samples/single-spark-job`
- Output: `/workspace/out/single-spark-job` (bound to `validation/out/single-spark-job`)
- `OUT_DIR=/workspace/out/single-spark-job`

Sample targets in `validation/samples/single-spark-job/pyproject.toml`:

- `spark-jar` (default) – JAR
- `spark-zip` – ZIP app
- `spark-pex` – PEX app

### 3.1 Build builder image and JAR

```bash
cd /Users/amarpandey/Github/uv-pack/validation

make build-example-linux

ls out/single-spark-job
# single-spark-job-linux-x86_64.jar
```

### 3.2 Build ZIP via Docker

```bash
cd /Users/amarpandey/Github/uv-pack/validation

docker run --rm -v $(pwd)/validation/out:/workspace/out uv-pack:builder-linux -t spark-zip

ls validation/out/single-spark-job
# single-spark-job-linux-x86_64.jar  single-spark-job-linux-x86_64.zip
```

### 3.3 Build PEX via Docker

```bash
cd /Users/amarpandey/Github/uv-pack/validation

docker run --rm -v $(pwd)/validation/out:/workspace/out uv-pack:builder-linux -t spark-pex

ls validation/out/single-spark-job
# single-spark-job-linux-x86_64.jar  single-spark-job-linux-x86_64.zip  single-spark-job-linux-x86_64.pex
```

At this point:

- `single-spark-job-linux-x86_64.jar`, `.zip`, and `.pex` are all produced by the validation Docker images
- All artifacts live under `validation/out/single-spark-job`

---

## Phase 4 – Linux multi-arch targets

Use the same builder image to build artifacts for different Linux architectures by overriding `--platform` and `--arch` in the uv-pack CLI.

### 4.1 Build linux-x86_64 JAR

```bash
cd /Users/amarpandey/Github/uv-pack/validation

docker run --rm \
  -v $(pwd)/out:/workspace/out \
  uv-pack:builder-linux \
  --platform linux --arch x86_64 -t spark-jar

ls out/single-spark-job
# single-spark-job-linux-x86_64.jar
```

### 4.2 Build linux-aarch64 JAR

```bash
cd /Users/amarpandey/Github/uv-pack/validation

docker run --rm \
  -v $(pwd)/validation/out:/workspace/out \
  uv-pack:builder-linux \
  --platform linux --arch aarch64 -t spark-jar

ls validation/out/single-spark-job
# single-spark-job-linux-x86_64.jar  single-spark-job-linux-aarch64.jar
```

Notes:

- The `--platform`/`--arch` flags control the **target** platform encoded into the artifact and its filename.
- For building the container images themselves as linux/amd64 or linux/arm64, you can optionally use:

  ```bash
  DOCKER_PLATFORM=linux/amd64 make -C validation build-example-linux
  DOCKER_PLATFORM=linux/arm64 make -C validation build-example-linux
  ```

- Non-Linux targets (macOS/Windows) are validated via native CI runners as described in `VALIDATION_PLAN.md`.

---

## Phase 5 – artifact validation (Linux runtime)

Use a lightweight Python container to validate the JAR, ZIP, and PEX artifacts produced for the `single-spark-job` example.

From the repo root:

```bash
cd /Users/amarpandey/Github/uv-pack

# validate linux-x86_64 artifacts
make -C validation test-artifacts-linux TARGET_OS=linux TARGET_ARCH=x86_64

# validate linux-aarch64 artifacts (after building them)
make -C validation test-artifacts-linux TARGET_OS=linux TARGET_ARCH=aarch64
```

What this does:

- Runs a `python:3.12-slim` container
- Mounts the repo under `/workspace` and uses `validation/validate_artifacts.py`
- Checks that the artifacts in `validation/out/single-spark-job` contain expected files
- Executes the JAR, PEX, and ZIP artifacts with Python (they are Python zipapps)
- Fails with a non-zero exit code if:
  - Any required path is missing inside an artifact
  - Any runtime process exits non-zero
  - The expected log line (`Running single Spark job with pyspark`) is not present

---

## Phase 6 – CI workflow for artifact builds

Artifacts are built and validated in CI via `.github/workflows/build-and-test-artifacts.yml`.

- `build-wheel` job:
  - Builds the uv-pack wheel on `ubuntu-latest` using `uv build`.
  - Publishes `dist/uv_pack-*-py3-none-any.whl` as a CI artifact.
- `build-artifacts-linux` job:
  - Runs on an `ubuntu-latest` (x86_64) runner.
  - Uses the wheel artifact to build the Linux base image (`make -C validation docker-base-linux`).
  - Builds the builder image (`validation/docker/Dockerfile.linux.builder`).
  - Runs the builder to produce `linux-aarch64` artifacts:
    - `single-spark-job-linux-aarch64.jar`
    - `single-spark-job-linux-aarch64.zip`
    - `single-spark-job-linux-aarch64.pex`
  - Uploads the resulting artifacts as CI artifacts.
- `validate-artifacts-linux-aarch64` job:
  - Runs on an `ubuntu-24.04-arm` (arm64) runner.
  - Downloads the `linux-aarch64` artifacts built on `ubuntu-latest` (x86_64).
  - Runs `validation/validate_artifacts.py` with:
    - `--target-os linux --target-arch aarch64`
  - Fails the workflow if validation fails.
- `build-artifacts-linux-from-arm` job:
  - Runs on an `ubuntu-24.04-arm` (arm64) runner.
  - Uses the wheel artifact to build the Linux base image (`make -C validation docker-base-linux`) on arm64.
  - Builds the builder image (`validation/docker/Dockerfile.linux.builder`) on arm64.
  - Runs the builder to produce `linux-x86_64` artifacts:
    - `single-spark-job-linux-x86_64.jar`
    - `single-spark-job-linux-x86_64.zip`
    - `single-spark-job-linux-x86_64.pex`
  - Uploads the resulting artifacts as CI artifacts under the name `single-spark-job-linux-x86_64-from-arm`.
- `validate-artifacts-linux-x86_64` job:
  - Runs on an `ubuntu-latest` (x86_64) runner.
  - Downloads the `linux-x86_64` artifacts built on `ubuntu-24.04-arm` (arm64).
  - Runs `validation/validate_artifacts.py` with:
    - `--target-os linux --target-arch x86_64`
  - Fails the workflow if validation fails.

Windows and macOS artifact jobs are sketched as placeholders and can be enabled later on
native CI runners.
