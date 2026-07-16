from __future__ import annotations

import subprocess
from pathlib import Path

import flet as ft

from .processes import launch_invoice_window, normalise_selected_paths


class XRechnungLauncherApp:
    """Small launcher window which opens every selected XML in its own window."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.file_picker = ft.FilePicker()
        self.child_processes: list[subprocess.Popen[bytes]] = []
        self.opened_files: list[Path] = []
        self.status_text = ft.Text(
            "Noch keine Rechnung geöffnet.",
            color=ft.Colors.GREY_600,
            text_align=ft.TextAlign.CENTER,
        )
        self.recent_list = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

        self._configure_page()
        self.page.add(self._build_layout())

    def _configure_page(self) -> None:
        self.page.title = "XRechnungsreader"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.GREY_50
        self.page.window.width = 820
        self.page.window.height = 620
        self.page.window.min_width = 680
        self.page.window.min_height = 500

    def _build_layout(self) -> ft.Control:
        return ft.Column(
            controls=[
                self._build_header(),
                ft.Container(
                    expand=True,
                    padding=ft.Padding.all(34),
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                width=650,
                                bgcolor=ft.Colors.WHITE,
                                border=ft.Border.all(1, ft.Colors.GREY_200),
                                border_radius=ft.BorderRadius.all(18),
                                padding=ft.Padding.symmetric(horizontal=34, vertical=42),
                                content=ft.Column(
                                    controls=[
                                        ft.Icon(
                                            ft.Icons.UPLOAD_FILE_OUTLINED,
                                            size=68,
                                            color=ft.Colors.BLUE_700,
                                        ),
                                        ft.Text(
                                            "XRechnungen auswählen",
                                            size=25,
                                            weight=ft.FontWeight.BOLD,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                        ft.Text(
                                            "Wähle eine oder mehrere XML-Dateien aus. "
                                            "Jede Rechnung wird in einem eigenen Fenster geöffnet.",
                                            color=ft.Colors.GREY_600,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                        ft.FilledButton(
                                            "XML-Dateien auswählen",
                                            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                                            on_click=self._pick_invoices,
                                        ),
                                        self.status_text,
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=16,
                                ),
                            ),
                            ft.Container(
                                width=650,
                                expand=True,
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "In dieser Sitzung geöffnet",
                                            size=15,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        self.recent_list,
                                    ],
                                    spacing=10,
                                    expand=True,
                                ),
                            ),
                            ft.Text(
                                "Die Originaldateien werden nur gelesen und nicht verändert.",
                                size=12,
                                color=ft.Colors.GREY_600,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=22,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _build_header(self) -> ft.Control:
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
            padding=ft.Padding.symmetric(horizontal=26, vertical=18),
            content=ft.Row(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.RECEIPT_LONG_OUTLINED,
                                size=30,
                                color=ft.Colors.BLUE_800,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        "XRechnungsreader",
                                        size=21,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "UBL und UN/CEFACT CII",
                                        size=12,
                                        color=ft.Colors.GREY_600,
                                    ),
                                ],
                                spacing=1,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Text(
                        "Mehrfachauswahl",
                        color=ft.Colors.GREY_600,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )

    async def _pick_invoices(self, _event=None) -> None:
        files = await self.file_picker.pick_files(
            dialog_title="XRechnungen auswählen",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["xml"],
            allow_multiple=True,
        )
        if not files:
            return

        paths, errors = normalise_selected_paths(files)
        opened: list[Path] = []

        for path in paths:
            error = self._launch_invoice(path, add_to_recent=True)
            if error is None:
                opened.append(path)
            else:
                errors.append(error)

        self._remove_finished_processes()
        if opened:
            self.status_text.value = (
                f"{len(opened)} Rechnungsfenster geöffnet."
                if len(opened) != 1
                else "1 Rechnungsfenster geöffnet."
            )
            self.status_text.color = ft.Colors.GREEN_700
            self._refresh_recent_list()
            self.page.update()

        if errors:
            self._show_errors(errors)

    def _launch_invoice(self, path: Path, *, add_to_recent: bool) -> str | None:
        """Open one invoice window and optionally add it to the session history."""

        if not path.is_file():
            return f"{path.name}: Die Datei wurde nicht gefunden."

        try:
            process = launch_invoice_window(path)
        except OSError as exc:
            return f"{path.name}: Das Fenster konnte nicht geöffnet werden ({exc})."

        self.child_processes.append(process)
        if add_to_recent and path not in self.opened_files:
            self.opened_files.append(path)
        return None

    def _reopen_recent_invoice(self, path: Path) -> None:
        """Open a session-history invoice again after a double-click."""

        error = self._launch_invoice(path, add_to_recent=False)
        self._remove_finished_processes()
        if error is not None:
            self._show_errors([error])
            return

        self.status_text.value = f"{path.name} erneut geöffnet."
        self.status_text.color = ft.Colors.GREEN_700
        self.page.update()

    def _remove_finished_processes(self) -> None:
        self.child_processes = [
            process for process in self.child_processes if process.poll() is None
        ]

    def _refresh_recent_list(self) -> None:
        self.recent_list.controls.clear()
        for path in reversed(self.opened_files[-10:]):
            card = ft.Container(
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, ft.Colors.GREY_200),
                border_radius=ft.BorderRadius.all(9),
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.DESCRIPTION_OUTLINED,
                            size=20,
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(path.name, weight=ft.FontWeight.W_500),
                                ft.Text(
                                    str(path.parent),
                                    size=11,
                                    color=ft.Colors.GREY_600,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    "Doppelklick zum erneuten Öffnen",
                                    size=10,
                                    color=ft.Colors.BLUE_GREY_400,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                ),
            )
            self.recent_list.controls.append(
                ft.GestureDetector(
                    content=card,
                    on_double_tap=lambda _event, invoice_path=path: (
                        self._reopen_recent_invoice(invoice_path)
                    ),
                )
            )

    def _show_errors(self, errors: list[str]) -> None:
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.ORANGE_800),
                    ft.Text("Einige Dateien konnten nicht geöffnet werden"),
                ]
            ),
            content=ft.Container(
                width=620,
                content=ft.Column(
                    controls=[ft.Text(error, selectable=True) for error in errors],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.TextButton("Schließen", on_click=lambda _: self.page.pop_dialog())
            ],
        )
        self.page.show_dialog(dialog)
