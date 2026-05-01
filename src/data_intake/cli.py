"""``intake`` command line interface."""

from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from data_intake.audit import run_audit
from data_intake.demo import build_demo
from data_intake.loaders import FileTooLargeError
from data_intake.models import Severity
from data_intake.report import without_examples, write_reports
from data_intake.site import build_site

app = typer.Typer(help="First-day audit of client data exports.", no_args_is_help=True)
console = Console()


@app.command()
def audit(
    folder: Annotated[Path, typer.Argument(help="Folder of CSV and Excel exports.")],
    client: Annotated[str, typer.Option(help="Name shown on the report.")] = "Client",
    out: Annotated[Path, typer.Option(help="HTML report path.")] = Path("audit.html"),
    json: Annotated[Path | None, typer.Option(help="Also write findings as JSON.")] = None,
    as_of: Annotated[
        str | None, typer.Option(help="Export date (YYYY-MM-DD); later dates are flagged.")
    ] = None,
    hide_examples: Annotated[
        bool, typer.Option(help="Leave out example values (for reports shared beyond the client).")
    ] = False,
) -> None:
    """Audit a folder of exports and write the report."""
    try:
        result = run_audit(folder, client, date.fromisoformat(as_of) if as_of else None)
    except (FileNotFoundError, FileTooLargeError) as error:
        raise typer.BadParameter(str(error)) from error
    write_reports(without_examples(result) if hide_examples else result, out, json)
    console.print(
        f"[bold]{len(result.tables)}[/] tables, "
        f"[red]{result.count(Severity.CRITICAL)} critical[/], "
        f"[yellow]{result.count(Severity.WARNING)} warnings[/], {result.count(Severity.INFO)} notes"
    )
    console.print(f"Report: {out}" + (f"  Findings: {json}" if json else ""))


@app.command()
def demo(
    out: Annotated[Path, typer.Option(help="Where to write sample exports.")] = Path(
        "demo_exports"
    ),
) -> None:
    """Write two sets of messy sample exports to try the audit on."""
    for name, folder in build_demo(out).items():
        console.print(f"{name}: {folder}")


@app.command()
def site(out: Annotated[Path, typer.Option(help="Output directory.")] = Path("site")) -> None:
    """Build the demo site (sample exports plus their audits)."""
    console.print(f"Site: {build_site(out)}")
