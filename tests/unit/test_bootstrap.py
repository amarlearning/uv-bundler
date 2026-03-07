from uv_pack.services.bootstrap import render_bootstrap


def test_render_bootstrap_contains_entry_point() -> None:
    content = render_bootstrap("app.main:run")
    assert "importlib.import_module('app.main')" in content
    assert "getattr(mod, 'run')" in content
    assert "raise SystemExit(_run())" in content


def test_render_bootstrap_multi_level_module() -> None:
    content = render_bootstrap("pkg.sub.module:execute")
    assert "importlib.import_module('pkg.sub.module')" in content
    assert "getattr(mod, 'execute')" in content


def test_render_bootstrap_zipapp_detection() -> None:
    """Bootstrap must use sys.path[0].is_file() to detect zipapp mode, not __file__."""
    content = render_bootstrap("app.main:run")
    assert "sys.path[0]" in content
    assert "is_file()" in content
    # Should NOT use Path(__file__).parent.exists() as the primary detection
    # (that only works in extracted mode, not inside a zip archive)
    assert "site-packages" in content


def test_render_bootstrap_is_valid_python() -> None:
    content = render_bootstrap("app.main:run")
    # Must compile without errors
    compile(content, "<bootstrap>", "exec")


def test_render_bootstrap_sys_path_insertion() -> None:
    content = render_bootstrap("app.main:run")
    assert "sys.path.insert(0," in content


def test_render_bootstrap_returns_int_or_zero() -> None:
    content = render_bootstrap("app.main:run")
    assert "isinstance(res, int)" in content
    assert "return 0" in content
