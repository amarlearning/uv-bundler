from importlib.metadata import PackageNotFoundError, version

__all__ = [
    "cli",
]

try:
    __version__ = version("uv-bundler")  # set from the git tag by setuptools-scm
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0+unknown"
