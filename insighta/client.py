import sys

import click
import httpx

from insighta.config import API_URL, clear_credentials, load_credentials, save_credentials

_HEADERS_BASE = {"X-API-Version": "1"}


def _auth_headers(token: str) -> dict:
    return {**_HEADERS_BASE, "Authorization": f"Bearer {token}"}


def _try_refresh(creds: dict) -> str | None:
    """Exchange the refresh token for a new pair. Returns new access token or None."""
    refresh_token = creds.get("refresh_token")
    if not refresh_token:
        return None
    try:
        resp = httpx.post(
            f"{API_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            save_credentials(
                data["access_token"],
                data["refresh_token"],
                {k: creds.get(k) for k in ("username", "email", "role", "avatar_url")},
            )
            return data["access_token"]
    except Exception:
        pass
    return None


def request(method: str, path: str, **kwargs) -> httpx.Response:
    """Authenticated request with automatic token refresh."""
    creds = load_credentials()
    if not creds:
        click.echo("Not logged in. Run 'insighta login' first.", err=True)
        sys.exit(1)

    try:
        resp = httpx.request(
            method,
            f"{API_URL}{path}",
            headers=_auth_headers(creds["access_token"]),
            timeout=20.0,
            **kwargs,
        )
    except httpx.ConnectError:
        click.echo(f"Cannot reach {API_URL}. Check your connection.", err=True)
        sys.exit(1)
    except httpx.TimeoutException:
        click.echo("Request timed out. Try again.", err=True)
        sys.exit(1)

    if resp.status_code == 401:
        new_token = _try_refresh(creds)
        if new_token:
            try:
                resp = httpx.request(
                    method,
                    f"{API_URL}{path}",
                    headers=_auth_headers(new_token),
                    timeout=20.0,
                    **kwargs,
                )
            except Exception:
                pass
        if resp.status_code == 401:
            clear_credentials()
            click.echo("Session expired. Please run 'insighta login' again.", err=True)
            sys.exit(1)

    return resp
