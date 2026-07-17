from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Mapping, Sequence

import flet as ft

from .app import InvoiceWindowApp
from .launcher import XRechnungLauncherApp
from .processes import INVOICE_ENV_VAR


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--invoice", type=Path)
    args, _unknown = parser.parse_known_args(argv)
    return args


def resolve_invoice_path(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path | None:
    args = parse_args(argv)
    if args.invoice:
        return args.invoice

    env = os.environ if environ is None else environ
    raw_path = env.get(INVOICE_ENV_VAR)
    return Path(raw_path) if raw_path else None


async def launcher_main(page: ft.Page) -> None:
    XRechnungLauncherApp(page)


def invoice_main(invoice_path: Path):
    async def _main(page: ft.Page) -> None:
        # Give a newly opened invoice precedence over the launcher while it is
        # being shown. The topmost flag is released again below so the invoice
        # behaves like a normal application window afterwards.
        page.window.always_on_top = True
        page.window.focused = True
        InvoiceWindowApp(page, invoice_path)
        await page.window.wait_until_ready_to_show()
        await page.window.to_front()
        await asyncio.sleep(1)
        page.window.always_on_top = False
        page.update()

    return _main


def run(argv: Sequence[str] | None = None) -> None:
    invoice_path = resolve_invoice_path(argv)
    if invoice_path:
        ft.run(invoice_main(invoice_path))
    else:
        ft.run(launcher_main)


if __name__ == "__main__":
    run()
