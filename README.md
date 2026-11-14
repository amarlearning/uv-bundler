# uv-bundler

[![PyPI](https://img.shields.io/pypi/v/uv-bundler)](https://pypi.org/project/uv-bundler/)
[![Python](https://img.shields.io/pypi/pyversions/uv-bundler)](https://pypi.org/project/uv-bundler/)
[![Artifacts validated](https://github.com/amarlearning/uv-bundler/actions/workflows/artifacts.yml/badge.svg)](https://github.com/amarlearning/uv-bundler/actions/workflows/artifacts.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](./LICENSE)

**Build AWS Lambda ZIPs, Spark `--py-files` archives and PEX files for Linux (x86_64 or
aarch64) from your Mac. No Docker, no Linux build box.**

```bash
uv tool install uv-bundler
uv-bundler --target lambda --arch aarch64
# → dist/my-fn-linux-aarch64.zip   (Linux Graviton wheels, built on macOS)
```

Your `pyproject.toml` already lists the dependencies. uv-bundler asks [uv](https://docs.astral.sh/uv/)
for the **target's** wheels (`--python-platform`), not your laptop's, and packs them with
your code in the layout the target runtime expects.

> Not affiliated with Astral. uv-bundler is a community tool built on top of uv.

---

## Why

`pip install` on a Mac fetches macOS wheels. Zip them up for Lambda or Spark, and the
first import of NumPy, orjson, pydantic-core or cryptography fails on Linux. The usual
fixes are a Docker build (`sam build --use-container`, a hand-written Dockerfile) or a
Linux CI job just for packaging.

uv-bundler does it in one command, on any host, in seconds, from config you check in.

---

## Quick start

**1. Describe the artifact in `pyproject.toml`:**

```toml
[tool.uv-bundler]
project_name = "my-fn"
default_target = "lambda"

[tool.uv-bundler.targets.lambda]
format = "zip"
entry_point = "my_fn.main:run"   # used by `python my-fn.zip`; Lambda calls your handler
platform = "linux"
arch = "x86_64"                  # or override with --arch aarch64
python_version = "3.12"
manylinux = "2014"
```

**2. Build:**

```bash
uv-bundler                 # → dist/my-fn-linux-x86_64.zip
uv-bundler --arch aarch64  # → dist/my-fn-linux-aarch64.zip
uv-bundler --dry-run       # show the resolved config, build nothing
```

**3. Deploy** with the tools you already use (below).

---

## Use it with

### AWS Lambda — `format = "zip"`

Your code and its dependencies sit at the root of the ZIP, which is the layout Lambda imports from.

```bash
aws lambda update-function-code --function-name my-fn \
  --zip-file fileb://dist/my-fn-linux-aarch64.zip
# handler: my_fn.handler.handler   runtime: python3.12   architecture: arm64
```

Native dependencies work, because Lambda extracts the ZIP before importing. With SAM or
CDK, point `CodeUri` / `Code.fromAsset` at the ZIP.

### Spark (EMR, Databricks, spark-on-k8s) — `format = "jar"` or `"zip"`

```bash
spark-submit --py-files dist/my-job-linux-x86_64.jar driver.py
```

Driver and executors both import your package and its dependencies from the archive.
**Keep pyspark out of `[project].dependencies`**: the cluster provides it. Put it in a
dev group (`[dependency-groups] dev = ["pyspark"]`) so you have it locally but never ship it.

`.jar` is a zip with a JVM-friendly manifest; PySpark accepts `.jar`, `.zip` and `.egg` in
`--py-files`. Python can't import native extensions (`.so`) from inside a zip on the path,
so for NumPy and similar dependencies on Spark use a PEX (see PySpark's *Python package
management* docs).

### Airflow, cron, schedulers, Spark with native deps — `format = "pex"`

```bash
python dist/my-job-linux-x86_64.pex
```

A [PEX](https://docs.pex-tool.org/) is a single executable file containing a whole
environment, native extensions included. Needs `pex` on PATH when you build
(`uv tool install pex`).

### Slim mode — dependencies already on the target

```bash
uv-bundler --slim   # → dist/my-job-linux-x86_64-slim.jar, your source only
```

For EMR clusters with bootstrapped libraries, Lambda Layers, or Airflow workers with a shared
environment. Slim builds don't resolve anything.

---

## How it works

1. Reads `[tool.uv-bundler]`, applies CLI overrides, checks that the entry-point module exists.
2. `uv pip compile --python-platform x86_64-manylinux2014 …` pins versions for the **target**.
3. `uv pip install --target … --python-platform …` downloads the matching wheels.
   (PEX targets skip this step, because pex resolves the lockfile itself.)
4. Assembles the archive: sources and dependencies at the root, plus a `__main__.py` so
   `python artifact.zip` runs your `entry_point`.

### Compared with other approaches

| Approach | Docker? | Output | Notes |
|---|---|---|---|
| **uv-bundler** | No | ZIP, `--py-files` JAR/ZIP, PEX | One config for all three; macOS and Linux hosts tested in CI |
| `pex --platform …` | No | PEX only | What uv-bundler uses for PEX. Use it directly if PEX is all you need |
| `pip download --platform … --only-binary :all:` + a zip script | No | Whatever you script | Same idea; you maintain the script and the layout |
| `sam build --use-container`, Docker builds | Yes | Lambda | Can compile sdist-only packages, which uv-bundler can't |
| `venv-pack` / `conda-pack` | Linux build host | Spark archives | Packs an environment that must already exist on Linux |

---

## Limitations

- **Needs wheels for the target.** A dependency that only publishes an sdist with native
  code can't be compiled for another platform. Pin a version that ships a matching wheel,
  change `manylinux` / `python_version`, or build that artifact on Linux. Pure-Python
  sdists are fine.
- **Native extensions in JAR/ZIP only load where the archive is extracted** (Lambda yes,
  `--py-files` no). uv-bundler warns when a JAR contains them. Use PEX otherwise.
- **Resolves from `pyproject.toml`, not `uv.lock`.** Versions are pinned at build time for
  the target, so they can differ from your local lock.

---

## How it's tested

Every push runs [`artifacts.yml`](.github/workflows/artifacts.yml). It builds the
[sample projects](validation/) on Linux x86_64, Linux aarch64 and macOS (Apple Silicon),
always targeting a platform other than the build host. Each artifact then runs on native
hardware **the way production runs it**:

- the Lambda ZIP is invoked through AWS's own Lambda runtime image,
- the Spark JAR and ZIP run with `spark-submit --py-files` in the official Spark image, with
  pyspark *not* bundled,
- the NumPy/pandas PEX runs in a clean `python:3.10-slim` container.

Run the same checks locally with `make -C validation test-artifacts`.

---

## Configuration reference

```toml
[tool.uv-bundler]
project_name = "analytics-engine"    # artifact filename prefix
default_target = "spark-prod"         # used when --target is omitted
output_base = "./dist"                # output directory (OUT_DIR env var wins)

[tool.uv-bundler.targets.spark-prod]
format = "jar"                        # "jar" | "zip" | "pex"
entry_point = "app.main:run"          # module.submodule:function

platform = "linux"                    # "linux" | "macos" | "windows"
arch = "x86_64"                       # "x86_64" | "aarch64"
python_version = "3.12"               # default 3.12
manylinux = "2014"                    # "2010" | "2014" | glibc minor, e.g. "31"

compression = "deflated"              # "deflated" | "stored"
exclude = ["tests/*", "*.pyc"]        # glob patterns, relative to the project root
extra_files = { "config/prod.yaml" = "resources/config.yaml" }  # source → path in archive

slim = false                          # true = source only, no dependencies
slim_exclude = ["tests/**", "*.pyi"]  # extra excludes applied only to slim builds
```

Artifacts are named `<project_name>-<platform>-<arch>[-slim].<format>`.

## CLI reference

```
uv-bundler [OPTIONS]

  -t, --target TEXT       Target name from [tool.uv-bundler.targets.*]
  -p, --project PATH      Project directory containing pyproject.toml (default: .)
  --arch TEXT             Override arch            (x86_64 | aarch64)
  --platform TEXT         Override platform        (linux | macos | windows)
  --python-version TEXT   Override Python version  (e.g. 3.12)
  --manylinux TEXT        Override manylinux tag   (e.g. 2014, 28)
  --slim                  Bundle source only
  --dry-run               Print the resolved config without building
```

---

## Troubleshooting

**"failed to resolve/install dependencies" mentioning a source build.** A dependency has no
wheel for the target. See [Limitations](#limitations).

**"'uv' not found on PATH" / "'pex' not found on PATH".** `brew install uv` (or see
[uv's install docs](https://docs.astral.sh/uv/getting-started/installation/)), and
`uv tool install pex` for PEX targets.

**`ImportError` for a native module when running a JAR/ZIP in place.** Python can't load
`.so` files from inside a zip. Use `format = "pex"`, or deploy somewhere that extracts the
archive, as Lambda does.

---

## Development

```bash
git clone https://github.com/amarlearning/uv-bundler.git && cd uv-bundler
make setup                                   # .venv with dev deps (needs uv)
make fmt && make lint && make type && make test
make -C validation test-artifacts            # real-runtime checks (needs Docker + pex)
```

Branches `feature/<desc>` / `fix/<desc>`, imperative commit subjects of 50 characters or
fewer, and docs updated whenever behavior changes. See [AGENTS.md](AGENTS.md) for the
architecture.

## License

[Apache License 2.0](./LICENSE)
