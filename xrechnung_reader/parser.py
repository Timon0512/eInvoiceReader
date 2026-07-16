from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from lxml import etree

from .models import (
    Address,
    InvoiceDocument,
    InvoiceLine,
    MonetaryTotals,
    Party,
    PaymentInfo,
    TaxBreakdown,
)

UBL_INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
UBL_CREDIT_NOTE_NS = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
CII_NS = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"

UBL_NS = {
    "ubl": UBL_INVOICE_NS,
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}

CII_NAMESPACES = {
    "rsm": CII_NS,
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
}

MAX_XML_SIZE_BYTES = 20 * 1024 * 1024


class XRechnungError(Exception):
    """Base exception for reader errors."""


class UnsupportedSyntaxError(XRechnungError):
    """Raised when the XML is neither EN-16931 UBL nor CII syntax."""


class InvalidInvoiceError(XRechnungError):
    """Raised when the input cannot be parsed as XML."""


def _first(node: etree._Element, xpath: str, ns: dict[str, str]) -> Any | None:
    result = node.xpath(xpath, namespaces=ns)
    if not result:
        return None
    return result[0]


def _text(node: etree._Element, xpath: str, ns: dict[str, str]) -> str | None:
    value = _first(node, xpath, ns)
    if value is None:
        return None
    if isinstance(value, etree._Element):
        text = "".join(value.itertext()).strip()
    else:
        text = str(value).strip()
    return text or None


def _texts(node: etree._Element, xpath: str, ns: dict[str, str]) -> list[str]:
    result: list[str] = []
    for value in node.xpath(xpath, namespaces=ns):
        if isinstance(value, etree._Element):
            text = "".join(value.itertext()).strip()
        else:
            text = str(value).strip()
        if text:
            result.append(text)
    return result


def _attribute(node: etree._Element, xpath: str, attribute: str, ns: dict[str, str]) -> str | None:
    element = _first(node, xpath, ns)
    if isinstance(element, etree._Element):
        value = element.get(attribute)
        return value.strip() if value and value.strip() else None
    return None


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _cii_date(node: etree._Element, xpath: str) -> str | None:
    date_element = _first(node, xpath, CII_NAMESPACES)
    if not isinstance(date_element, etree._Element):
        return None
    raw = (date_element.text or "").strip()
    date_format = date_element.get("format")
    if not raw:
        return None
    if date_format == "102" and len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    if date_format == "610" and len(raw) == 6 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}"
    return raw


def detect_syntax(root: etree._Element) -> tuple[str, str]:
    qname = etree.QName(root)
    namespace = qname.namespace
    local_name = qname.localname

    if namespace == UBL_INVOICE_NS and local_name == "Invoice":
        return "UBL", "Invoice"
    if namespace == UBL_CREDIT_NOTE_NS and local_name == "CreditNote":
        return "UBL", "CreditNote"
    if namespace == CII_NS and local_name == "CrossIndustryInvoice":
        return "CII", "Invoice"

    raise UnsupportedSyntaxError(
        f"Nicht unterstütztes XML-Format: {{{namespace}}}{local_name}. "
        "Erwartet wird UBL 2.1 Invoice/CreditNote oder UN/CEFACT CII D16B (Namespace :100)."
    )


def _safe_parse(path: Path) -> etree._Element:
    if not path.exists():
        raise InvalidInvoiceError(f"Datei nicht gefunden: {path}")
    if not path.is_file():
        raise InvalidInvoiceError(f"Pfad ist keine Datei: {path}")
    if path.suffix.lower() != ".xml":
        raise InvalidInvoiceError("Es werden ausschließlich .xml-Dateien unterstützt.")
    if path.stat().st_size > MAX_XML_SIZE_BYTES:
        raise InvalidInvoiceError("XML-Datei ist größer als das erlaubte Limit von 20 MB.")

    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        remove_comments=False,
    )
    try:
        tree = etree.parse(str(path), parser)
    except (etree.XMLSyntaxError, OSError) as exc:
        raise InvalidInvoiceError(f"XML konnte nicht gelesen werden: {exc}") from exc
    return tree.getroot()


def _ubl_party(root: etree._Element, base_xpath: str) -> Party:
    party_node = _first(root, base_xpath, UBL_NS)
    if not isinstance(party_node, etree._Element):
        return Party()

    address_node = _first(party_node, "cac:PostalAddress", UBL_NS)
    address = Address()
    if isinstance(address_node, etree._Element):
        address = Address(
            street=_text(address_node, "cbc:StreetName", UBL_NS),
            additional_street=_text(address_node, "cbc:AdditionalStreetName", UBL_NS),
            city=_text(address_node, "cbc:CityName", UBL_NS),
            postal_code=_text(address_node, "cbc:PostalZone", UBL_NS),
            country_subdivision=_text(address_node, "cbc:CountrySubentity", UBL_NS),
            country_code=_text(address_node, "cac:Country/cbc:IdentificationCode", UBL_NS),
        )

    return Party(
        name=(
            _text(party_node, "cac:PartyLegalEntity/cbc:RegistrationName", UBL_NS)
            or _text(party_node, "cac:PartyName/cbc:Name", UBL_NS)
        ),
        trading_name=_text(party_node, "cac:PartyName/cbc:Name", UBL_NS),
        identifier=_text(party_node, "cac:PartyIdentification/cbc:ID", UBL_NS),
        vat_identifier=(
            _text(
                party_node,
                "cac:PartyTaxScheme[cac:TaxScheme/cbc:ID='VAT']/cbc:CompanyID",
                UBL_NS,
            )
            or _text(party_node, "cac:PartyTaxScheme/cbc:CompanyID", UBL_NS)
        ),
        electronic_address=_text(party_node, "cbc:EndpointID", UBL_NS),
        electronic_address_scheme=_attribute(party_node, "cbc:EndpointID", "schemeID", UBL_NS),
        contact_name=_text(party_node, "cac:Contact/cbc:Name", UBL_NS),
        contact_email=_text(party_node, "cac:Contact/cbc:ElectronicMail", UBL_NS),
        contact_phone=_text(party_node, "cac:Contact/cbc:Telephone", UBL_NS),
        address=address,
    )


def _parse_ubl(root: etree._Element, path: Path, document_kind: str) -> InvoiceDocument:
    is_credit_note = document_kind == "CreditNote"
    type_code_element = "CreditNoteTypeCode" if is_credit_note else "InvoiceTypeCode"
    line_element = "CreditNoteLine" if is_credit_note else "InvoiceLine"
    quantity_element = "CreditedQuantity" if is_credit_note else "InvoicedQuantity"

    payment_means = _first(root, "cac:PaymentMeans", UBL_NS)
    payment_terms = _texts(root, "cac:PaymentTerms/cbc:Note", UBL_NS)
    payment = PaymentInfo(terms="\n".join(payment_terms) if payment_terms else None)
    if isinstance(payment_means, etree._Element):
        payment = PaymentInfo(
            means_code=_text(payment_means, "cbc:PaymentMeansCode", UBL_NS),
            means_text=_attribute(payment_means, "cbc:PaymentMeansCode", "name", UBL_NS),
            payment_reference=_text(payment_means, "cbc:PaymentID", UBL_NS),
            iban=_text(payment_means, "cac:PayeeFinancialAccount/cbc:ID", UBL_NS),
            account_name=_text(payment_means, "cac:PayeeFinancialAccount/cbc:Name", UBL_NS),
            terms="\n".join(payment_terms) if payment_terms else None,
        )

    tax_breakdown: list[TaxBreakdown] = []
    for subtotal in root.xpath("cac:TaxTotal/cac:TaxSubtotal", namespaces=UBL_NS):
        tax_breakdown.append(
            TaxBreakdown(
                category_code=_text(subtotal, "cac:TaxCategory/cbc:ID", UBL_NS),
                rate=_decimal(_text(subtotal, "cac:TaxCategory/cbc:Percent", UBL_NS)),
                taxable_amount=_decimal(_text(subtotal, "cbc:TaxableAmount", UBL_NS)),
                tax_amount=_decimal(_text(subtotal, "cbc:TaxAmount", UBL_NS)),
                exemption_reason=(
                    _text(subtotal, "cac:TaxCategory/cbc:TaxExemptionReason", UBL_NS)
                    or _text(subtotal, "cac:TaxCategory/cbc:TaxExemptionReasonCode", UBL_NS)
                ),
            )
        )

    monetary = _first(root, "cac:LegalMonetaryTotal", UBL_NS)
    totals = MonetaryTotals()
    if isinstance(monetary, etree._Element):
        totals = MonetaryTotals(
            line_net_total=_decimal(_text(monetary, "cbc:LineExtensionAmount", UBL_NS)),
            allowance_total=_decimal(_text(monetary, "cbc:AllowanceTotalAmount", UBL_NS)),
            charge_total=_decimal(_text(monetary, "cbc:ChargeTotalAmount", UBL_NS)),
            tax_exclusive_total=_decimal(_text(monetary, "cbc:TaxExclusiveAmount", UBL_NS)),
            tax_total=_decimal(_text(root, "cac:TaxTotal/cbc:TaxAmount", UBL_NS)),
            tax_inclusive_total=_decimal(_text(monetary, "cbc:TaxInclusiveAmount", UBL_NS)),
            prepaid_total=_decimal(_text(monetary, "cbc:PrepaidAmount", UBL_NS)),
            rounding_amount=_decimal(_text(monetary, "cbc:PayableRoundingAmount", UBL_NS)),
            payable_amount=_decimal(_text(monetary, "cbc:PayableAmount", UBL_NS)),
        )

    lines: list[InvoiceLine] = []
    for line in root.xpath(f"cac:{line_element}", namespaces=UBL_NS):
        quantity_node = _first(line, f"cbc:{quantity_element}", UBL_NS)
        quantity = None
        unit_code = None
        if isinstance(quantity_node, etree._Element):
            quantity = _decimal((quantity_node.text or "").strip())
            unit_code = quantity_node.get("unitCode")

        lines.append(
            InvoiceLine(
                line_id=_text(line, "cbc:ID", UBL_NS),
                item_name=_text(line, "cac:Item/cbc:Name", UBL_NS),
                description=_text(line, "cac:Item/cbc:Description", UBL_NS),
                seller_item_id=_text(line, "cac:Item/cac:SellersItemIdentification/cbc:ID", UBL_NS),
                buyer_item_id=_text(line, "cac:Item/cac:BuyersItemIdentification/cbc:ID", UBL_NS),
                quantity=quantity,
                unit_code=unit_code,
                unit_price=_decimal(_text(line, "cac:Price/cbc:PriceAmount", UBL_NS)),
                price_base_quantity=_decimal(_text(line, "cac:Price/cbc:BaseQuantity", UBL_NS)),
                line_net_amount=_decimal(_text(line, "cbc:LineExtensionAmount", UBL_NS)),
                tax_category_code=_text(line, "cac:Item/cac:ClassifiedTaxCategory/cbc:ID", UBL_NS),
                tax_rate=_decimal(
                    _text(line, "cac:Item/cac:ClassifiedTaxCategory/cbc:Percent", UBL_NS)
                ),
            )
        )

    document = InvoiceDocument(
        source_file=str(path),
        syntax="UBL",
        document_kind=document_kind,
        specification_id=_text(root, "cbc:CustomizationID", UBL_NS),
        business_process_id=_text(root, "cbc:ProfileID", UBL_NS),
        invoice_number=_text(root, "cbc:ID", UBL_NS),
        invoice_type_code=_text(root, f"cbc:{type_code_element}", UBL_NS),
        issue_date=_text(root, "cbc:IssueDate", UBL_NS),
        due_date=_text(root, "cbc:DueDate", UBL_NS),
        currency=_text(root, "cbc:DocumentCurrencyCode", UBL_NS),
        buyer_reference=_text(root, "cbc:BuyerReference", UBL_NS),
        order_reference=_text(root, "cac:OrderReference/cbc:ID", UBL_NS),
        contract_reference=_text(root, "cac:ContractDocumentReference/cbc:ID", UBL_NS),
        seller=_ubl_party(root, "cac:AccountingSupplierParty/cac:Party"),
        buyer=_ubl_party(root, "cac:AccountingCustomerParty/cac:Party"),
        payment=payment,
        tax_breakdown=tax_breakdown,
        totals=totals,
        lines=lines,
        notes=_texts(root, "cbc:Note", UBL_NS),
    )
    _add_basic_warnings(document)
    return document


def _cii_party(node: etree._Element | None) -> Party:
    if not isinstance(node, etree._Element):
        return Party()

    address_node = _first(node, "ram:PostalTradeAddress", CII_NAMESPACES)
    address = Address()
    if isinstance(address_node, etree._Element):
        street_parts = _texts(address_node, "ram:LineOne | ram:LineTwo | ram:LineThree", CII_NAMESPACES)
        address = Address(
            street=street_parts[0] if street_parts else None,
            additional_street=", ".join(street_parts[1:]) if len(street_parts) > 1 else None,
            city=_text(address_node, "ram:CityName", CII_NAMESPACES),
            postal_code=_text(address_node, "ram:PostcodeCode", CII_NAMESPACES),
            country_subdivision=_text(address_node, "ram:CountrySubDivisionName", CII_NAMESPACES),
            country_code=_text(address_node, "ram:CountryID", CII_NAMESPACES),
        )

    contact = _first(node, "ram:DefinedTradeContact", CII_NAMESPACES)
    return Party(
        name=_text(node, "ram:Name", CII_NAMESPACES),
        trading_name=_text(node, "ram:SpecifiedLegalOrganization/ram:TradingBusinessName", CII_NAMESPACES),
        identifier=(
            _text(node, "ram:SpecifiedLegalOrganization/ram:ID", CII_NAMESPACES)
            or _text(node, "ram:ID", CII_NAMESPACES)
            or _text(node, "ram:GlobalID", CII_NAMESPACES)
        ),
        vat_identifier=(
            _text(node, "ram:SpecifiedTaxRegistration/ram:ID[@schemeID='VA']", CII_NAMESPACES)
            or _text(node, "ram:SpecifiedTaxRegistration/ram:ID", CII_NAMESPACES)
        ),
        electronic_address=_text(
            node, "ram:URIUniversalCommunication/ram:URIID", CII_NAMESPACES
        ),
        electronic_address_scheme=_attribute(
            node,
            "ram:URIUniversalCommunication/ram:URIID",
            "schemeID",
            CII_NAMESPACES,
        ),
        contact_name=_text(contact, "ram:PersonName", CII_NAMESPACES) if isinstance(contact, etree._Element) else None,
        contact_email=_text(
            contact,
            "ram:EmailURIUniversalCommunication/ram:URIID",
            CII_NAMESPACES,
        ) if isinstance(contact, etree._Element) else None,
        contact_phone=_text(
            contact,
            "ram:TelephoneUniversalCommunication/ram:CompleteNumber",
            CII_NAMESPACES,
        ) if isinstance(contact, etree._Element) else None,
        address=address,
    )


def _parse_cii(root: etree._Element, path: Path) -> InvoiceDocument:
    transaction = _first(root, "rsm:SupplyChainTradeTransaction", CII_NAMESPACES)
    if not isinstance(transaction, etree._Element):
        raise InvalidInvoiceError("CII-Dokument enthält keine SupplyChainTradeTransaction.")

    agreement = _first(transaction, "ram:ApplicableHeaderTradeAgreement", CII_NAMESPACES)
    settlement = _first(transaction, "ram:ApplicableHeaderTradeSettlement", CII_NAMESPACES)

    seller_node = _first(agreement, "ram:SellerTradeParty", CII_NAMESPACES) if isinstance(agreement, etree._Element) else None
    buyer_node = _first(agreement, "ram:BuyerTradeParty", CII_NAMESPACES) if isinstance(agreement, etree._Element) else None

    payment_means = _first(settlement, "ram:SpecifiedTradeSettlementPaymentMeans", CII_NAMESPACES) if isinstance(settlement, etree._Element) else None
    payment_terms_nodes = settlement.xpath("ram:SpecifiedTradePaymentTerms", namespaces=CII_NAMESPACES) if isinstance(settlement, etree._Element) else []
    terms_texts: list[str] = []
    due_date = None
    for terms in payment_terms_nodes:
        terms_texts.extend(_texts(terms, "ram:Description", CII_NAMESPACES))
        due_date = due_date or _cii_date(
            terms,
            "ram:DueDateDateTime/udt:DateTimeString",
        )

    payment = PaymentInfo(terms="\n".join(terms_texts) if terms_texts else None)
    if isinstance(payment_means, etree._Element):
        payment = PaymentInfo(
            means_code=_text(payment_means, "ram:TypeCode", CII_NAMESPACES),
            means_text=_text(payment_means, "ram:Information", CII_NAMESPACES),
            payment_reference=(
                _text(settlement, "ram:PaymentReference", CII_NAMESPACES)
                if isinstance(settlement, etree._Element)
                else None
            ),
            iban=(
                _text(
                    payment_means,
                    "ram:PayeePartyCreditorFinancialAccount/ram:IBANID",
                    CII_NAMESPACES,
                )
                or _text(
                    payment_means,
                    "ram:PayeePartyCreditorFinancialAccount/ram:ProprietaryID",
                    CII_NAMESPACES,
                )
            ),
            account_name=_text(
                payment_means,
                "ram:PayeePartyCreditorFinancialAccount/ram:AccountName",
                CII_NAMESPACES,
            ),
            terms="\n".join(terms_texts) if terms_texts else None,
        )

    tax_breakdown: list[TaxBreakdown] = []
    if isinstance(settlement, etree._Element):
        for tax in settlement.xpath("ram:ApplicableTradeTax", namespaces=CII_NAMESPACES):
            tax_breakdown.append(
                TaxBreakdown(
                    category_code=_text(tax, "ram:CategoryCode", CII_NAMESPACES),
                    rate=_decimal(_text(tax, "ram:RateApplicablePercent", CII_NAMESPACES)),
                    taxable_amount=_decimal(_text(tax, "ram:BasisAmount", CII_NAMESPACES)),
                    tax_amount=_decimal(_text(tax, "ram:CalculatedAmount", CII_NAMESPACES)),
                    exemption_reason=(
                        _text(tax, "ram:ExemptionReason", CII_NAMESPACES)
                        or _text(tax, "ram:ExemptionReasonCode", CII_NAMESPACES)
                    ),
                )
            )

    summation = _first(
        settlement,
        "ram:SpecifiedTradeSettlementHeaderMonetarySummation",
        CII_NAMESPACES,
    ) if isinstance(settlement, etree._Element) else None
    totals = MonetaryTotals()
    if isinstance(summation, etree._Element):
        totals = MonetaryTotals(
            line_net_total=_decimal(_text(summation, "ram:LineTotalAmount", CII_NAMESPACES)),
            allowance_total=_decimal(_text(summation, "ram:AllowanceTotalAmount", CII_NAMESPACES)),
            charge_total=_decimal(_text(summation, "ram:ChargeTotalAmount", CII_NAMESPACES)),
            tax_exclusive_total=_decimal(_text(summation, "ram:TaxBasisTotalAmount", CII_NAMESPACES)),
            tax_total=_decimal(_text(summation, "ram:TaxTotalAmount", CII_NAMESPACES)),
            tax_inclusive_total=_decimal(_text(summation, "ram:GrandTotalAmount", CII_NAMESPACES)),
            prepaid_total=_decimal(_text(summation, "ram:TotalPrepaidAmount", CII_NAMESPACES)),
            rounding_amount=_decimal(_text(summation, "ram:RoundingAmount", CII_NAMESPACES)),
            payable_amount=_decimal(_text(summation, "ram:DuePayableAmount", CII_NAMESPACES)),
        )

    lines: list[InvoiceLine] = []
    for line in transaction.xpath("ram:IncludedSupplyChainTradeLineItem", namespaces=CII_NAMESPACES):
        quantity_node = _first(
            line,
            "ram:SpecifiedLineTradeDelivery/ram:BilledQuantity",
            CII_NAMESPACES,
        )
        quantity = None
        unit_code = None
        if isinstance(quantity_node, etree._Element):
            quantity = _decimal((quantity_node.text or "").strip())
            unit_code = quantity_node.get("unitCode")

        lines.append(
            InvoiceLine(
                line_id=_text(
                    line,
                    "ram:AssociatedDocumentLineDocument/ram:LineID",
                    CII_NAMESPACES,
                ),
                item_name=_text(line, "ram:SpecifiedTradeProduct/ram:Name", CII_NAMESPACES),
                description=_text(
                    line,
                    "ram:SpecifiedTradeProduct/ram:Description",
                    CII_NAMESPACES,
                ),
                seller_item_id=_text(
                    line,
                    "ram:SpecifiedTradeProduct/ram:SellerAssignedID",
                    CII_NAMESPACES,
                ),
                buyer_item_id=_text(
                    line,
                    "ram:SpecifiedTradeProduct/ram:BuyerAssignedID",
                    CII_NAMESPACES,
                ),
                quantity=quantity,
                unit_code=unit_code,
                unit_price=_decimal(
                    _text(
                        line,
                        "ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice/ram:ChargeAmount",
                        CII_NAMESPACES,
                    )
                ),
                price_base_quantity=_decimal(
                    _text(
                        line,
                        "ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice/ram:BasisQuantity",
                        CII_NAMESPACES,
                    )
                ),
                line_net_amount=_decimal(
                    _text(
                        line,
                        "ram:SpecifiedLineTradeSettlement/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount",
                        CII_NAMESPACES,
                    )
                ),
                tax_category_code=_text(
                    line,
                    "ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:CategoryCode",
                    CII_NAMESPACES,
                ),
                tax_rate=_decimal(
                    _text(
                        line,
                        "ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent",
                        CII_NAMESPACES,
                    )
                ),
            )
        )

    exchanged_document = _first(root, "rsm:ExchangedDocument", CII_NAMESPACES)
    context = _first(root, "rsm:ExchangedDocumentContext", CII_NAMESPACES)

    document = InvoiceDocument(
        source_file=str(path),
        syntax="CII",
        document_kind="Invoice",
        specification_id=(
            _text(
                context,
                "ram:GuidelineSpecifiedDocumentContextParameter/ram:ID",
                CII_NAMESPACES,
            )
            if isinstance(context, etree._Element)
            else None
        ),
        business_process_id=(
            _text(
                context,
                "ram:BusinessProcessSpecifiedDocumentContextParameter/ram:ID",
                CII_NAMESPACES,
            )
            if isinstance(context, etree._Element)
            else None
        ),
        invoice_number=_text(exchanged_document, "ram:ID", CII_NAMESPACES) if isinstance(exchanged_document, etree._Element) else None,
        invoice_type_code=_text(exchanged_document, "ram:TypeCode", CII_NAMESPACES) if isinstance(exchanged_document, etree._Element) else None,
        issue_date=_cii_date(
            exchanged_document,
            "ram:IssueDateTime/udt:DateTimeString",
        ) if isinstance(exchanged_document, etree._Element) else None,
        due_date=due_date,
        currency=_text(settlement, "ram:InvoiceCurrencyCode", CII_NAMESPACES) if isinstance(settlement, etree._Element) else None,
        buyer_reference=_text(agreement, "ram:BuyerReference", CII_NAMESPACES) if isinstance(agreement, etree._Element) else None,
        order_reference=_text(
            agreement,
            "ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID",
            CII_NAMESPACES,
        ) if isinstance(agreement, etree._Element) else None,
        contract_reference=_text(
            agreement,
            "ram:ContractReferencedDocument/ram:IssuerAssignedID",
            CII_NAMESPACES,
        ) if isinstance(agreement, etree._Element) else None,
        seller=_cii_party(seller_node),
        buyer=_cii_party(buyer_node),
        payment=payment,
        tax_breakdown=tax_breakdown,
        totals=totals,
        lines=lines,
        notes=_texts(
            exchanged_document,
            "ram:IncludedNote/ram:Content",
            CII_NAMESPACES,
        ) if isinstance(exchanged_document, etree._Element) else [],
    )
    _add_basic_warnings(document)
    return document


def _add_basic_warnings(document: InvoiceDocument) -> None:
    checks = [
        (document.specification_id, "Spezifikationskennung fehlt."),
        (document.invoice_number, "Rechnungsnummer fehlt."),
        (document.issue_date, "Rechnungsdatum fehlt."),
        (document.invoice_type_code, "Rechnungsart-Code fehlt."),
        (document.currency, "Währung fehlt."),
        (document.seller.name, "Name des Verkäufers fehlt."),
        (document.buyer.name, "Name des Käufers fehlt."),
        (document.totals.payable_amount, "Zahlbetrag fehlt."),
    ]
    document.warnings.extend(message for value, message in checks if value is None)

    specification_id = document.specification_id or ""
    if "en16931" not in specification_id.lower() and "xrechnung" not in specification_id.lower():
        document.warnings.append(
            "Die Spezifikationskennung weist nicht eindeutig auf EN 16931 oder XRechnung hin."
        )


def read_invoice(file_path: str | Path) -> InvoiceDocument:
    """Read a UBL or CII invoice and map it to a syntax-neutral model."""
    path = Path(file_path).expanduser().resolve()
    root = _safe_parse(path)
    syntax, document_kind = detect_syntax(root)
    if syntax == "UBL":
        return _parse_ubl(root, path, document_kind)
    return _parse_cii(root, path)


class XRechnungReader:
    """Small service class suitable for a later API/frontend integration."""

    def read(self, file_path: str | Path) -> InvoiceDocument:
        return read_invoice(file_path)
