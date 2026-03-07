# Validate artifacts built by uv-pack by running them inside a Docker container.
# Set TARGET_ARCH=aarch64 to validate ARM artifacts (requires aarch64 host or emulation).
#
# Usage:
#   make test-artifacts TARGET_ARCH=x86_64   (default)
#   make test-artifacts TARGET_ARCH=aarch64

TARGET_OS   ?= linux
TARGET_ARCH ?= x86_64
IMAGE       := python:3.10-slim

SPARK_STEM  := single-spark-job-$(TARGET_OS)-$(TARGET_ARCH)
ETL_STEM    := numpy-etl-$(TARGET_OS)-$(TARGET_ARCH)
LAMBDA_STEM := lambda-zip-$(TARGET_OS)-$(TARGET_ARCH)

.PHONY: test-artifacts
test-artifacts:
	@echo "==> Validating single-spark-job (JAR/ZIP/PEX)"
	docker run --rm -v "$$(pwd)/out/single-spark-job:/artifacts" "$(IMAGE)" \
	  sh -c "python /artifacts/$(SPARK_STEM).jar | grep -q 'Running single Spark job with pyspark'"
	docker run --rm -v "$$(pwd)/out/single-spark-job:/artifacts" "$(IMAGE)" \
	  sh -c "python /artifacts/$(SPARK_STEM).zip | grep -q 'Running single Spark job with pyspark'"
	docker run --rm -v "$$(pwd)/out/single-spark-job:/artifacts" "$(IMAGE)" \
	  sh -c "python /artifacts/$(SPARK_STEM).pex | grep -q 'Running single Spark job with pyspark'"
	@echo "==> Validating numpy-etl (PEX)"
	docker run --rm -v "$$(pwd)/out/numpy-etl:/artifacts" "$(IMAGE)" \
	  sh -c "python /artifacts/$(ETL_STEM).pex | grep -q 'ETL complete'"
	@echo "==> Validating lambda-zip (ZIP)"
	docker run --rm -v "$$(pwd)/out/lambda-zip:/artifacts" "$(IMAGE)" \
	  sh -c "python /artifacts/$(LAMBDA_STEM).zip | grep -q 'lambda ok'"
	@echo "==> All samples validated ok for $(TARGET_OS)/$(TARGET_ARCH)"
