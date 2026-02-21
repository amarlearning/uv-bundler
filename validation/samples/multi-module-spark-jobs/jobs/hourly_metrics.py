from __future__ import annotations

from common.io import format_result
from pyspark.sql import SparkSession


def run() -> int:
    spark = SparkSession.builder.appName("hourly-metrics").getOrCreate()
    data = [("00:00", 100), ("01:00", 120), ("02:00", 80)]
    df = spark.createDataFrame(data, ["window", "count"])
    peak = df.orderBy(df["count"].desc()).limit(1).collect()[0]
    message = format_result("hourly_metrics", {"window": peak["window"], "count": peak["count"]})
    print(message)
    spark.stop()
    return 0
