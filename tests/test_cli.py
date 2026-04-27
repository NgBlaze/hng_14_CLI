import base64
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from insighta.cli import cli
from insighta.config import save_credentials


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fake_creds(tmp_path, monkeypatch):
    """Patch CREDENTIALS_PATH to a temp file and write fake creds."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({
        "access_token": "fake-access",
        "refresh_token": "fake-refresh",
        "username": "testuser",
        "email": "test@example.com",
        "role": "analyst",
        "avatar_url": "",
    }))
    monkeypatch.setattr("insighta.config.CREDENTIALS_PATH", creds_file)
    monkeypatch.setattr("insighta.cli.CREDENTIALS_PATH", creds_file)
    monkeypatch.setattr("insighta.client.__builtins__", __builtins__)
    return creds_file


# ─── PKCE unit tests ──────────────────────────────────────────────────────────

def test_pkce_challenge_derivation():
    """code_challenge must be base64url(SHA256(code_verifier))."""
    from insighta.cli import _generate_pkce
    verifier, challenge = _generate_pkce()
    digest = hashlib.sha256(verifier.encode()).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert challenge == expected


def test_pkce_verifier_is_url_safe():
    from insighta.cli import _generate_pkce
    verifier, _ = _generate_pkce()
    safe_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert all(c in safe_chars for c in verifier)


# ─── Auth command tests ───────────────────────────────────────────────────────

def test_whoami_not_logged_in(runner, tmp_path, monkeypatch):
    monkeypatch.setattr("insighta.config.CREDENTIALS_PATH", tmp_path / "none.json")
    monkeypatch.setattr("insighta.cli.CREDENTIALS_PATH", tmp_path / "none.json")
    result = runner.invoke(cli, ["whoami"])
    assert result.exit_code != 0 or "Not logged in" in result.output


def test_logout_not_logged_in(runner, tmp_path, monkeypatch):
    monkeypatch.setattr("insighta.config.CREDENTIALS_PATH", tmp_path / "none.json")
    result = runner.invoke(cli, ["logout"])
    assert "Not logged in" in result.output
    assert result.exit_code == 0


# ─── Profile command tests ────────────────────────────────────────────────────

def test_profiles_list_requires_auth(runner, tmp_path, monkeypatch):
    monkeypatch.setattr("insighta.config.CREDENTIALS_PATH", tmp_path / "none.json")
    result = runner.invoke(cli, ["profiles", "list"])
    assert "Not logged in" in result.output or result.exit_code != 0


def test_profiles_search_requires_auth(runner, tmp_path, monkeypatch):
    monkeypatch.setattr("insighta.config.CREDENTIALS_PATH", tmp_path / "none.json")
    result = runner.invoke(cli, ["profiles", "search", "young males"])
    assert result.exit_code != 0 or "Not logged in" in result.output
