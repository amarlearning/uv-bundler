"""Unit tests for CLI helpers and the main build command.

All tests that invoke the build command mock out the two subprocess calls
(uv pip compile, uv pip install) so no network access or real uv binary is
needed — those paths are covered by integration tests.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from zipfile import ZipFile

import pytest
from typer.testing import CliRunner

import uv_bundler.cli as _cli
from uv_bundler.cli import _artifact_path, _is_excluded, _output_root, _stage_sources, app
from uv_bundler.domain.config import GlobalConfig, TargetConfig, UvPackConfig

# ── _is_excluded ──────────────────────────────────────────────────────────────


def test_is_excluded_matches_exact_pattern() -> None:
    assert _is_excluded("tests/foo.py", ["tests/*"]) is True


def test_is_excluded_matches_glob_wildcard() -> None:
    assert _is_excluded("app/__pycache__", ["**/__pycache__"]) is True


def test_is_excluded_no_match_returns_false() -> None:
    assert _is_excluded("app/main.py", ["tests/*", "*.pyc"]) is False


def test_is_excluded_empty_patterns() -> None:
    assert _is_excluded("anything", []) is False


def test_is_excluded_pyc_extension() -> None:
    assert _is_excluded("app/main.pyc", ["*.pyc"]) is True


# ── _output_root ──────────────────────────────────────────────────────────────


def test_output_root_uses_out_dir_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_dir = tmp_path / "env_out"
    monkeypatch.setenv("OUT_DIR", str(env_dir))
    pyproject = tmp_path / "pyproject.toml"
    cfg = UvPackConfig(global_config=GlobalConfig(output_base="./dist"))
    result = _output_root(pyproject, cfg)
    assert result == env_dir.resolve()


def test_output_root_out_dir_takes_precedence_over_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_dir = tmp_path / "from_env"
    monkeypatch.setenv("OUT_DIR", str(env_dir))
    pyproject = tmp_path / "pyproject.toml"
    cfg = UvPackConfig(global_config=GlobalConfig(output_base="./should_not_use"))
    assert _output_root(pyproject, cfg) == env_dir.resolve()


def test_output_root_uses_output_base_from_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OUT_DIR", raising=False)
    pyproject = tmp_path / "pyproject.toml"
    cfg = UvPackConfig(global_config=GlobalConfig(output_base="./artifacts"))
    result = _output_root(pyproject, cfg)
    assert result == (tmp_path / "artifacts").resolve()


def test_output_root_defaults_to_dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OUT_DIR", raising=False)
    pyproject = tmp_path / "pyproject.toml"
    cfg = UvPackConfig(global_config=GlobalConfig())
    result = _output_root(pyproject, cfg)
    assert result == (tmp_path / "dist").resolve()


# ── _artifact_path ────────────────────────────────────────────────────────────


def test_artifact_path_naming(tmp_path: Path) -> None:
    cfg = UvPackConfig(global_config=GlobalConfig(project_name="my-job"))
    tgt = TargetConfig(platform="linux", arch="x86_64")
    path = _artifact_path(tmp_path, cfg, tgt, ".jar")
    assert path == tmp_path / "my-job-linux-x86_64.jar"


def test_artifact_path_defaults_project_name_to_app(tmp_path: Path) -> None:
    cfg = UvPackConfig(global_config=GlobalConfig())  # no project_name
    tgt = TargetConfig(platform="linux", arch="aarch64")
    path = _artifact_path(tmp_path, cfg, tgt, ".pex")
    assert path == tmp_path / "app-linux-aarch64.pex"


def test_artifact_path_zip_suffix(tmp_path: Path) -> None:
    cfg = UvPackConfig(global_config=GlobalConfig(project_name="lambda-fn"))
    tgt = TargetConfig(platform="linux", arch="x86_64")
    path = _artifact_path(tmp_path, cfg, tgt, ".zip")
    assert path.name == "lambda-fn-linux-x86_64.zip"


# ── _stage_sources ────────────────────────────────────────────────────────────


def _make_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "app").mkdir()
    (project / "app" / "__init__.py").write_text("")
    (project / "app" / "main.py").write_text("def run():\n    return 0\n")
    (project / "pyproject.toml").write_text("[project]\nname='x'\n")
    (project / "README.md").write_text("# readme")
    (project / "uv.lock").write_text("")
    return project


def test_stage_sources_copies_python_packages(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    dest = tmp_path / "staging"
    dest.mkdir()
    _stage_sources(project, dest)
    assert (dest / "app" / "main.py").exists()
    assert (dest / "app" / "__init__.py").exists()


def test_stage_sources_excludes_pyproject_toml(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    dest = tmp_path / "staging"
    dest.mkdir()
    _stage_sources(project, dest)
    assert not (dest / "pyproject.toml").exists()


def test_stage_sources_excludes_readme(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    dest = tmp_path / "staging"
    dest.mkdir()
    _stage_sources(project, dest)
    assert not (dest / "README.md").exists()


def test_stage_sources_excludes_dotfiles(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    (project / ".env").write_text("SECRET=x")
    dest = tmp_path / "staging"
    dest.mkdir()
    _stage_sources(project, dest)
    assert not (dest / ".env").exists()


def test_stage_sources_excludes_skip_dirs(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    (project / "dist").mkdir()
    (project / "dist" / "app.jar").write_text("artifact")
    dest = tmp_path / "staging"
    dest.mkdir()
    _stage_sources(project, dest)
    assert not (dest / "dist").exists()


def test_stage_sources_excludes_pycache(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    pycache = project / "app" / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-310.pyc").write_bytes(b"bytecode")
    dest = tmp_path / "staging"
    dest.mkdir()
    _stage_sources(project, dest)
    assert not (dest / "app" / "__pycache__").exists()


def test_stage_sources_respects_user_exclude_patterns(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    (project / "tests").mkdir()
    (project / "tests" / "test_main.py").write_text("def test_x(): pass\n")
    dest = tmp_path / "staging"
    dest.mkdir()
    _stage_sources(project, dest, exclude=["tests/*"])
    assert not (dest / "tests").exists()


def test_stage_sources_excludes_uv_lock(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    dest = tmp_path / "staging"
    dest.mkdir()
    _stage_sources(project, dest)
    assert not (dest / "uv.lock").exists()


# ── CLI command: dry-run ──────────────────────────────────────────────────────


def _write_minimal_project(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "main.py").write_text("def run():\n    return 0\n")
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "test-app"
            version = "0.1.0"
            dependencies = []

            [tool.uv-bundler]
            project_name = "test-app"
            default_target = "spark-prod"

            [tool.uv-bundler.targets.spark-prod]
            format = "jar"
            entry_point = "app.main:run"
            platform = "linux"
            arch = "x86_64"
            python_version = "3.10"
            manylinux = "2014"

            [tool.uv-bundler.targets.airflow-pex]
            format = "pex"
            entry_point = "app.main:run"
            platform = "linux"
            arch = "x86_64"
            python_version = "3.10"
            manylinux = "2014"

            [tool.uv-bundler.targets.spark-zip]
            format = "zip"
            entry_point = "app.main:run"
            platform = "linux"
            arch = "x86_64"
            python_version = "3.10"
            manylinux = "2014"
            """
        ).strip()
    )


def test_dry_run_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run"])
    assert result.exit_code == 0
    assert "uv-bundler dry run" in result.stdout


def test_dry_run_shows_resolved_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run"])
    assert "format: jar" in result.stdout
    assert "entry_point: app.main:run" in result.stdout
    assert "platform: linux" in result.stdout
    assert "arch: x86_64" in result.stdout


def test_dry_run_arch_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run", "--arch", "aarch64"])
    assert result.exit_code == 0
    assert "aarch64" in result.stdout


def test_dry_run_target_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["--target", "spark-zip", "--dry-run"])
    assert result.exit_code == 0
    assert "format: zip" in result.stdout


# ── CLI command: full build (mocked subprocess) ───────────────────────────────


def _mock_uv_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch process_run in the CLI module so uv commands succeed without network access."""
    monkeypatch.setattr(_cli, "process_run", lambda *args, **kwargs: 0)


def test_cli_builds_jar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    _mock_uv_success(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    dist = tmp_path / "dist"
    assert dist.exists()
    jar_files = list(dist.glob("*.jar"))
    assert len(jar_files) == 1
    assert "test-app-linux-x86_64" in jar_files[0].name


def test_cli_builds_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    _mock_uv_success(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(app, ["--target", "spark-zip"])
    assert result.exit_code == 0
    zip_files = list((tmp_path / "dist").glob("*.zip"))
    assert len(zip_files) == 1


def test_cli_out_dir_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    _mock_uv_success(monkeypatch)
    out_dir = tmp_path / "custom_out"
    monkeypatch.setenv("OUT_DIR", str(out_dir))
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert any(out_dir.glob("*.jar"))


def test_cli_resolver_failure_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_cli, "process_run", lambda *args, **kwargs: 1)
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code != 0


def test_cli_missing_pyproject_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run"])
    assert result.exit_code != 0


def test_cli_jar_artifact_is_valid_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Built JAR must be openable as a ZIP and contain __main__.py."""
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    _mock_uv_success(monkeypatch)
    runner = CliRunner()
    runner.invoke(app, [])
    jar = next((tmp_path / "dist").glob("*.jar"))
    with ZipFile(jar) as zf:
        assert "__main__.py" in zf.namelist()
        assert "META-INF/MANIFEST.MF" in zf.namelist()


# ── _artifact_path: slim suffix ────────────────────────────────────────────────


def test_artifact_path_slim_adds_slim_suffix(tmp_path: Path) -> None:
    cfg = UvPackConfig(global_config=GlobalConfig(project_name="my-job"))
    tgt = TargetConfig(platform="linux", arch="x86_64")
    path = _artifact_path(tmp_path, cfg, tgt, ".jar", slim=True)
    assert path == tmp_path / "my-job-linux-x86_64-slim.jar"


def test_artifact_path_no_slim_no_suffix(tmp_path: Path) -> None:
    cfg = UvPackConfig(global_config=GlobalConfig(project_name="my-job"))
    tgt = TargetConfig(platform="linux", arch="x86_64")
    path = _artifact_path(tmp_path, cfg, tgt, ".jar", slim=False)
    assert path == tmp_path / "my-job-linux-x86_64.jar"


# ── CLI command: slim mode ─────────────────────────────────────────────────────


def test_dry_run_shows_slim_false_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run"])
    assert result.exit_code == 0
    assert "slim: False" in result.stdout


def test_dry_run_shows_slim_true_when_flag_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run", "--slim"])
    assert result.exit_code == 0
    assert "slim: True" in result.stdout


def test_cli_slim_flag_skips_resolve_and_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--slim must not invoke the resolver (uv pip compile/install)."""
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls: list[list[str]] = []

    def tracking_run(args: list[str], **kwargs: object) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(_cli, "process_run", tracking_run)
    runner = CliRunner()
    result = runner.invoke(app, ["--slim"])
    assert result.exit_code == 0
    # No uv calls should have happened
    assert all("uv" not in " ".join(a) for a in calls)


def test_cli_slim_builds_jar_with_slim_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    _mock_uv_success(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(app, ["--slim"])
    assert result.exit_code == 0
    dist = tmp_path / "dist"
    slim_jars = list(dist.glob("*-slim.jar"))
    assert len(slim_jars) == 1
    assert "test-app-linux-x86_64-slim" in slim_jars[0].name


def test_cli_slim_jar_has_no_site_packages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Slim JAR must not contain any site-packages/ entries."""
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    _mock_uv_success(monkeypatch)
    runner = CliRunner()
    runner.invoke(app, ["--slim"])
    jar = next((tmp_path / "dist").glob("*-slim.jar"))
    with ZipFile(jar) as zf:
        names = zf.namelist()
    assert not any(n.startswith("site-packages/") for n in names)
    assert "app/main.py" in names


def test_cli_slim_exclude_filters_source_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """slim_exclude patterns remove matching source files from the slim artifact."""
    _write_minimal_project(tmp_path)
    # Add a tests/ directory that slim_exclude should strip
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_x(): pass\n")
    # Rewrite pyproject with slim=true and slim_exclude targeting tests/
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "test-app"
            version = "0.1.0"
            dependencies = []

            [tool.uv-bundler]
            project_name = "test-app"
            default_target = "spark-prod"

            [tool.uv-bundler.targets.spark-prod]
            format = "jar"
            entry_point = "app.main:run"
            platform = "linux"
            arch = "x86_64"
            python_version = "3.10"
            manylinux = "2014"
            slim = true
            slim_exclude = ["tests/*"]
            """
        ).strip()
    )
    monkeypatch.chdir(tmp_path)
    _mock_uv_success(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    jar = next((tmp_path / "dist").glob("*-slim.jar"))
    with ZipFile(jar) as zf:
        names = zf.namelist()
    assert not any("tests/" in n for n in names)
    assert "app/main.py" in names


def test_cli_slim_flag_overrides_config_slim_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--slim CLI flag activates slim even when config has slim=false (default)."""
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    _mock_uv_success(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(app, ["--slim"])
    assert result.exit_code == 0
    dist = tmp_path / "dist"
    assert any(p.name.endswith("-slim.jar") for p in dist.iterdir())


def test_cli_pex_compiles_but_skips_uv_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pex resolves the lockfile itself, so `uv pip install` would be wasted work."""
    _write_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls: list[list[str]] = []

    def tracking_run(args: list[str], **kwargs: object) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(_cli, "process_run", tracking_run)
    result = CliRunner().invoke(app, ["--target", "airflow-pex"])
    assert result.exit_code == 0, result.stdout
    assert [c[:3] for c in calls if c[0] == "uv"] == [["uv", "pip", "compile"]]
    assert any(c[0] == "pex" for c in calls)
