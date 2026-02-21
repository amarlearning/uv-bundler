from __future__ import annotations

import pyspark


def run() -> int:
    version = getattr(pyspark, "__version__", "unknown")
    print(f"Running single Spark job with pyspark {version}")
    return 0
