import sys
from pathlib import Path

import click
from rich.console import Console
from rich.status import Status

from insighta import client, display

console = Console()


@click.group()
def profiles():
    """Manage profiles."""


# ─── insighta profiles list ───────────────────────────────────────────────────

@profiles.command("list")
@click.option("--gender", type=click.Choice(["male", "female"]), default=None)
@click.option("--age-group", type=click.Choice(["child", "teenager", "adult", "senior"]), default=None)
@click.option("--country", default=None, metavar="CODE", help="Country code e.g. NG")
@click.option("--min-age", type=int, default=None)
@click.option("--max-age", type=int, default=None)
@click.option("--sort-by", type=click.Choice(["age", "created_at", "gender_probability"]), default=None)
@click.option("--order", type=click.Choice(["asc", "desc"]), default="asc")
@click.option("--page", type=int, default=1, show_default=True)
@click.option("--limit", type=int, default=10, show_default=True)
def list_profiles(gender, age_group, country, min_age, max_age, sort_by, order, page, limit):
    """List profiles with optional filters."""
    params: dict = {"page": page, "limit": limit}
    if gender:
        params["gender"] = gender
    if age_group:
        params["age_group"] = age_group
    if country:
        params["country_id"] = country.upper()
    if min_age is not None:
        params["min_age"] = min_age
    if max_age is not None:
        params["max_age"] = max_age
    if sort_by:
        params["sort_by"] = sort_by
    if order != "asc":
        params["order"] = order

    with Status("Fetching profiles...", console=console):
        resp = client.request("GET", "/api/profiles", params=params)

    if resp.status_code != 200:
        display.error(resp.json().get("message", "Failed to fetch profiles."))
        sys.exit(1)

    body = resp.json()
    display.profiles_table(body["data"])
    display.pagination_info(body["page"], body["limit"], body["total"], body.get("total_pages", 1))


# ─── insighta profiles get ────────────────────────────────────────────────────

@profiles.command("get")
@click.argument("profile_id")
def get_profile(profile_id):
    """Get a single profile by ID."""
    with Status("Fetching profile...", console=console):
        resp = client.request("GET", f"/api/profiles/{profile_id}")

    if resp.status_code == 404:
        display.error("Profile not found.")
        sys.exit(1)
    if resp.status_code != 200:
        display.error(resp.json().get("message", "Failed to fetch profile."))
        sys.exit(1)

    display.profile_detail(resp.json()["data"])


# ─── insighta profiles search ─────────────────────────────────────────────────

@profiles.command("search")
@click.argument("query")
@click.option("--page", type=int, default=1, show_default=True)
@click.option("--limit", type=int, default=10, show_default=True)
def search_profiles(query, page, limit):
    """Search profiles using natural language."""
    with Status("Searching...", console=console):
        resp = client.request("GET", "/api/profiles/search", params={"q": query, "page": page, "limit": limit})

    if resp.status_code != 200:
        display.error(resp.json().get("message", "Search failed."))
        sys.exit(1)

    body = resp.json()
    display.profiles_table(body["data"])
    display.pagination_info(body["page"], body["limit"], body["total"], body.get("total_pages", 1))


# ─── insighta profiles create ─────────────────────────────────────────────────

@profiles.command("create")
@click.option("--name", required=True, help="Person's name to enrich")
def create_profile(name):
    """Create a new profile (admin only)."""
    with Status(f"Creating profile for [bold]{name}[/bold]...", console=console):
        resp = client.request("POST", "/api/profiles", json={"name": name})

    if resp.status_code == 403:
        display.error("Admin access required to create profiles.")
        sys.exit(1)
    if resp.status_code not in (200, 201):
        display.error(resp.json().get("message", "Failed to create profile."))
        sys.exit(1)

    body = resp.json()
    if body.get("message") == "Profile already exists":
        console.print("[yellow]Profile already exists:[/yellow]")
    else:
        display.success("Profile created:")
    display.profile_detail(body["data"])


# ─── insighta profiles export ─────────────────────────────────────────────────

@profiles.command("export")
@click.option("--format", "fmt", type=click.Choice(["csv"]), default="csv", show_default=True)
@click.option("--gender", type=click.Choice(["male", "female"]), default=None)
@click.option("--age-group", type=click.Choice(["child", "teenager", "adult", "senior"]), default=None)
@click.option("--country", default=None, metavar="CODE")
@click.option("--min-age", type=int, default=None)
@click.option("--max-age", type=int, default=None)
@click.option("--sort-by", type=click.Choice(["age", "created_at", "gender_probability"]), default=None)
@click.option("--order", type=click.Choice(["asc", "desc"]), default="asc")
def export_profiles(fmt, gender, age_group, country, min_age, max_age, sort_by, order):
    """Export profiles to a CSV file in the current directory."""
    params: dict = {"format": fmt}
    if gender:
        params["gender"] = gender
    if age_group:
        params["age_group"] = age_group
    if country:
        params["country_id"] = country.upper()
    if min_age is not None:
        params["min_age"] = min_age
    if max_age is not None:
        params["max_age"] = max_age
    if sort_by:
        params["sort_by"] = sort_by
    if order != "asc":
        params["order"] = order

    with Status("Exporting profiles...", console=console):
        resp = client.request("GET", "/api/profiles/export", params=params)

    if resp.status_code != 200:
        try:
            display.error(resp.json().get("message", "Export failed."))
        except Exception:
            display.error(f"Export failed with status {resp.status_code}.")
        sys.exit(1)

    # Extract filename from Content-Disposition or use a default
    disposition = resp.headers.get("content-disposition", "")
    filename = "profiles_export.csv"
    if 'filename="' in disposition:
        filename = disposition.split('filename="')[1].rstrip('"')

    output_path = Path.cwd() / filename
    output_path.write_bytes(resp.content)
    display.success(f"Exported to [bold]{output_path}[/bold]")
