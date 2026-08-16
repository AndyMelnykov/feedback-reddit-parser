import pytest

import credentials


def test_get_secret_returns_stored_value(monkeypatch):
    monkeypatch.setattr(credentials.keyring, "get_password", lambda service, key: "secret-value")

    assert credentials.get_secret("reddit_client_id") == "secret-value"


def test_get_secret_raises_when_missing(monkeypatch):
    monkeypatch.setattr(credentials.keyring, "get_password", lambda service, key: None)

    with pytest.raises(credentials.MissingCredentialError):
        credentials.get_secret("reddit_client_id")


def test_get_secret_uses_service_name(monkeypatch):
    seen = {}

    def fake_get_password(service, key):
        seen["service"] = service
        seen["key"] = key
        return "value"

    monkeypatch.setattr(credentials.keyring, "get_password", fake_get_password)
    credentials.get_secret("anthropic_api_key")

    assert seen == {"service": credentials.SERVICE, "key": "anthropic_api_key"}
