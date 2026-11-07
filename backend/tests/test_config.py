from core.config import Settings


def test_cors_origins_accepts_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, http://127.0.0.1:5173")
    assert Settings().cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_cors_origins_accepts_json_list(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://a.test"]')
    assert Settings().cors_origins == ["http://a.test"]
