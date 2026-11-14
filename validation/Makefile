# Build the sample artifacts and run them the way their real runtimes do
# (spark-submit, a clean python container, the AWS Lambda runtime image).
# Needs uv, pex and a running Docker. Non-native TARGET_ARCH runs under emulation.
#
# Usage:
#   make test-artifacts                      # linux/x86_64
#   make test-artifacts TARGET_ARCH=aarch64

TARGET_ARCH ?= x86_64
OUT         := $(abspath out)
BUNDLER     ?= uv-bundler

.PHONY: build-artifacts
build-artifacts:
	mkdir -p $(OUT)
	cd samples/single-spark-job && OUT_DIR=$(OUT) $(BUNDLER) -t spark-jar --arch $(TARGET_ARCH)
	cd samples/single-spark-job && OUT_DIR=$(OUT) $(BUNDLER) -t spark-zip --arch $(TARGET_ARCH)
	cd samples/numpy-etl && OUT_DIR=$(OUT) $(BUNDLER) -t etl-$(TARGET_ARCH)
	cd samples/lambda-zip && OUT_DIR=$(OUT) $(BUNDLER) -t lambda-$(TARGET_ARCH)

.PHONY: test-artifacts
test-artifacts: build-artifacts
	./run_artifacts.sh all $(OUT) $(TARGET_ARCH)
