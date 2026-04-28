import base64
import hashlib
import queue
import secrets
import socket
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import click
import httpx
from rich.console import Console
from rich.status import Status

from insighta import client, display
from insighta.commands.profiles import profiles
from insighta.config import (
    API_URL, CREDENTIALS_PATH, GITHUB_CLIENT_ID,
    clear_credentials, load_credentials, save_credentials,
)

console = Console()


# ─── PKCE helpers ─────────────────────────────────────────────────────────────

def _generate_pkce() -> tuple[str, str]:
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run_callback_server(port: int, result: queue.Queue) -> HTTPServer:
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:sans-serif;text-align:center;margin-top:80px'>"
                b"<h2>Login successful &#10003;</h2>"
                b"<p>You can close this window and return to your terminal.</p>"
                b"</body></html>"
            )
            result.put({
                "code": (params.get("code") or [None])[0],
                "state": (params.get("state") or [None])[0],
                "error": (params.get("error") or [None])[0],
            })

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    return server


# ─── CLI root ─────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Insighta Labs+ — profile intelligence platform."""


# ─── insighta login ───────────────────────────────────────────────────────────

@cli.command()
def login():
    """Log in via GitHub OAuth (PKCE)."""
    creds = load_credentials()
    if creds:
        console.print(f"Already logged in as [bold cyan]@{creds['username']}[/bold cyan]. "
                      "Run [dim]insighta logout[/dim] first to switch accounts.")
        return

    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(16)
    port = _free_port()
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    result: queue.Queue = queue.Queue()
    _run_callback_server(port, result)

    # GitHub App: scope is derived from App permissions, not URL param.
    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )

    console.print("\nOpening GitHub in your browser...")
    console.print(f"[dim]If nothing opens, visit:[/dim]\n{github_url}\n")
    webbrowser.open(github_url)

    with Status("Waiting for GitHub authentication...", console=console):
        try:
            callback = result.get(timeout=120)
        except queue.Empty:
            display.error("Login timed out after 2 minutes. Try again.")
            sys.exit(1)

    if callback.get("error"):
        display.error(f"GitHub OAuth error: {callback['error']}")
        sys.exit(1)

    if callback.get("state") != state:
        display.error("State mismatch — possible CSRF. Aborting.")
        sys.exit(1)

    code = callback.get("code")
    if not code:
        display.error("No authorization code received.")
        sys.exit(1)

    with Status("Completing login...", console=console):
        try:
            resp = httpx.post(
                f"{API_URL}/auth/github/exchange",
                json={
                    "code": code,
                    "code_verifier": code_verifier,
                    "code_challenge": code_challenge,
                    "redirect_uri": redirect_uri,
                },
                timeout=20.0,
            )
        except httpx.ConnectError:
            display.error(f"Cannot reach {API_URL}. Check your connection.")
            sys.exit(1)

    if resp.status_code != 200:
        msg = resp.json().get("message", resp.text)
        display.error(f"Authentication failed: {msg}")
        sys.exit(1)

    data = resp.json()
    save_credentials(data["access_token"], data["refresh_token"], data["user"])

    console.print(
        f"\n[bold green]Logged in as[/bold green] [bold cyan]@{data['user']['username']}[/bold cyan] "
        f"[dim]({data['user']['role']})[/dim]\n"
        f"[dim]Credentials saved to {CREDENTIALS_PATH}[/dim]"
    )


# ─── insighta logout ──────────────────────────────────────────────────────────

@cli.command()
def logout():
    """Log out and revoke your session."""
    creds = load_credentials()
    if not creds:
        console.print("Not logged in.")
        return

    try:
        httpx.post(
            f"{API_URL}/auth/logout",
            json={"refresh_token": creds.get("refresh_token")},
            timeout=10.0,
        )
    except Exception:
        pass

    clear_credentials()
    display.success(f"Logged out @{creds.get('username', 'user')}")


# ─── insighta whoami ──────────────────────────────────────────────────────────

@cli.command()
def whoami():
    """Show the currently logged-in user."""
    creds = load_credentials()
    if not creds:
        display.error("Not logged in. Run 'insighta login' first.")
        sys.exit(1)

    resp = client.request("GET", "/auth/whoami")
    if resp.status_code != 200:
        display.error(resp.json().get("message", "Failed to fetch user info."))
        sys.exit(1)

    display.whoami_table(resp.json()["data"])


# ─── Register subgroups ───────────────────────────────────────────────────────

cli.add_command(profiles)
