from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(args: list[str], cwd: Path | None = None) -> int:
    print(f"Running: {' '.join(args)}", file=sys.stderr)
    try:
        proc = subprocess.run(args, cwd=str(cwd) if cwd else None, check=False)
        return int(proc.returncode)
    except FileNotFoundError:
        print(f"Error: '{args[0]}' not found on PATH", file=sys.stderr)
        return 127
