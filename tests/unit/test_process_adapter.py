from types import SimpleNamespace

from uv_pack.adapters import process


def test_run_invokes_subprocess(tmp_path, monkeypatch) -> None:
    called = {}

    def fake_run(args, cwd=None, check=False):
        called["args"] = args
        called["cwd"] = cwd
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(process.subprocess, "run", fake_run)
    d = tmp_path
    code = process.run(["echo", "x"], cwd=d)
    assert code == 0
    assert called["args"] == ["echo", "x"]
    assert called["cwd"] == str(d)


def test_run_missing_executable_returns_127(monkeypatch) -> None:
    expected = 127

    def fake_run(args, cwd=None, check=False):
        raise FileNotFoundError

    monkeypatch.setattr(process.subprocess, "run", fake_run)
    code = process.run(["not-a-real-exe"])
    assert code == expected
