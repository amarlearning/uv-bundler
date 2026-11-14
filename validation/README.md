# Artifact validation

The samples here are built by uv-bundler and then **run the way production runs them**.
Checking only that an archive builds, or that `python artifact.zip` works, can miss
the bugs users actually hit.

| Sample             | Format(s)     | Bundled deps            | Run with                                                      |
|--------------------|---------------|-------------------------|---------------------------------------------------------------|
| `single-spark-job` | JAR, ZIP, PEX | tabulate (pyspark is provided by the cluster) | `spark-submit --py-files` in the official `spark:4.0.1-python3` image |
| `numpy-etl`        | PEX           | numpy, pandas (native)  | `python job.pex` in a clean `python:3.10-slim` container      |
| `lambda-zip`       | ZIP           | orjson (native, not in the Lambda runtime) | the handler, invoked in AWS's `public.ecr.aws/lambda/python:3.12` image |

Slim artifacts and the Spark PEX are checked for structure only (`validate_artifacts.py`).

## Run locally

Needs `uv`, `pex` (`uv tool install pex`), `uv-bundler` and a running Docker.

```bash
make -C validation test-artifacts                     # linux/x86_64
make -C validation test-artifacts TARGET_ARCH=aarch64 # linux/aarch64
```

`test-artifacts` builds every sample into `validation/out/`, then calls
[`run_artifacts.sh`](run_artifacts.sh). A non-native `TARGET_ARCH` runs under Docker's
emulation, which is slower but works on any host.

## CI

`.github/workflows/artifacts.yml` builds each sample on hosts that differ from the target:
Linux x86_64 → aarch64, Linux aarch64 → x86_64, and macOS (Apple Silicon) → both. It then
runs `run_artifacts.sh` on a native runner for each target architecture.
