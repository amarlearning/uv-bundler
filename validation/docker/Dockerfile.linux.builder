FROM uv-pack:base-linux

WORKDIR /workspace

COPY validation/samples/single-spark-job /workspace/validation/samples/single-spark-job

WORKDIR /workspace/validation/samples/single-spark-job

RUN uv pip install . --system && mkdir -p /workspace/out/single-spark-job

ENV OUT_DIR=/workspace/out/single-spark-job

ENTRYPOINT ["uv-pack"]
