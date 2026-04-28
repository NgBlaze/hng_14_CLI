import json
import os
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".insighta" / "credentials.json"
API_URL = os.environ.get("INSIGHTA_API_URL", "https://hng-14-stage-1.vercel.app")
GITHUB_CLIENT_ID = os.environ.get("INSIGHTA_GITHUB_CLIENT_ID", "Iv23li63ND82ZMFCbcb8")


def save_credentials(access_token: str, refresh_token: str, user: dict) -> None:
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_text(json.dumps({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
        "avatar_url": user.get("avatar_url"),
    }, indent=2))
    CREDENTIALS_PATH.chmod(0o600)


def load_credentials() -> dict | None:
    if not CREDENTIALS_PATH.exists():
        return None
    try:
        return json.loads(CREDENTIALS_PATH.read_text())
    except Exception:
        return None


def clear_credentials() -> None:
    if CREDENTIALS_PATH.exists():
        CREDENTIALS_PATH.unlink()
