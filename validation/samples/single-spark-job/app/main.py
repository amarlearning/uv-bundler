from __future__ import annotations

from pyspark.sql import SparkSession  # provided by the Spark runtime
from tabulate import tabulate  # bundled by uv-bundler


def _format(row: tuple[str, int]) -> str:
    # Runs on the executors: needs both this module and tabulate from --py-files.
    return str(tabulate([row], tablefmt="plain"))


def run() -> int:
    spark = SparkSession.builder.appName("single-spark-job").getOrCreate()
    try:
        rows = spark.sparkContext.parallelize([("spark", 1), ("uv-bundler", 2)], 2)
        formatted = rows.map(_format).collect()
    finally:
        spark.stop()
    print("spark job ok: " + " | ".join(" ".join(r.split()) for r in formatted))
    return 0
