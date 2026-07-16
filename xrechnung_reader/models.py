from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


@dataclass(slots=True)
class Address:
    street: str | None = None
    additional_street: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country_subdivision: str | None = None
    country_code: str | None = None


@dataclass(slots=True)
class Party:
    name: str | None = None
    trading_name: str | None = None
    identifier: str | None = None
    vat_identifier: str | None = None
    electronic_address: str | None = None
    electronic_address_scheme: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    address: Address = field(default_factory=Address)


@dataclass(slots=True)
class PaymentInfo:
    means_code: str | None = None
    means_text: str | None = None
    payment_reference: str | None = None
    iban: str | None = None
    account_name: str | None = None
    terms: str | None = None


@dataclass(slots=True)
class TaxBreakdown:
    category_code: str | None = None
    rate: Decimal | None = None
    taxable_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    exemption_reason: str | None = None


@dataclass(slots=True)
class MonetaryTotals:
    line_net_total: Decimal | None = None
    allowance_total: Decimal | None = None
    charge_total: Decimal | None = None
    tax_exclusive_total: Decimal | None = None
    tax_total: Decimal | None = None
    tax_inclusive_total: Decimal | None = None
    prepaid_total: Decimal | None = None
    rounding_amount: Decimal | None = None
    payable_amount: Decimal | None = None


@dataclass(slots=True)
class InvoiceLine:
    line_id: str | None = None
    item_name: str | None = None
    description: str | None = None
    seller_item_id: str | None = None
    buyer_item_id: str | None = None
    quantity: Decimal | None = None
    unit_code: str | None = None
    unit_price: Decimal | None = None
    price_base_quantity: Decimal | None = None
    line_net_amount: Decimal | None = None
    tax_category_code: str | None = None
    tax_rate: Decimal | None = None


@dataclass(slots=True)
class InvoiceDocument:
    source_file: str
    syntax: str
    document_kind: str
    specification_id: str | None = None
    business_process_id: str | None = None
    invoice_number: str | None = None
    invoice_type_code: str | None = None
    issue_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    buyer_reference: str | None = None
    order_reference: str | None = None
    contract_reference: str | None = None
    seller: Party = field(default_factory=Party)
    buyer: Party = field(default_factory=Party)
    payment: PaymentInfo = field(default_factory=PaymentInfo)
    tax_breakdown: list[TaxBreakdown] = field(default_factory=list)
    totals: MonetaryTotals = field(default_factory=MonetaryTotals)
    lines: list[InvoiceLine] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_value(asdict(self))
