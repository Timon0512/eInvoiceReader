from __future__ import annotations

from datetime import date
from decimal import Decimal

from xrechnung_reader.models import Address, Party


def display(value: object | None) -> str:
    return "–" if value is None or str(value).strip() == "" else str(value)


def number(value: Decimal | None, places: int = 2) -> str:
    if value is None:
        return "–"
    text = f"{value:,.{places}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def money(value: Decimal | None, currency: str | None) -> str:
    if value is None:
        return "–"
    return f"{number(value)} {currency or ''}".strip()


def percent(value: Decimal | None) -> str:
    return "–" if value is None else f"{number(value)} %"


def german_date(value: str | None) -> str:
    if not value:
        return "–"
    try:
        return date.fromisoformat(value[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return value


def address_lines(address: Address) -> list[str]:
    result = [address.street, address.additional_street]
    city = " ".join(part for part in [address.postal_code, address.city] if part)
    if city:
        result.append(city)
    if address.country_code:
        result.append(address.country_code)
    return [item for item in result if item]


def party_lines(party: Party) -> list[str]:
    result = [party.name, party.trading_name]
    result.extend(address_lines(party.address))
    if party.vat_identifier:
        result.append(f"USt-ID: {party.vat_identifier}")
    if party.electronic_address:
        result.append(f"E-Adresse: {party.electronic_address}")
    return [item for item in result if item] or ["–"]
