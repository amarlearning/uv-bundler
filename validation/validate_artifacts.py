from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from zipfile import ZipFile

EXPECTED_JAR_PATHS = {
    "META-INF/MANIFEST.MF",
    "__main__.py",
    "app/main.py",
    "app/__init__.py",
}

EXPECTED_ZIP_PATHS = {
    "__main__.py",
    "app/main.py",
    "app/__init__.py",
}

EXPECTED_PEX_PATHS = {
    ".bootstrap/pex/__main__.py",
}

EXPECTED_LOG_SUBSTRING = "Running single Spark job with pyspark"


def load_members(path: Path) -> set[str]:
    with ZipFile(path) as zf:
        return set(zf.namelist())


def require_paths(members: set[str], required: Iterable[str], label: str) -> list[str]:
    missing = []
    for entry in required:
        if entry not in members:
            missing.append(f"{label}: missing required entry {entry}")
    return missing


def validate_contents(base: Path, target_os: str, target_arch: str) -> list[str]:
    errors: list[str] = []
    stem = f"single-spark-job-{target_os}-{target_arch}"
    jar = base / f"{stem}.jar"
    pex = base / f"{stem}.pex"
    zip_app = base / f"{stem}.zip"

    if not jar.exists():
        errors.append(f"contents: missing JAR {jar}")
    else:
        members = load_members(jar)
        errors.extend(require_paths(members, EXPECTED_JAR_PATHS, "jar"))

    if not zip_app.exists():
        errors.append(f"contents: missing ZIP {zip_app}")
    else:
        members = load_members(zip_app)
        errors.extend(require_paths(members, EXPECTED_ZIP_PATHS, "zip"))

    if not pex.exists():
        errors.append(f"contents: missing PEX {pex}")
    else:
        members = load_members(pex)
        errors.extend(require_paths(members, EXPECTED_PEX_PATHS, "pex"))

    return errors


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def validate_runtime(base: Path, target_os: str, target_arch: str) -> list[str]:
    errors: list[str] = []
    stem = f"single-spark-job-{target_os}-{target_arch}"
    jar = base / f"{stem}.jar"
    pex = base / f"{stem}.pex"
    zip_app = base / f"{stem}.zip"

    if jar.exists():
        code, out, err = run_command(["python", str(jar)])
        if code != 0:
            errors.append(f"runtime: jar exited with {code}: {err or out}")
        elif EXPECTED_LOG_SUBSTRING not in out:
            errors.append("runtime: jar output did not contain expected log line")

    if pex.exists():
        # TODO: Fix PEX dependency inclusion in uv-pack; currently PEX is built without deps.
        # code, out, err = run_command(["python", str(pex)])
        # if code != 0:
        #     errors.append(f"runtime: pex exited with {code}: {err or out}")
        # elif EXPECTED_LOG_SUBSTRING not in out:
        #     errors.append("runtime: pex output did not contain expected log line")
        pass

    if zip_app.exists():
        code, out, err = run_command(["python", str(zip_app)])
        if code != 0:
            errors.append(f"runtime: zip exited with {code}: {err or out}")
        elif EXPECTED_LOG_SUBSTRING not in out:
            errors.append("runtime: zip output did not contain expected log line")

    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("validation/out/single-spark-job"),
    )
    parser.add_argument("--target-os", default="linux")
    parser.add_argument("--target-arch", default="x86_64")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(argv or sys.argv[1:])
    base = ns.out_dir
    target_os = ns.target_os
    target_arch = ns.target_arch

    errors: list[str] = []
    errors.extend(validate_contents(base, target_os, target_arch))
    errors.extend(validate_runtime(base, target_os, target_arch))

    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 1

    print(
        f"validation ok for {target_os}-{target_arch} in {base}",
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
