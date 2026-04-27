from rich.console import Console
from rich.table import Table

console = Console()


def profiles_table(profiles: list[dict]) -> None:
    if not profiles:
        console.print("[yellow]No profiles found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", style="dim", max_width=36, no_wrap=True)
    table.add_column("Name", min_width=12)
    table.add_column("Gender")
    table.add_column("G%", justify="right")
    table.add_column("Age", justify="right")
    table.add_column("Group")
    table.add_column("Country")
    table.add_column("C%", justify="right")
    table.add_column("Created")

    for p in profiles:
        table.add_row(
            p.get("id", ""),
            p.get("name", "").title(),
            p.get("gender", ""),
            f"{p.get('gender_probability', 0):.0%}",
            str(p.get("age", "")),
            p.get("age_group", ""),
            f"{p.get('country_id', '')} · {p.get('country_name', '')}",
            f"{p.get('country_probability', 0):.0%}",
            (p.get("created_at") or "")[:10],
        )

    console.print(table)


def profile_detail(p: dict) -> None:
    table = Table(show_header=False, border_style="dim", padding=(0, 1))
    table.add_column("Field", style="bold cyan", min_width=20)
    table.add_column("Value")

    rows = [
        ("ID", p.get("id", "")),
        ("Name", p.get("name", "").title()),
        ("Gender", p.get("gender", "")),
        ("Gender probability", f"{p.get('gender_probability', 0):.0%}"),
        ("Age", str(p.get("age", ""))),
        ("Age group", p.get("age_group", "")),
        ("Country", f"{p.get('country_id', '')} — {p.get('country_name', '')}"),
        ("Country probability", f"{p.get('country_probability', 0):.0%}"),
        ("Created", p.get("created_at", "")),
    ]
    for field, value in rows:
        table.add_row(field, value)

    console.print(table)


def pagination_info(page: int, limit: int, total: int, total_pages: int) -> None:
    console.print(
        f"[dim]Page {page}/{total_pages} · {total} total · {limit} per page[/dim]"
    )


def whoami_table(user: dict) -> None:
    table = Table(show_header=False, border_style="dim", padding=(0, 1))
    table.add_column("", style="bold cyan", min_width=10)
    table.add_column("")
    table.add_row("Username", f"@{user['username']}")
    table.add_row("Email", user.get("email") or "—")
    table.add_row("Role", user["role"])
    table.add_row("ID", user["id"])
    console.print(table)


def error(msg: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {msg}")


def success(msg: str) -> None:
    console.print(f"[bold green]✓[/bold green] {msg}")
