"""spark-submit driver for the single-spark-job sample.

Kept outside the sample directory so the job's code can only come from the
artifact passed via --py-files, never from the driver's own folder.
"""

from app.main import run

raise SystemExit(run())
