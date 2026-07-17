from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

INVOICE_ENV_VAR = "XRECHNUNG_INVOICE_PATH"


def is_packaged_flet_runtime(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether the Python code runs inside a packaged native Flet app."""

    env = os.environ if environ is None else environ
    return (
        bool(env.get("FLET_APP_STORAGE_DATA"))
        or bool(getattr(sys, "frozen", False))
        # Nuitka deliberately does not set sys.frozen. Every compiled module
        # receives __compiled__ instead, including standalone/onefile builds.
        or globals().get("__compiled__") is not None
    )


def _packaged_executable() -> str:
    """Return the original packaged executable, including for Nuitka onefile."""

    compiled = globals().get("__compiled__")
    candidates = [
        getattr(compiled, "original_argv0", None),
        sys.argv[0] if compiled is not None and sys.argv else None,
        sys.executable,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path.resolve())

    # Keep subprocess' normal error reporting if none of the candidates can be
    # inspected (for example because a mapped drive has just disconnected).
    return str(sys.executable)


def build_invoice_process_command(
    *,
    executable: str | Path | None = None,
    packaged: bool | None = None,
) -> list[str]:
    """Build the command for an independent invoice window process.

    A packaged Flet app relaunches its host executable without command-line
    arguments. The invoice path is passed via an environment variable so the
    Flet runner stays in production mode. During development a new Python
    process starts the frontend module directly.
    """

    is_packaged = is_packaged_flet_runtime() if packaged is None else packaged
    if executable is not None:
        exe = str(executable)
    elif is_packaged:
        exe = _packaged_executable()
    else:
        exe = str(sys.executable)

    if is_packaged:
        return [exe]
    return [exe, "-m", "xrechnung_app.main"]


def build_child_environment(
    invoice_path: str | Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Create a clean environment for a new independent Flet runtime."""

    path = Path(invoice_path).expanduser().resolve()
    child_env = dict(os.environ if environ is None else environ)

    # These values belong to the current Flet process and must never be reused
    # by a newly launched native app instance. The new Flet host creates fresh
    # bridge ports and its own console log during startup.
    for key in (
        "FLET_DART_BRIDGE_PORT",
        "FLET_DART_BRIDGE_EXIT_PORT",
        "FLET_PAGE_URL",
        "FLET_APP_CONSOLE",
    ):
        child_env.pop(key, None)

    child_env[INVOICE_ENV_VAR] = str(path)
    return child_env


def launch_invoice_window(
    invoice_path: str | Path,
    *,
    executable: str | Path | None = None,
    packaged: bool | None = None,
) -> subprocess.Popen[bytes]:
    """Launch one XML invoice in a separate native Flet application window."""

    path = Path(invoice_path).expanduser().resolve()
    is_packaged = is_packaged_flet_runtime() if packaged is None else packaged
    command = build_invoice_process_command(
        executable=executable,
        packaged=is_packaged,
    )
    child_env = build_child_environment(path)

    kwargs: dict[str, object] = {
        "close_fds": True,
        "env": child_env,
    }
    if not is_packaged:
        # Source starts need the project root so ``python -m`` can import the
        # application. Packaged builds must not use __file__ as their cwd:
        # with Nuitka onefile that path belongs to the temporary extraction
        # directory and is not a stable launch location on Citrix systems.
        kwargs["cwd"] = str(Path(__file__).resolve().parent.parent)
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    return subprocess.Popen(command, **kwargs)  # type: ignore[arg-type]


def normalise_selected_paths(files: Sequence[object]) -> tuple[list[Path], list[str]]:
    """Convert FilePicker results into unique XML paths and user-facing errors."""

    paths: list[Path] = []
    errors: list[str] = []
    seen: set[Path] = set()

    for file in files:
        raw_path = getattr(file, "path", None)
        name = getattr(file, "name", "Unbekannte Datei")
        if not raw_path:
            errors.append(f"Für {name} konnte kein lokaler Dateipfad ermittelt werden.")
            continue

        path = Path(raw_path).expanduser().resolve()
        if path.suffix.lower() != ".xml":
            errors.append(f"{path.name}: Es werden nur XML-Dateien unterstützt.")
            continue
        if not path.is_file():
            errors.append(f"{path.name}: Die Datei wurde nicht gefunden.")
            continue
        if path in seen:
            continue

        seen.add(path)
        paths.append(path)

    return paths, errors
