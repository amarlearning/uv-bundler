from __future__ import annotations

from common.io import format_result
from pyspark.sql import SparkSession


def run() -> int:
    spark = SparkSession.builder.appName("daily-sales").getOrCreate()
    data = [(1, "widget", 10.0), (2, "gadget", 20.0)]
    df = spark.createDataFrame(data, ["id", "sku", "amount"])
    total = df.groupBy().sum("amount").collect()[0][0]
    message = format_result("daily_sales", {"total_amount": total})
    print(message)
    spark.stop()
    return 0
