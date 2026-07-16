from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import InvoiceDocument


def _format_decimal(value: Decimal | None, places: int | None = None) -> str:
    if value is None:
        return "–"
    if places is not None:
        value = value.quantize(Decimal(1).scaleb(-places))
    text = f"{value:f}"
    integer, dot, fraction = text.partition(".")
    integer = f"{int(integer):,}".replace(",", ".")
    if dot:
        return f"{integer},{fraction}"
    return integer


def _format_money(value: Decimal | None, currency: str | None) -> str:
    if value is None:
        return "–"
    return f"{_format_decimal(value, 2)} {currency or ''}".strip()


def render_html(document: InvoiceDocument, output_path: str | Path) -> Path:
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["money"] = lambda value: _format_money(value, document.currency)
    env.filters["number"] = _format_decimal
    template = env.get_template("invoice.html.j2")

    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.render(invoice=document), encoding="utf-8")
    return output


def render_json(document: InvoiceDocument, output_path: str | Path) -> Path:
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output
