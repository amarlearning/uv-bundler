# single-spark-job

A PySpark job whose own code and its dependency (`tabulate`) ship in one archive passed
to `spark-submit --py-files`. pyspark itself is **not** bundled: the cluster provides it,
so it sits in the `dev` dependency group (installed locally, never packaged).

```bash
uv-bundler --target spark-jar --arch x86_64   # → dist/single-spark-job-linux-x86_64.jar (~40 KB)

spark-submit --py-files dist/single-spark-job-linux-x86_64.jar driver.py
```

`driver.py` is a two-liner (`from app.main import run; run()`); see
[`../../spark_driver.py`](../../spark_driver.py). `app.main` maps a function over an RDD,
so the **executors** import both the job code and `tabulate` from the archive.

| Target                         | Format | Notes                                       |
|--------------------------------|--------|---------------------------------------------|
| `spark-jar` / `spark-zip`      | JAR/ZIP | Same flat layout; PySpark accepts both     |
| `spark-pex`                    | PEX    | For native deps (see PySpark's Python package management docs) |
| `spark-*-slim`                 | any    | Source only, when deps are already on the cluster |

Native extensions (`.so`) can't be imported from a `--py-files` archive (Python's
zipimport limitation). For those, ship a PEX instead.
