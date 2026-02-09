# Technical Specification: uv-pack (v1.0)

## 1. Project Objective

uv-pack is a specialized build-orchestration tool designed to produce platform-agnostic, deployment-ready Python artifacts (JAR, PEX, ZIP) from any host OS. It leverages uv for high-speed, cross-platform dependency resolution and provides a "Standardized Build" contract for Data Engineering pipelines.

## 2. Configuration Schema (pyproject.toml)

The tool uses a hierarchical configuration. Global settings provide fallbacks, while target-specific settings allow for platform overrides.


```TOML
[tool.uv-pack]
# --- Global Defaults ---
project_name = "analytics-engine"
default_target = "spark-prod"
output_base = "./dist"          # Global output directory

[tool.uv-pack.targets.spark-prod]
# --- Core Settings ---
format = "jar"                  # Options: "jar", "pex", "zip"
entry_point = "app.main:run"    # Callable string: module.submodule:function

# --- Resolution Settings (Cross-Platform) ---
platform = "linux"              # Options: "linux", "macos", "windows"
arch = "x86_64"                 # Options: "x86_64", "aarch64" (ARM)
python_version = "3.10"         # Specific Python version for the target
manylinux = "2014"              # glibc version (Options: "2010", "2014", "31")

# --- Packaging Strategy ---
bundle = "fat"                  # "fat" (deps included), "slim" (source only)
include_binaries = true         # Whether to include compiled .so files
compression = "deflated"        # Options: "stored", "deflated"

# --- Advanced Options ---
# Paths to exclude from the final artifact (Glob patterns)
exclude = ["tests/*", "**/__pycache__", "*.pyc", ".git*"]
# Additional files to inject (e.g., config files outside the source tree)
extra_files = { "config/prod.yaml" = "resources/config.yaml" }
```

## 3. The Execution Lifecycle (Step-by-Step)

### Step 1: Context Hydration

The engine reads pyproject.toml and merges it with CLI overrides.

* Validation: It checks if the entry_point module exists in the local source tree.
* Platform Mapping: Translates linux + x86_64 into the PEP 508 platform string: x86_64-unknown-linux-gnu.

### Step 2: The "Ghost" Resolution

uv-pack invokes uv to resolve dependencies for the Target Environment without installing them locally.

* The Command:
  ```bash
  uv pip compile pyproject.toml \
  --python-platform <target_platform_string> \
  --python-version <config_python_version> \
  --output-file .uv-pack/resolved.lock
  ```

* Why: This ensures the lockfile contains the specific hashes for "manylinux" wheels, even if the build is running on a MacBook.

### Step 3: Staging & Wheel Extraction

The engine creates a temporary staging/ directory.

1. Download: Downloads all wheels identified in the resolved.lock using uv pip download.
2. Unpack: Every .whl is unzipped into staging/site-packages/.
3. Source Injection: The local project source code is copied into the root of staging/.

### Step 4: The Bootstrap Generation

For JAR and ZIP formats, a bootstrap script is required to handle the runtime environment within the compressed artifact. uv-pack generates a __main__.py:

```python
import sys, os, importlib

# 1. Path Injection: Add the internal site-packages to the head of sys.path
base_dir = os.path.dirname(__file__)
site_packages = os.path.join(base_dir, "site-packages")
sys.path.insert(0, site_packages)

# 2. Entry Point Execution: Dynamically load the user's function
# Translates "app.main:run" -> from app.main import run; run()
module_str, func_str = "app.main", "run" 
module = importlib.import_module(module_str)
func = getattr(module, func_str)

if __name__ == "__main__":
    func()
```


### Step 5: Final Assembly (Target Specifics)

Depending on the format flag, the engine performs the final wrap:

* JAR: Adds META-INF/MANIFEST.MF. Validates that no .dylib or .dll files are present (checks for .so only).
* PEX: Directs the pex library to build an executable using the staging/ directory as the source.
* ZIP: Re-organizes the staging/ structure if needed (e.g., for AWS Lambda Layers, it moves site-packages to python/).

## 4. Key Decisions & Decision Log

| Decision Point | Selection | Technical Justification |
| :---- | :---- | :---- |
| Glibc Compatibility | Default to manylinux2014 | Matches the older Linux kernels found in Enterprise Spark (EMR 6.x) and Databricks. |
| Dependency Location | /site-packages subdir | Keeps the root of the JAR clean and prevents local source modules from being accidentally overwritten by dependency files. |
| Resolution Tool | uv Subprocess | Provides the best performance. If uv is missing, the tool fails early with a clear installation guide. |
| Cross-Arch Logic | Ghost Resolve | Eliminates the need for Docker. By resolving for the target tags, we can build ARM64 artifacts on Intel machines. |

## 5. Artifact Directory Structure (Inside the JAR)

```shell
artifact.jar
├── __main__.py               # Generated bootstrap
├── app/                      # User source code
│   └── main.py
├── site-packages/            # Unzipped wheels
│   ├── pandas/
│   ├── numpy/
│   └── ...
└── META-INF/
    └── MANIFEST.MF           # JVM Metadata
```

## 6. Implementation Roadmap

1. Module config_loader: Handles TOML parsing and hierarchy merging.
2. Module resolver: Interfaces with uv to generate the platform-specific lockfile.
3. Module packager: Base class with specialized JarPackager, PexPackager, and ZipPackager implementations.
4. CLI Entrypoint: Built with click or typer to provide a clean user interface.
