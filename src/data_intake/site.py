"""Static site with the demo audits, for GitHub Pages."""

import shutil
from pathlib import Path

from data_intake.audit import run_audit
from data_intake.demo import AS_OF, build_demo
from data_intake.report import _env, write_reports

BUSINESSES = {
    "shop": ("Pinecrest Goods", "Online homeware store: orders, customers and products."),
    "studio": ("Northline Studio", "Design studio: invoices, clients and timesheets."),
}


SITE_MARKER = ".intake-site"


class UnsafeOutputError(ValueError):
    """Raised instead of deleting a folder this tool did not create."""


def _clear_previous_site(out_dir: Path) -> None:
    """Delete an earlier build, but never a folder that is not one."""
    if not out_dir.exists():
        return
    if any(out_dir.iterdir()) and not (out_dir / SITE_MARKER).exists():
        raise UnsafeOutputError(
            f"{out_dir} is not empty and was not built by intake site; choose another --out"
        )
    shutil.rmtree(out_dir)


def build_site(out_dir: Path) -> Path:
    """Generate the demo exports, audit them, and write an index page. Returns index path."""
    _clear_previous_site(out_dir)
    folders = build_demo(out_dir / "exports")
    cards = []
    for key, folder in folders.items():
        name, blurb = BUSINESSES[key]
        audit = run_audit(folder, name, as_of=AS_OF)
        write_reports(audit, out_dir / key / "index.html", out_dir / key / "findings.json")
        cards.append(
            {
                "key": key,
                "name": name,
                "blurb": blurb,
                "audit": audit,
                "files": sorted(p.name for p in folder.iterdir()),
            }
        )
    (out_dir / SITE_MARKER).write_text("Built by intake site; safe to delete.\n")
    index = out_dir / "index.html"
    index.write_text(_env.get_template("site_index.html.j2").render(cards=cards), encoding="utf-8")
    return index
