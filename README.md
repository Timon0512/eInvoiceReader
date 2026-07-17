# XRechnungsreader – Backend und Flet-Desktopanwendung

Python-Anwendung zum Einlesen und Anzeigen elektronischer Rechnungen nach EN 16931 beziehungsweise XRechnung.

## Unterstützte XML-Syntaxen

- OASIS UBL 2.1 `Invoice`
- OASIS UBL 2.1 `CreditNote`
- UN/CEFACT Cross Industry Invoice (CII, Namespace-Version `:100`)
- automatische Syntax-Erkennung über Root-Element und Namespace

## Desktop-Frontend

Das Flet-Frontend enthält:

- nativen FilePicker für `.xml`-Dateien
- Mehrfachauswahl im FilePicker
- ein eigenes natives Flet-Fenster pro ausgewählter Rechnung
- Sitzungsliste mit Doppelklick zum erneuten Öffnen einer Rechnung
- Tabs für Übersicht, Positionen, Steuern/Summen, Zahlung, XML und Hinweise
- Button **Rechnung entfernen**, der nur das jeweilige Fenster schließt
- Export jeder Rechnung als PDF, HTML und JSON
- direkten PDF-Renderer ohne Chromium oder eingebetteten Browser

Drag-and-drop und die frühere eigene Flutter-Erweiterung wurden vollständig entfernt. Dadurch kann die Anwendung wieder mit dem normalen Flet-Client gestartet werden.

## Fensterarchitektur

Das Hauptfenster ist nur der Launcher:

1. Eine oder mehrere XML-Dateien werden über den FilePicker ausgewählt.
2. Für jede Datei startet ein eigener Anwendungsprozess.
3. Jeder Prozess erzeugt ein separates Flet-Fenster für genau eine Rechnung.
4. Das Schließen oder Entfernen einer Rechnung beeinflusst die anderen Fenster nicht.

Diese Trennung ist bewusst gewählt, damit jedes Rechnungsfenster einen eigenen Zustand und eigene Exportdialoge besitzt.

## Onefile Build unter windows mit nuitka

Voraussetzungen:

- Python 3.11 oder neuer
```powershell
 pip install -U nuitka
 python -m nuitka --standalone --onefile --disable-console --include-package-data=flet main.py
```

## Frontend starten

Mit dem mitgelieferten Skript:

```powershell
.\scripts\run_dev_windows.ps1
```

Direkt über Flet:

```powershell
flet run main.py
```

Alternativ nach Installation des Projekts:

```powershell
python -m pip install -e .
xrechnung-reader-gui
```

Oder über das mitgelieferte .exe build:

```powershell
.\exe build\main.exe
```

### Mehrere Dateien öffnen

1. Auf **XML-Dateien auswählen** klicken.
2. Im Dateidialog mit `Strg` oder `Umschalt` mehrere XML-Dateien markieren.
3. Auswahl bestätigen.
4. Jede Rechnung öffnet sich in einem eigenen Fenster.

Der Launcher bleibt geöffnet, sodass später weitere Dateien ausgewählt werden können.

### Rechnung aus der Sitzungsliste erneut öffnen

Unter **In dieser Sitzung geöffnet** bleibt jede einmal ausgewählte Rechnung als Kachel sichtbar. Ein Doppelklick auf die Kachel öffnet die Rechnung erneut in einem eigenen Fenster. Die Kachel wird dabei nicht dupliziert. Falls die XML-Datei zwischenzeitlich verschoben oder gelöscht wurde, zeigt der Launcher eine Fehlermeldung.

## Rechnung entfernen

Der Button **Rechnung entfernen** im jeweiligen Rechnungsfenster:

- schließt nur dieses Fenster,
- entfernt den Zustand dieser geöffneten Rechnung,
- verändert oder löscht die ursprüngliche XML-Datei nicht.

## Export

Jedes Rechnungsfenster bietet eigene Buttons für:

- PDF
- HTML
- JSON

Der PDF-Export erzeugt eine lesbare A4-Darstellung direkt aus dem gemeinsamen Rechnungsmodell.

## Windows-Release erstellen

```powershell
.\scripts\build_windows.ps1
```

Alternativ direkt:

```powershell
flet build windows . --clear-cache --product "XRechnungsreader" --artifact "XRechnungsreader" -v
```

Die Anwendung liegt anschließend typischerweise hier:

```text
build\windows\XRechnungsreader.exe
```

Im gepackten Build öffnet die Anwendung für jede Rechnung eine weitere Instanz derselben EXE. Der Dateipfad wird intern über die Umgebungsvariable `XRECHNUNG_INVOICE_PATH` übergeben, damit der Flet-Runner im normalen Produktionsmodus startet.

## Kommandozeilen-Backend

HTML-Ausgabe:

```powershell
python -m xrechnung_reader "C:\Rechnungen\rechnung.xml"
```

JSON-Ausgabe:

```powershell
python -m xrechnung_reader rechnung.xml --format json --output rechnung.json
```

## Nutzung aus Python

```python
from xrechnung_reader import XRechnungReader, render_html, render_pdf

reader = XRechnungReader()
invoice = reader.read(r"C:\Rechnungen\rechnung.xml")

render_html(invoice, "rechnung.html")
render_pdf(invoice, "rechnung.pdf")
```

## Tests

Der aktuelle Stand enthält Tests für:

- UBL-Parsing
- CII-Parsing
- deutsche Anzeigeformatierung
- Mehrfachauswahl und Pfadfilterung
- Entwicklungs- und Release-Befehle für separate Fenster
- Übergabe des Rechnungspfads per Argument oder Umgebungsvariable
- PDF-Erzeugung

```powershell
pytest
```

## Wichtige Abgrenzung

Der Reader erkennt die Syntax und extrahiert die wichtigsten semantischen Rechnungsdaten. Er ersetzt keine vollständige Konformitätsprüfung gegen XML Schema, EN-16931-Schematron und die jeweils gültige XRechnung-CIUS. Dafür sollte später der offizielle KoSIT Validator angebunden werden.
