from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from fpdf import FPDF

from .models import Address, InvoiceDocument, Party


def _number(value: Decimal | None, places: int = 2) -> str:
    if value is None:
        return "-"
    text = f"{value:,.{places}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def _money(value: Decimal | None, currency: str | None) -> str:
    if value is None:
        return "-"
    return f"{_number(value)} {currency or ''}".strip()


def _address_lines(address: Address) -> list[str]:
    lines = [address.street, address.additional_street]
    city = " ".join(part for part in [address.postal_code, address.city] if part)
    if city:
        lines.append(city)
    if address.country_code:
        lines.append(address.country_code)
    return [line for line in lines if line]


def _party_lines(party: Party) -> list[str]:
    lines = [party.name or "-", party.trading_name]
    lines.extend(_address_lines(party.address))
    if party.vat_identifier:
        lines.append(f"USt-ID: {party.vat_identifier}")
    if party.electronic_address:
        lines.append(f"E-Adresse: {party.electronic_address}")
    return [line for line in lines if line]


def _find_unicode_font() -> Path | None:
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    return next((path for path in candidates if path.exists()), None)


def _safe_text(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("\t", " ").replace("\r", " ")


class InvoicePDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(self.font_family, size=8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, f"Seite {self.page_no()}", align="C")


def _label_value(pdf: InvoicePDF, label: str, value: object, width: float = 95) -> None:
    x = pdf.get_x()
    y = pdf.get_y()
    pdf.set_font(pdf.font_family, style="B", size=9)
    pdf.multi_cell(38, 5, _safe_text(label), new_x="RIGHT", new_y="TOP")
    pdf.set_font(pdf.font_family, size=9)
    pdf.multi_cell(width - 38, 5, _safe_text(value) or "-", new_x="LMARGIN", new_y="NEXT")
    if pdf.get_y() < y + 5:
        pdf.set_y(y + 5)
    pdf.set_x(x)


def _section(pdf: InvoicePDF, title: str) -> None:
    pdf.ln(3)
    pdf.set_fill_color(235, 240, 246)
    pdf.set_text_color(30, 48, 70)
    pdf.set_font(pdf.font_family, style="B", size=11)
    pdf.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(25, 25, 25)
    pdf.ln(2)


def _write_lines(pdf: InvoicePDF, lines: Iterable[str], width: float) -> None:
    pdf.set_font(pdf.font_family, size=9)
    for line in lines:
        pdf.multi_cell(width, 5, _safe_text(line), new_x="LMARGIN", new_y="NEXT")


def render_pdf(document: InvoiceDocument, output_path: str | Path) -> Path:
    """Render a human-readable A4 representation of an electronic invoice."""

    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    pdf = InvoicePDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    font_path = _find_unicode_font()
    if font_path:
        pdf.add_font("InvoiceSans", style="", fname=str(font_path))
        pdf.add_font("InvoiceSans", style="B", fname=str(font_path))
        pdf.font_family = "InvoiceSans"
    else:
        pdf.font_family = "Helvetica"

    pdf.set_title(f"XRechnung {document.invoice_number or ''}".strip())
    pdf.set_author(document.seller.name or "XRechnungsreader")
    pdf.add_page()

    pdf.set_font(pdf.font_family, style="B", size=18)
    pdf.set_text_color(25, 54, 88)
    pdf.cell(0, 10, "Elektronische Rechnung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(pdf.font_family, size=9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(
        0,
        6,
        f"{document.syntax} · {Path(document.source_file).name}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(25, 25, 25)

    _section(pdf, "Rechnungsdaten")
    _label_value(pdf, "Rechnungsnummer", document.invoice_number)
    _label_value(pdf, "Rechnungsdatum", document.issue_date)
    _label_value(pdf, "Fällig am", document.due_date)
    _label_value(pdf, "Währung", document.currency)
    _label_value(pdf, "Käuferreferenz", document.buyer_reference)
    _label_value(pdf, "Bestellreferenz", document.order_reference)
    _label_value(pdf, "Vertragsreferenz", document.contract_reference)

    _section(pdf, "Rechnungspartner")
    start_y = pdf.get_y()
    col_width = (pdf.w - pdf.l_margin - pdf.r_margin - 8) / 2
    left_x = pdf.l_margin
    right_x = left_x + col_width + 8

    pdf.set_xy(left_x, start_y)
    pdf.set_font(pdf.font_family, style="B", size=10)
    pdf.cell(col_width, 6, "Verkäufer", new_x="LMARGIN", new_y="NEXT")
    left_content_y = pdf.get_y()
    _write_lines(pdf, _party_lines(document.seller), col_width)
    left_end = pdf.get_y()

    pdf.set_xy(right_x, start_y)
    pdf.set_font(pdf.font_family, style="B", size=10)
    pdf.cell(col_width, 6, "Käufer", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(right_x)
    right_content_y = pdf.get_y()
    pdf.set_xy(right_x, right_content_y)
    pdf.set_font(pdf.font_family, size=9)
    for line in _party_lines(document.buyer):
        pdf.multi_cell(col_width, 5, _safe_text(line), new_x="LEFT", new_y="NEXT")
        pdf.set_x(right_x)
    right_end = pdf.get_y()
    pdf.set_y(max(left_end, right_end, left_content_y + 5))
    pdf.set_x(pdf.l_margin)

    _section(pdf, "Positionen")
    widths = [12, 73, 20, 23, 22, 26]
    headers = ["Pos.", "Beschreibung", "Menge", "Preis", "Steuer", "Netto"]
    pdf.set_fill_color(220, 228, 237)
    pdf.set_font(pdf.font_family, style="B", size=8)
    for width, header in zip(widths, headers):
        pdf.cell(width, 7, header, border=1, fill=True)
    pdf.ln()

    pdf.set_font(pdf.font_family, size=8)
    for index, line in enumerate(document.lines, start=1):
        if pdf.get_y() > 258:
            pdf.add_page()
            pdf.set_font(pdf.font_family, style="B", size=8)
            for width, header in zip(widths, headers):
                pdf.cell(width, 7, header, border=1, fill=True)
            pdf.ln()
            pdf.set_font(pdf.font_family, size=8)
        description = line.item_name or line.description or "-"
        row = [
            line.line_id or str(index),
            description[:68],
            f"{_number(line.quantity, 3)} {line.unit_code or ''}".strip(),
            _money(line.unit_price, document.currency),
            f"{_number(line.tax_rate)} %" if line.tax_rate is not None else "-",
            _money(line.line_net_amount, document.currency),
        ]
        for width, value in zip(widths, row):
            pdf.cell(width, 7, _safe_text(value), border=1)
        pdf.ln()

    _section(pdf, "Steuern und Summen")
    for tax in document.tax_breakdown:
        label = f"Steuer {tax.category_code or ''} / {_number(tax.rate)} %".strip()
        value = (
            f"Basis {_money(tax.taxable_amount, document.currency)} · "
            f"Betrag {_money(tax.tax_amount, document.currency)}"
        )
        _label_value(pdf, label, value)

    totals = document.totals
    for label, value in [
        ("Positionssumme", totals.line_net_total),
        ("Nachlässe", totals.allowance_total),
        ("Zuschläge", totals.charge_total),
        ("Nettobetrag", totals.tax_exclusive_total),
        ("Umsatzsteuer", totals.tax_total),
        ("Bruttobetrag", totals.tax_inclusive_total),
        ("Bereits gezahlt", totals.prepaid_total),
    ]:
        _label_value(pdf, label, _money(value, document.currency))

    pdf.ln(2)
    pdf.set_fill_color(25, 54, 88)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(pdf.font_family, style="B", size=12)
    pdf.cell(
        0,
        10,
        f"Zahlbetrag: {_money(totals.payable_amount, document.currency)}",
        fill=True,
        align="R",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(25, 25, 25)

    _section(pdf, "Zahlung")
    _label_value(pdf, "Zahlungsart", document.payment.means_text or document.payment.means_code)
    _label_value(pdf, "Zahlungsreferenz", document.payment.payment_reference)
    _label_value(pdf, "Kontoinhaber", document.payment.account_name)
    _label_value(pdf, "IBAN", document.payment.iban)
    _label_value(pdf, "Zahlungsbedingungen", document.payment.terms)

    if document.notes or document.warnings:
        _section(pdf, "Hinweise")
        pdf.set_font(pdf.font_family, size=9)
        for note in document.notes:
            pdf.multi_cell(0, 5, f"• {_safe_text(note)}", new_x="LMARGIN", new_y="NEXT")
        for warning in document.warnings:
            pdf.multi_cell(0, 5, f"Warnung: {_safe_text(warning)}", new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(output))
    return output
