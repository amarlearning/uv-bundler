# lambda-zip

An AWS Lambda deployment package for x86_64 and Graviton (aarch64), built on any host.

The handler depends on `orjson`, which is **not** part of the Lambda runtime and contains
native code. A successful invocation therefore shows that the ZIP carries the right Linux
wheel at the path Lambda imports from (the archive root).

```bash
uv-bundler --target lambda-aarch64   # → dist/lambda-zip-linux-aarch64.zip

aws lambda update-function-code --function-name my-fn \
  --zip-file fileb://dist/lambda-zip-linux-aarch64.zip
# handler: lambda_jobs.handler.handler   runtime: python3.12   arch: arm64
```

Test it locally against AWS's runtime image:

```bash
../../run_artifacts.sh lambda dist aarch64
```

| Target           | Platform      |
|------------------|---------------|
| `lambda-x86_64`  | linux/x86_64  |
| `lambda-aarch64` | linux/aarch64 |

`entry_point = "lambda_jobs.main:run"` only drives the `__main__.py` smoke entry; Lambda
itself calls the handler directly.
