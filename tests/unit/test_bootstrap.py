from uv_pack.services.bootstrap import render_bootstrap


def test_render_bootstrap_contains_entry_point() -> None:
    content = render_bootstrap("app.main:run")
    assert "importlib.import_module('app.main')" in content
    assert "getattr(mod, 'run')" in content
    assert "raise SystemExit(_run())" in content
