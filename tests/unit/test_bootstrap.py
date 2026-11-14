from uv_bundler.services.bootstrap import render_bootstrap


def test_render_bootstrap_contains_entry_point() -> None:
    content = render_bootstrap("app.main:run")
    assert "importlib.import_module('app.main')" in content
    assert "getattr(mod, 'run')" in content
    assert "raise SystemExit(_run())" in content


def test_render_bootstrap_multi_level_module() -> None:
    content = render_bootstrap("pkg.sub.module:execute")
    assert "importlib.import_module('pkg.sub.module')" in content
    assert "getattr(mod, 'execute')" in content


def test_render_bootstrap_is_valid_python() -> None:
    content = render_bootstrap("app.main:run")
    # Must compile without errors
    compile(content, "<bootstrap>", "exec")


def test_render_bootstrap_returns_int_or_zero() -> None:
    content = render_bootstrap("app.main:run")
    assert "isinstance(res, int)" in content
    assert "return 0" in content
