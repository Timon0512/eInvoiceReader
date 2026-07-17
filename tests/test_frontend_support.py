import asyncio
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import xrechnung_app.main as frontend_main
from xrechnung_app.formatting import german_date, money, party_lines
from xrechnung_app.launcher import XRechnungLauncherApp
from xrechnung_app.main import parse_args, resolve_invoice_path
from xrechnung_app.processes import (
    INVOICE_ENV_VAR,
    build_child_environment,
    build_invoice_process_command,
    is_packaged_flet_runtime,
    launch_invoice_window,
    normalise_selected_paths,
)
from xrechnung_reader.models import Address, InvoiceDocument, InvoiceLine, Party
from xrechnung_reader.pdf import render_pdf


def test_german_formatting() -> None:
    assert german_date("2026-07-16") == "16.07.2026"
    assert money(Decimal("1234.5"), "EUR") == "1.234,50 EUR"
    party = Party(name="Muster GmbH", address=Address(postal_code="50667", city="Köln"))
    assert party_lines(party) == ["Muster GmbH", "50667 Köln"]


def test_file_picker_results_support_multiple_xml_files(tmp_path: Path) -> None:
    first = tmp_path / "first.xml"
    second = tmp_path / "second.XML"
    other = tmp_path / "notes.txt"
    first.write_text("<Invoice/>", encoding="utf-8")
    second.write_text("<Invoice/>", encoding="utf-8")
    other.write_text("not xml", encoding="utf-8")

    files = [
        SimpleNamespace(path=str(first), name=first.name),
        SimpleNamespace(path=str(second), name=second.name),
        SimpleNamespace(path=str(first), name=first.name),
        SimpleNamespace(path=str(other), name=other.name),
        SimpleNamespace(path=None, name="missing.xml"),
    ]

    paths, errors = normalise_selected_paths(files)

    assert paths == [first.resolve(), second.resolve()]
    assert len(errors) == 2
    assert "nur XML-Dateien" in errors[0]
    assert "kein lokaler Dateipfad" in errors[1]


def test_development_invoice_window_command() -> None:
    command = build_invoice_process_command(
        executable="python.exe",
        packaged=False,
    )

    assert command == [
        "python.exe",
        "-m",
        "xrechnung_app.main",
    ]


def test_packaged_invoice_window_command() -> None:
    command = build_invoice_process_command(
        executable="XRechnungsreader.exe",
        packaged=True,
    )

    assert command == ["XRechnungsreader.exe"]


def test_packaged_runtime_detection() -> None:
    assert is_packaged_flet_runtime({"FLET_APP_STORAGE_DATA": r"C:\\AppData"})
    assert not is_packaged_flet_runtime({})


def test_nuitka_runtime_detection(monkeypatch) -> None:
    monkeypatch.setitem(
        is_packaged_flet_runtime.__globals__,
        "__compiled__",
        SimpleNamespace(),
    )

    assert is_packaged_flet_runtime({})


def test_packaged_window_launch_does_not_use_extraction_directory(
    tmp_path: Path, monkeypatch
) -> None:
    invoice = tmp_path / "invoice.xml"
    invoice.write_text("<Invoice/>", encoding="utf-8")
    popen_calls: list[tuple[list[str], dict[str, object]]] = []
    fake_process = SimpleNamespace()

    def fake_popen(command: list[str], **kwargs: object):
        popen_calls.append((command, kwargs))
        return fake_process

    monkeypatch.setattr("xrechnung_app.processes.subprocess.Popen", fake_popen)

    result = launch_invoice_window(
        invoice,
        executable=r"Z:\\Programme\\XRechnungsreader.exe",
        packaged=True,
    )

    assert result is fake_process
    assert popen_calls[0][0] == [r"Z:\\Programme\\XRechnungsreader.exe"]
    assert "cwd" not in popen_calls[0][1]
    assert popen_calls[0][1]["env"][INVOICE_ENV_VAR] == str(invoice.resolve())


def test_invoice_argument_is_parsed(tmp_path: Path) -> None:
    invoice = tmp_path / "invoice.xml"
    args = parse_args(["--invoice", str(invoice)])
    assert args.invoice == invoice


def test_invoice_path_can_come_from_environment(tmp_path: Path) -> None:
    invoice = tmp_path / "invoice.xml"
    resolved = resolve_invoice_path([], {INVOICE_ENV_VAR: str(invoice)})
    assert resolved == invoice


def test_invoice_window_gets_temporary_initial_priority(
    tmp_path: Path, monkeypatch
) -> None:
    invoice = tmp_path / "invoice.xml"
    events: list[str] = []

    class FakeWindow:
        always_on_top = False
        focused = False

        async def wait_until_ready_to_show(self) -> None:
            events.append("ready")

        async def to_front(self) -> None:
            events.append("front")

    page = SimpleNamespace(
        window=FakeWindow(),
        update=lambda: events.append("update"),
    )

    monkeypatch.setattr(
        frontend_main,
        "InvoiceWindowApp",
        lambda _page, path: events.append(f"app:{path.name}"),
    )

    async def no_delay(seconds: float) -> None:
        events.append(f"delay:{seconds:g}")

    monkeypatch.setattr(frontend_main.asyncio, "sleep", no_delay)

    asyncio.run(frontend_main.invoice_main(invoice)(page))

    assert page.window.focused is True
    assert page.window.always_on_top is False
    assert events == ["app:invoice.xml", "ready", "front", "delay:1", "update"]



def test_child_environment_resets_flet_runtime_values(tmp_path: Path) -> None:
    invoice = tmp_path / "invoice.xml"
    invoice.write_text("<Invoice/>", encoding="utf-8")
    env = build_child_environment(
        invoice,
        {
            "KEEP_ME": "yes",
            "FLET_DART_BRIDGE_PORT": "111",
            "FLET_DART_BRIDGE_EXIT_PORT": "222",
            "FLET_PAGE_URL": "tcp://old",
            "FLET_APP_CONSOLE": "old.log",
        },
    )

    assert env["KEEP_ME"] == "yes"
    assert env[INVOICE_ENV_VAR] == str(invoice.resolve())
    assert "FLET_DART_BRIDGE_PORT" not in env
    assert "FLET_DART_BRIDGE_EXIT_PORT" not in env
    assert "FLET_PAGE_URL" not in env
    assert "FLET_APP_CONSOLE" not in env

def test_pdf_renderer_creates_pdf(tmp_path: Path) -> None:
    invoice = InvoiceDocument(
        source_file="rechnung.xml",
        syntax="UBL 2.1 Invoice",
        document_kind="invoice",
        invoice_number="RE-2026-001",
        issue_date="2026-07-16",
        currency="EUR",
        seller=Party(name="Muster GmbH"),
        buyer=Party(name="Beispiel AG"),
        lines=[
            InvoiceLine(
                line_id="1",
                item_name="Beratung",
                quantity=Decimal("2"),
                unit_code="HUR",
                unit_price=Decimal("100"),
                line_net_amount=Decimal("200"),
                tax_rate=Decimal("19"),
            )
        ],
    )
    invoice.totals.payable_amount = Decimal("238")
    path = render_pdf(invoice, tmp_path / "rechnung.pdf")
    assert path.exists()
    assert path.read_bytes().startswith(b"%PDF")


def test_reopening_recent_invoice_does_not_duplicate_history(
    tmp_path: Path, monkeypatch
) -> None:
    invoice = tmp_path / "invoice.xml"
    invoice.write_text("<Invoice/>", encoding="utf-8")
    fake_process = SimpleNamespace(poll=lambda: None)
    monkeypatch.setattr(
        "xrechnung_app.launcher.launch_invoice_window",
        lambda _path: fake_process,
    )

    updates: list[bool] = []
    app = XRechnungLauncherApp.__new__(XRechnungLauncherApp)
    app.child_processes = []
    app.opened_files = [invoice.resolve()]
    app.status_text = SimpleNamespace(value="", color=None)
    app.page = SimpleNamespace(update=lambda: updates.append(True))

    app._reopen_recent_invoice(invoice.resolve())

    assert app.opened_files == [invoice.resolve()]
    assert app.child_processes == [fake_process]
    assert app.status_text.value == "invoice.xml erneut geöffnet."
    assert updates == [True]
