from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from xrechnung_reader.models import InvoiceDocument


@dataclass
class AppState:
    current_file: Path | None = None
    invoice: InvoiceDocument | None = None
    original_xml: str | None = None

    def clear(self) -> None:
        self.current_file = None
        self.invoice = None
        self.original_xml = None
