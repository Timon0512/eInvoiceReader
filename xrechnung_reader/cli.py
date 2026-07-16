from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .parser import XRechnungError, read_invoice
from .render import render_html, render_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xrechnung-reader",
        description="Liest EN-16931-/XRechnung-XML in UBL- oder CII-Syntax.",
    )
    parser.add_argument("input", type=Path, help="Pfad zur XML-Rechnung")
    parser.add_argument(
        "-f",
        "--format",
        choices=("html", "json"),
        default="html",
        help="Ausgabeformat (Standard: html)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Ausgabepfad; Standard ist <input>.html bzw. <input>.json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output = args.output or args.input.with_suffix(f".{args.format}")

    try:
        invoice = read_invoice(args.input)
        result = render_html(invoice, output) if args.format == "html" else render_json(invoice, output)
    except XRechnungError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Dateifehler: {exc}", file=sys.stderr)
        return 3

    print(f"Erkannt: {invoice.syntax} / {invoice.document_kind}")
    print(f"Ausgabe: {result}")
    if invoice.warnings:
        print(f"Hinweise: {len(invoice.warnings)}")
    return 0
