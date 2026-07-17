from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import flet as ft

from xrechnung_reader import (
    InvalidInvoiceError,
    UnsupportedSyntaxError,
    XRechnungReader,
    render_html,
    render_json,
)
from xrechnung_reader.pdf import render_pdf

from .formatting import display, german_date, money, number, party_lines, percent
from .state import AppState


class InvoiceWindowApp:
    """Displays exactly one invoice in its own native Flet window."""

    def __init__(self, page: ft.Page, invoice_path: Path) -> None:
        self.page = page
        self.reader = XRechnungReader()
        self.state = AppState()
        self.file_picker = ft.FilePicker()
        self.root = ft.Column(expand=True, spacing=0)

        self._configure_page(invoice_path)
        self.page.add(self.root)
        self._load_and_render(invoice_path)

    def _configure_page(self, invoice_path: Path) -> None:
        self.page.title = f"XRechnung – {invoice_path.name}"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.GREY_50
        self.page.window.width = 1220
        self.page.window.height = 840
        self.page.window.min_width = 900
        self.page.window.min_height = 650

    def _load_and_render(self, path: Path) -> None:
        try:
            path = path.expanduser().resolve()
            if path.suffix.lower() != ".xml":
                raise ValueError("Bitte wählen Sie eine Datei mit der Endung .xml aus.")
            if not path.is_file():
                raise FileNotFoundError(f"Die Datei wurde nicht gefunden: {path}")

            invoice = self.reader.read(path)
            self.state.current_file = path
            self.state.invoice = invoice
            self.state.original_xml = self._read_xml_text(path)
            self.page.title = f"XRechnung {display(invoice.invoice_number)} – {path.name}"
            self._render_invoice()
        except UnsupportedSyntaxError as exc:
            self._render_load_error("Nicht unterstützte Rechnungssyntax", str(exc))
        except InvalidInvoiceError as exc:
            self._render_load_error("XML-Datei konnte nicht als Rechnung gelesen werden", str(exc))
        except (OSError, ValueError) as exc:
            self._render_load_error("Datei konnte nicht geöffnet werden", str(exc))
        except Exception as exc:  # defensive UI boundary
            self._render_load_error(
                "Unerwarteter Fehler beim Einlesen",
                str(exc),
            )

    @staticmethod
    def _read_xml_text(path: Path) -> str:
        raw = path.read_bytes()
        match = re.match(br"\s*<\?xml[^>]*encoding=[\"']([^\"']+)", raw, re.I)
        encoding = match.group(1).decode("ascii", errors="ignore") if match else "utf-8"
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            return raw.decode("utf-8", errors="replace")

    def _render_invoice(self) -> None:
        self.root.controls.clear()
        self.root.controls.extend(
            [
                self._build_header(),
                ft.Container(
                    content=self._build_tabs_control(),
                    padding=ft.Padding.all(18),
                    expand=True,
                ),
            ]
        )
        self.page.update()

    def _build_header(self) -> ft.Control:
        invoice = self._require_invoice()
        file_name = self.state.current_file.name if self.state.current_file else "Rechnung.xml"
        warning_text = (
            f"{len(invoice.warnings)} Warnung(en)"
            if invoice.warnings
            else "Keine Parserwarnungen"
        )
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
            padding=ft.Padding.symmetric(horizontal=24, vertical=14),
            content=ft.Row(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.RECEIPT_LONG_OUTLINED,
                                size=32,
                                color=ft.Colors.BLUE_800,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        f"Rechnung {display(invoice.invoice_number)}",
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"{invoice.syntax} · {file_name}",
                                        size=12,
                                        color=ft.Colors.GREY_600,
                                    ),
                                ],
                                spacing=2,
                            ),
                            ft.Chip(label=warning_text),
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton(
                                "PDF",
                                icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
                                on_click=self._save_pdf,
                            ),
                            ft.OutlinedButton(
                                "HTML",
                                icon=ft.Icons.WEB_OUTLINED,
                                on_click=self._save_html,
                            ),
                            ft.OutlinedButton(
                                "JSON",
                                icon=ft.Icons.DATA_OBJECT,
                                on_click=self._save_json,
                            ),
                            ft.TextButton(
                                "Rechnung schließen",
                                icon=ft.Icons.CLOSE,
                                on_click=self._remove_invoice,
                                style=ft.ButtonStyle(color=ft.Colors.RED_700),
                            ),
                        ],
                        spacing=6,
                        wrap=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _build_tabs_control(self) -> ft.Control:
        tabs = [
            ("Übersicht", ft.Icons.DASHBOARD_OUTLINED, self._overview_tab()),
            ("Positionen", ft.Icons.FORMAT_LIST_NUMBERED, self._positions_tab()),
            ("Steuer & Summen", ft.Icons.CALCULATE_OUTLINED, self._totals_tab()),
            ("Zahlung", ft.Icons.ACCOUNT_BALANCE_OUTLINED, self._payment_tab()),
            ("XML", ft.Icons.CODE, self._xml_tab()),
            ("Hinweise", ft.Icons.REPORT_OUTLINED, self._messages_tab()),
        ]
        return ft.Tabs(
            length=len(tabs),
            expand=True,
            content=ft.Column(
                controls=[
                    ft.TabBar(
                        tabs=[ft.Tab(label=label, icon=icon) for label, icon, _ in tabs],
                        scrollable=True,
                    ),
                    ft.TabBarView(
                        controls=[content for _, _, content in tabs],
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
            ),
        )

    def _render_load_error(self, title: str, details: str) -> None:
        self.root.controls.clear()
        self.root.controls.append(
            ft.Container(
                expand=True,
                padding=ft.Padding.all(40),
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color=ft.Colors.RED_700),
                        ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            details or "Die Datei konnte nicht verarbeitet werden.",
                            selectable=True,
                            color=ft.Colors.GREY_700,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.FilledButton(
                            "Fenster schließen",
                            icon=ft.Icons.CLOSE,
                            on_click=self._close_window,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=18,
                    expand=True,
                ),
            )
        )
        self.page.update()

    async def _close_window(self, _event=None) -> None:
        await self.page.window.close()

    def _overview_tab(self) -> ft.Control:
        invoice = self._require_invoice()
        return self._tab_scroll(
            [
                self._section_title("Rechnungsdaten"),
                ft.ResponsiveRow(
                    controls=[
                        self._field("Rechnungsnummer", invoice.invoice_number),
                        self._field("Rechnungsart", invoice.invoice_type_code),
                        self._field("Rechnungsdatum", german_date(invoice.issue_date)),
                        self._field("Fällig am", german_date(invoice.due_date)),
                        self._field("Währung", invoice.currency),
                        self._field("Käuferreferenz / Leitweg-ID", invoice.buyer_reference),
                        self._field("Bestellreferenz", invoice.order_reference),
                        self._field("Vertragsreferenz", invoice.contract_reference),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
                self._section_title("Rechnungspartner"),
                ft.ResponsiveRow(
                    controls=[
                        self._party_card("Verkäufer", party_lines(invoice.seller)),
                        self._party_card("Käufer", party_lines(invoice.buyer)),
                    ],
                    spacing=16,
                    run_spacing=16,
                ),
                self._section_title("Gesamt"),
                ft.Container(
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    border_radius=ft.BorderRadius.all(14),
                    padding=ft.Padding.all(20),
                    content=ft.Row(
                        controls=[
                            ft.Text("Zahlbetrag", color=ft.Colors.WHITE, size=16),
                            ft.Text(
                                money(invoice.totals.payable_amount, invoice.currency),
                                color=ft.Colors.WHITE,
                                size=24,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ),
            ]
        )

    def _positions_tab(self) -> ft.Control:
        invoice = self._require_invoice()
        rows: list[ft.DataRow] = []
        for index, line in enumerate(invoice.lines, start=1):
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(display(line.line_id or index))),
                        ft.DataCell(
                            ft.Container(
                                width=300,
                                content=ft.Text(
                                    display(line.item_name or line.description),
                                    max_lines=3,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            )
                        ),
                        ft.DataCell(ft.Text(f"{number(line.quantity, 3)} {line.unit_code or ''}".strip())),
                        ft.DataCell(ft.Text(money(line.unit_price, invoice.currency))),
                        ft.DataCell(ft.Text(percent(line.tax_rate))),
                        ft.DataCell(ft.Text(money(line.line_net_amount, invoice.currency))),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Pos.")),
                ft.DataColumn(ft.Text("Beschreibung")),
                ft.DataColumn(ft.Text("Menge"), numeric=True),
                ft.DataColumn(ft.Text("Einzelpreis"), numeric=True),
                ft.DataColumn(ft.Text("Steuer"), numeric=True),
                ft.DataColumn(ft.Text("Netto"), numeric=True),
            ],
            rows=rows,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            border_radius=ft.BorderRadius.all(10),
            heading_row_color=ft.Colors.BLUE_GREY_50,
            column_spacing=24,
        )
        return ft.Container(
            padding=ft.Padding.all(18),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Rechnungspositionen", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{len(rows)} Position(en)", color=ft.Colors.GREY_600),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(controls=[table], scroll=ft.ScrollMode.AUTO),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    def _totals_tab(self) -> ft.Control:
        invoice = self._require_invoice()
        tax_rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(display(tax.category_code))),
                    ft.DataCell(ft.Text(percent(tax.rate))),
                    ft.DataCell(ft.Text(money(tax.taxable_amount, invoice.currency))),
                    ft.DataCell(ft.Text(money(tax.tax_amount, invoice.currency))),
                    ft.DataCell(ft.Text(display(tax.exemption_reason))),
                ]
            )
            for tax in invoice.tax_breakdown
        ]
        totals = invoice.totals
        return self._tab_scroll(
            [
                self._section_title("Steueraufschlüsselung"),
                ft.Row(
                    controls=[
                        ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("Kategorie")),
                                ft.DataColumn(ft.Text("Satz"), numeric=True),
                                ft.DataColumn(ft.Text("Basis"), numeric=True),
                                ft.DataColumn(ft.Text("Steuer"), numeric=True),
                                ft.DataColumn(ft.Text("Befreiungsgrund")),
                            ],
                            rows=tax_rows,
                            border=ft.Border.all(1, ft.Colors.GREY_200),
                            border_radius=ft.BorderRadius.all(10),
                            heading_row_color=ft.Colors.BLUE_GREY_50,
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                ),
                self._section_title("Rechnungssummen"),
                self._totals_card(
                    [
                        ("Summe Positionen", money(totals.line_net_total, invoice.currency)),
                        ("Nachlässe", money(totals.allowance_total, invoice.currency)),
                        ("Zuschläge", money(totals.charge_total, invoice.currency)),
                        ("Nettobetrag", money(totals.tax_exclusive_total, invoice.currency)),
                        ("Umsatzsteuer", money(totals.tax_total, invoice.currency)),
                        ("Bruttobetrag", money(totals.tax_inclusive_total, invoice.currency)),
                        ("Bereits gezahlt", money(totals.prepaid_total, invoice.currency)),
                        ("Rundung", money(totals.rounding_amount, invoice.currency)),
                        ("Zahlbetrag", money(totals.payable_amount, invoice.currency)),
                    ]
                ),
            ]
        )

    def _payment_tab(self) -> ft.Control:
        invoice = self._require_invoice()
        payment = invoice.payment
        return self._tab_scroll(
            [
                self._section_title("Zahlungsinformationen"),
                ft.ResponsiveRow(
                    controls=[
                        self._field("Zahlungsart", payment.means_text or payment.means_code),
                        self._field("Fälligkeitsdatum", german_date(invoice.due_date)),
                        self._copy_field("Zahlungsreferenz", payment.payment_reference),
                        self._field("Kontoinhaber", payment.account_name),
                        self._copy_field("IBAN", payment.iban),
                        self._field("Zahlungsbedingungen", payment.terms, col=12),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
            ]
        )

    def _xml_tab(self) -> ft.Control:
        xml = self.state.original_xml or ""
        return ft.Container(
            padding=ft.Padding.all(16),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Original-XML", size=18, weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                icon=ft.Icons.CONTENT_COPY,
                                tooltip="XML kopieren",
                                on_click=self._clipboard_handler(xml, "XML wurde kopiert."),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        bgcolor=ft.Colors.BLUE_GREY_900,
                        border_radius=ft.BorderRadius.all(10),
                        padding=ft.Padding.all(16),
                        content=ft.Text(
                            xml,
                            selectable=True,
                            font_family="monospace",
                            size=12,
                            color=ft.Colors.BLUE_GREY_50,
                            no_wrap=True,
                        ),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    def _messages_tab(self) -> ft.Control:
        invoice = self._require_invoice()
        controls: list[ft.Control] = [
            self._message_card(
                "Information",
                f"Die Syntax wurde als {invoice.syntax} erkannt.",
                ft.Icons.INFO_OUTLINE,
                ft.Colors.BLUE_700,
            )
        ]
        controls.extend(
            self._message_card("Warnung", message, ft.Icons.WARNING_AMBER, ft.Colors.ORANGE_800)
            for message in invoice.warnings
        )
        controls.extend(
            self._message_card("Hinweis", message, ft.Icons.NOTES, ft.Colors.BLUE_GREY_700)
            for message in invoice.notes
        )
        if not invoice.warnings:
            controls.append(
                self._message_card(
                    "Parser",
                    "Beim Auslesen wurden keine grundlegenden Parserwarnungen erzeugt.",
                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                    ft.Colors.GREEN_700,
                )
            )
        controls.append(
            self._message_card(
                "Abgrenzung",
                "Diese Ansicht ersetzt keine vollständige Schema-, Schematron- oder KoSIT-Validierung.",
                ft.Icons.GPP_MAYBE_OUTLINED,
                ft.Colors.RED_700,
            )
        )
        return self._tab_scroll(controls)

    def _tab_scroll(self, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(
            padding=ft.Padding.all(20),
            content=ft.Column(controls=controls, spacing=16, scroll=ft.ScrollMode.AUTO, expand=True),
        )

    def _section_title(self, title: str) -> ft.Control:
        return ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)

    def _field(self, label: str, value: object, col: int = 6) -> ft.Control:
        return ft.Container(
            col={"sm": 12, "md": col},
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            border_radius=ft.BorderRadius.all(10),
            padding=ft.Padding.all(14),
            content=ft.Column(
                controls=[
                    ft.Text(label, size=11, color=ft.Colors.GREY_600),
                    ft.Text(display(value), selectable=True, weight=ft.FontWeight.W_500),
                ],
                spacing=4,
            ),
        )

    def _copy_field(self, label: str, value: object, col: int = 6) -> ft.Control:
        text = display(value)
        return ft.Container(
            col={"sm": 12, "md": col},
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            border_radius=ft.BorderRadius.all(10),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(label, size=11, color=ft.Colors.GREY_600),
                            ft.Text(text, selectable=True, weight=ft.FontWeight.W_500),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CONTENT_COPY,
                        tooltip="Kopieren",
                        on_click=self._clipboard_handler(text, f"{label} wurde kopiert."),
                    ),
                ]
            ),
        )

    def _party_card(self, title: str, lines: list[str]) -> ft.Control:
        return ft.Container(
            col={"sm": 12, "md": 6},
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(18),
            content=ft.Column(
                controls=[
                    ft.Text(title, size=14, weight=ft.FontWeight.BOLD),
                    *[ft.Text(line, selectable=True) for line in lines],
                ],
                spacing=5,
            ),
        )

    def _totals_card(self, rows: list[tuple[str, str]]) -> ft.Control:
        controls: list[ft.Control] = []
        for index, (label, value) in enumerate(rows):
            is_total = index == len(rows) - 1
            if is_total:
                controls.append(ft.Divider(height=18))
            controls.append(
                ft.Row(
                    controls=[
                        ft.Text(label, weight=ft.FontWeight.BOLD if is_total else None),
                        ft.Text(
                            value,
                            size=18 if is_total else 14,
                            weight=ft.FontWeight.BOLD if is_total else ft.FontWeight.W_500,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )
        return ft.Container(
            width=600,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(20),
            content=ft.Column(controls=controls, spacing=10),
        )

    def _message_card(self, title: str, message: str, icon, color) -> ft.Control:
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            border_radius=ft.BorderRadius.all(10),
            padding=ft.Padding.all(14),
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=color),
                    ft.Column(
                        controls=[
                            ft.Text(title, weight=ft.FontWeight.BOLD),
                            ft.Text(message, selectable=True),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )

    async def _save_pdf(self, _event=None) -> None:
        await self._save_export("pdf", render_pdf)

    async def _save_html(self, _event=None) -> None:
        await self._save_export("html", render_html)

    async def _save_json(self, _event=None) -> None:
        await self._save_export("json", render_json)

    async def _save_export(
        self,
        extension: str,
        renderer: Callable[[object, str | Path], Path],
    ) -> None:
        invoice = self._require_invoice()
        safe_number = re.sub(r"[^A-Za-z0-9._-]+", "_", invoice.invoice_number or "Rechnung")
        output = await self.file_picker.save_file(
            dialog_title=f"{extension.upper()} speichern",
            file_name=f"XRechnung_{safe_number}.{extension}",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=[extension],
        )
        if not output:
            return
        path = Path(output)
        if path.suffix.lower() != f".{extension}":
            path = path.with_suffix(f".{extension}")
        try:
            renderer(invoice, path)
            self._show_snack(f"{extension.upper()} wurde gespeichert: {path.name}")
        except OSError as exc:
            self._show_error(f"Die Datei konnte nicht gespeichert werden.\n\n{exc}")

    async def _remove_invoice(self, _event=None) -> None:
        self.state.clear()
        await self.page.window.close()

    def _clipboard_handler(self, value: str, confirmation: str):
        async def handler(_event=None) -> None:
            await self.page.clipboard.set(value)
            self._show_snack(confirmation)

        return handler

    def _show_snack(self, message: str) -> None:
        self.page.show_dialog(
            ft.SnackBar(content=message, show_close_icon=True, duration=3500)
        )

    def _show_error(self, message: str) -> None:
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_700),
                    ft.Text("Aktion konnte nicht ausgeführt werden"),
                ]
            ),
            content=ft.Text(message, selectable=True),
            actions=[ft.TextButton("Schließen", on_click=lambda _: self.page.pop_dialog())],
        )
        self.page.show_dialog(dialog)

    def _require_invoice(self):
        if not self.state.invoice:
            raise RuntimeError("Es ist keine Rechnung geladen.")
        return self.state.invoice
