#!/usr/bin/env bash
# Run uv-bundler sample artifacts the way their real runtimes do.
#
#   spark   spark-submit --py-files <jar|zip> in the official Spark 4 image (pyspark NOT bundled)
#   numpy   python <pex> in a clean python:3.10-slim container
#   lambda  invoke the handler through AWS's Lambda runtime image (unzipped to /var/task)
#
# Usage: run_artifacts.sh <spark|numpy|lambda|all> <artifact-dir> <x86_64|aarch64>
set -euo pipefail

check=${1:?check}
dir=$(cd "${2:?artifact dir}" && pwd)
arch=${3:?arch}
here=$(cd "$(dirname "$0")" && pwd)
case "$arch" in
  x86_64) platform=linux/amd64 ;;
  aarch64) platform=linux/arm64 ;;
  *) echo "unknown arch: $arch" >&2; exit 2 ;;
esac

spark() {
  # Official Spark image: JVM + Python 3.10 + Spark, nothing from our artifact preinstalled.
  docker run --rm --platform "$platform" -e STEM="single-spark-job-linux-$arch" \
    -v "$dir:/artifacts:ro" -v "$here:/validation:ro" --entrypoint bash \
    spark:4.0.1-python3 -euc '
      for f in "/artifacts/$STEM.jar" "/artifacts/$STEM.zip"; do
        echo "==> spark-submit --py-files $f"
        /opt/spark/bin/spark-submit --master "local[2]" --py-files "$f" \
          /validation/spark_driver.py | tee /dev/stderr | grep -q "spark job ok"
      done'
}

numpy() {
  docker run --rm --platform "$platform" -v "$dir:/artifacts:ro" python:3.10-slim \
    python "/artifacts/numpy-etl-linux-$arch.pex" | tee /dev/stderr | grep -q "ETL complete"
}

lambda() {
  local task cid resp=""
  task=$(mktemp -d)
  unzip -q "$dir/lambda-zip-linux-$arch.zip" -d "$task"  # what Lambda does on deploy
  chmod -R a+rX "$task"
  cid=$(docker run -d --platform "$platform" -p 9000:8080 -v "$task:/var/task:ro" \
    public.ecr.aws/lambda/python:3.12 lambda_jobs.handler.handler)
  for _ in $(seq 1 30); do
    resp=$(curl -sf -XPOST http://localhost:9000/2015-03-31/functions/function/invocations \
      -d '{"message": "hello", "request_id": "ci-123"}') && break
    sleep 1
  done
  echo "$resp"
  if ! grep -Eq '"statusCode": ?200' <<<"$resp" || ! grep -q 'ci-123' <<<"$resp"; then
    docker logs "$cid" >&2
    docker rm -f "$cid" >/dev/null
    return 1
  fi
  docker rm -f "$cid" >/dev/null
}

case "$check" in
  spark | numpy | lambda) "$check" ;;
  all) spark && numpy && lambda ;;
  *) echo "unknown check: $check" >&2; exit 2 ;;
esac
echo "==> $check ok (linux/$arch)"
