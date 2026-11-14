from __future__ import annotations

import argparse
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

# Slim artifacts: same source files, no site-packages/
EXPECTED_SLIM_JAR_PATHS = {
    "META-INF/MANIFEST.MF",
    "__main__.py",
    "app/main.py",
    "app/__init__.py",
}

EXPECTED_SLIM_ZIP_PATHS = {
    "__main__.py",
    "app/main.py",
    "app/__init__.py",
}


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


def validate_slim_contents(base: Path, target_os: str, target_arch: str) -> list[str]:
    """Validate slim artifacts: must contain sources but no installed dependencies."""
    errors: list[str] = []
    stem = f"single-spark-job-{target_os}-{target_arch}-slim"
    jar = base / f"{stem}.jar"
    zip_app = base / f"{stem}.zip"
    pex = base / f"{stem}.pex"

    if not jar.exists():
        errors.append(f"slim contents: missing slim JAR {jar}")
    else:
        members = load_members(jar)
        errors.extend(require_paths(members, EXPECTED_SLIM_JAR_PATHS, "slim-jar"))
        if any(".dist-info/" in m for m in members):
            errors.append("slim-jar: must not contain installed dependencies (slim mode)")

    if not zip_app.exists():
        errors.append(f"slim contents: missing slim ZIP {zip_app}")
    else:
        members = load_members(zip_app)
        errors.extend(require_paths(members, EXPECTED_SLIM_ZIP_PATHS, "slim-zip"))
        if any(".dist-info/" in m for m in members):
            errors.append("slim-zip: must not contain installed dependencies (slim mode)")

    if not pex.exists():
        errors.append(f"slim contents: missing slim PEX {pex}")

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
    parser.add_argument(
        "--skip-slim",
        action="store_true",
        default=False,
        help="Skip slim artifact validation",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(argv or sys.argv[1:])
    base = ns.out_dir
    target_os = ns.target_os
    target_arch = ns.target_arch

    errors: list[str] = []
    errors.extend(validate_contents(base, target_os, target_arch))

    if not ns.skip_slim:
        errors.extend(validate_slim_contents(base, target_os, target_arch))

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
