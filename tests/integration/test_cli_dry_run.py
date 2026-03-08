import textwrap
from pathlib import Path

from typer.testing import CliRunner

from uv_bundler.cli import app


def test_build_dry_run_with_minimal_project(tmp_path: Path, monkeypatch) -> None:
    # Create a minimal project structure with an entry point
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "main.py").write_text("def run():\n    return 'ok'\n")

    pyproject = textwrap.dedent(
        """
        [tool.uv-bundler]
        default_target = "spark-prod"

        [tool.uv-bundler.targets.spark-prod]
        format = "jar"
        entry_point = "app.main:run"
        platform = "linux"
        arch = "x86_64"
        python_version = "3.10"
        manylinux = "2014"
        """
    ).strip()
    (tmp_path / "pyproject.toml").write_text(pyproject)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    # Invoke the app as a single-command entry (Typer compatibility)
    result = runner.invoke(app, ["--dry-run"])
    # Debug output for easier failure diagnosis
    print(result.output)
    assert result.exit_code == 0
    assert "uv-bundler dry run" in result.stdout
    assert "format: jar" in result.stdout
    assert "entry_point: app.main:run" in result.stdout


def test_build_without_dry_run_builds_artifact(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "main.py").write_text("def run():\n    return 'ok'\n")

    pyproject = textwrap.dedent(
        """
        [project]
        name = "test-app"
        version = "0.1.0"
        dependencies = []

        [tool.uv-bundler]
        default_target = "spark-prod"

        [tool.uv-bundler.targets.spark-prod]
        format = "jar"
        entry_point = "app.main:run"
        platform = "linux"
        arch = "x86_64"
        python_version = "3.10"
        manylinux = "2014"
        """
    ).strip()
    (tmp_path / "pyproject.toml").write_text(pyproject)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    dist_dir = tmp_path / "dist"
    assert dist_dir.exists()
    assert any(p.name == "app-linux-x86_64.jar" for p in dist_dir.iterdir())
