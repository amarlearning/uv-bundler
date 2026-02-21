.PHONY: docker-base-linux
docker-base-linux:
	docker build $${DOCKER_PLATFORM:+--platform $${DOCKER_PLATFORM}} -f docker/Dockerfile.linux.base -t uv-pack:base-linux ..

.PHONY: build-example-linux
build-example-linux: docker-base-linux
	mkdir -p out
	docker build $${DOCKER_PLATFORM:+--platform $${DOCKER_PLATFORM}} -f docker/Dockerfile.linux.builder -t uv-pack:builder-linux ..
	docker run --rm -v $$(pwd)/out:/workspace/out uv-pack:builder-linux

.PHONY: test-artifacts-linux
test-artifacts-linux:
	: $${TARGET_OS:=linux}
	: $${TARGET_ARCH:=x86_64}
	docker run --rm -v $$(pwd)/..:/workspace -w /workspace python:3.12-slim bash -lc "python validation/validate_artifacts.py --out-dir validation/out/single-spark-job --target-os $${TARGET_OS} --target-arch $${TARGET_ARCH}"
