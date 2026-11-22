import pytest

import fetch


def test_fence_refuses_twelve_month_window():
    with pytest.raises(fetch.FenceError):
        fetch.check_fence(2025, 11)
    with pytest.raises(fetch.FenceError):
        fetch.check_fence(2026, 10)
    fetch.check_fence(2025, 10)


def test_range_crossing_fence_refused_before_any_request(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network touched")

    monkeypatch.setattr(fetch.urllib.request, "urlopen", boom)
    with pytest.raises(fetch.FenceError):
        fetch.fetch("damlbmp", "2025-09", "2025-12", tmp_path)
    assert not any(tmp_path.rglob("*.zip"))
