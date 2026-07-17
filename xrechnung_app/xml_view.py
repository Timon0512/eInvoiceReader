from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from lxml import etree


XML_DECLARATION_RE: Final = re.compile(
    r"^\ufeff?\s*(<\?xml\s+[^?]*\?>)",
    re.IGNORECASE,
)
XML_NAMESPACE: Final = "http://www.w3.org/XML/1998/namespace"


@dataclass(frozen=True)
class XmlAttribute:
    name: str
    value: str


@dataclass(frozen=True)
class XmlNodeInfo:
    """Display information for one XML node without creating UI controls."""

    kind: str
    name: str
    local_name: str
    path: tuple[str, ...]
    description: str | None
    attributes: tuple[XmlAttribute, ...]
    text: str | None


@dataclass(frozen=True)
class PreparedXmlDocument:
    root: etree._Element
    formatted_source: str


SECTION_DESCRIPTIONS: Final[dict[str, str]] = {
    # UBL
    "Invoice": "Rechnung",
    "CreditNote": "Gutschrift",
    "AccountingSupplierParty": "Verkäufer",
    "AccountingCustomerParty": "Käufer",
    "PayeeParty": "Zahlungsempfänger",
    "TaxRepresentativeParty": "Steuervertreter",
    "Party": "Rechnungspartner",
    "PartyIdentification": "Kennung des Rechnungspartners",
    "PartyName": "Name des Rechnungspartners",
    "PostalAddress": "Anschrift",
    "PartyTaxScheme": "Steuerliche Angaben",
    "PartyLegalEntity": "Rechtliche Unternehmensdaten",
    "Contact": "Kontakt",
    "Delivery": "Lieferung",
    "DeliveryLocation": "Lieferort",
    "PaymentMeans": "Zahlungsart und Bankverbindung",
    "PayeeFinancialAccount": "Zahlungskonto",
    "FinancialInstitutionBranch": "Kreditinstitut",
    "PaymentTerms": "Zahlungsbedingungen",
    "AllowanceCharge": "Zu- oder Abschlag",
    "TaxTotal": "Steuer",
    "TaxSubtotal": "Steueraufschlüsselung",
    "TaxCategory": "Steuerkategorie",
    "ClassifiedTaxCategory": "Steuerkategorie der Position",
    "LegalMonetaryTotal": "Rechnungssummen",
    "InvoiceLine": "Rechnungsposition",
    "CreditNoteLine": "Gutschriftsposition",
    "Item": "Artikel oder Leistung",
    "Price": "Preis",
    "OrderReference": "Bestellreferenz",
    "ContractDocumentReference": "Vertragsreferenz",
    "BillingReference": "Referenz auf ein Abrechnungsdokument",
    "InvoiceDocumentReference": "Referenzierte Rechnung",
    "AdditionalDocumentReference": "Zusätzliches Dokument",
    # CII
    "CrossIndustryInvoice": "Rechnung",
    "ExchangedDocumentContext": "Dokumentkontext",
    "ExchangedDocument": "Rechnungsdokument",
    "SupplyChainTradeTransaction": "Geschäftsvorgang",
    "IncludedSupplyChainTradeLineItem": "Rechnungsposition",
    "AssociatedDocumentLineDocument": "Positionsreferenz",
    "SpecifiedTradeProduct": "Artikel oder Leistung",
    "SpecifiedLineTradeAgreement": "Preisvereinbarung der Position",
    "SpecifiedLineTradeDelivery": "Liefermenge der Position",
    "SpecifiedLineTradeSettlement": "Abrechnung der Position",
    "ApplicableHeaderTradeAgreement": "Vertragspartner und Referenzen",
    "ApplicableHeaderTradeDelivery": "Lieferangaben",
    "ApplicableHeaderTradeSettlement": "Zahlung, Steuern und Summen",
    "SellerTradeParty": "Verkäufer",
    "BuyerTradeParty": "Käufer",
    "ShipToTradeParty": "Lieferempfänger",
    "ApplicableTradeTax": "Steuerangaben",
    "SpecifiedTradePaymentTerms": "Zahlungsbedingungen",
    "SpecifiedTradeSettlementPaymentMeans": "Zahlungsart und Bankverbindung",
    "PayeePartyCreditorFinancialAccount": "Zahlungskonto",
    "PayeeSpecifiedCreditorFinancialInstitution": "Kreditinstitut",
    "SpecifiedTradeSettlementHeaderMonetarySummation": "Rechnungssummen",
    "SpecifiedTradeSettlementLineMonetarySummation": "Positionssumme",
    "SellerOrderReferencedDocument": "Auftragsreferenz des Verkäufers",
    "BuyerOrderReferencedDocument": "Bestellreferenz des Käufers",
    "ContractReferencedDocument": "Vertragsreferenz",
}


FIELD_DESCRIPTIONS: Final[dict[str, str]] = {
    "CustomizationID": "XRechnungs- und Profilkennung",
    "ProfileID": "Prozessprofil",
    "InvoiceTypeCode": "Rechnungsart",
    "CreditNoteTypeCode": "Gutschriftsart",
    "IssueDate": "Rechnungsdatum",
    "DueDate": "Fälligkeitsdatum",
    "TaxPointDate": "Steuerdatum",
    "Note": "Freitext oder Hinweis",
    "DocumentCurrencyCode": "Rechnungswährung",
    "InvoiceCurrencyCode": "Rechnungswährung",
    "BuyerReference": "Käuferreferenz oder Leitweg-ID",
    "InvoicedQuantity": "Abgerechnete Menge",
    "CreditedQuantity": "Gutgeschriebene Menge",
    "BilledQuantity": "Abgerechnete Menge",
    "LineExtensionAmount": "Nettobetrag der Position",
    "LineTotalAmount": "Summe der Positionen",
    "PriceAmount": "Einzelpreis",
    "ChargeAmount": "Betrag",
    "BasisQuantity": "Preisbasis-Menge",
    "TaxAmount": "Steuerbetrag",
    "TaxableAmount": "Steuerpflichtiger Betrag",
    "TaxBasisTotalAmount": "Steuerbasis",
    "TaxTotalAmount": "Gesamter Steuerbetrag",
    "Percent": "Steuersatz",
    "RateApplicablePercent": "Steuersatz",
    "CategoryCode": "Steuerkategorie",
    "TaxExclusiveAmount": "Nettobetrag",
    "TaxInclusiveAmount": "Bruttobetrag",
    "GrandTotalAmount": "Bruttobetrag",
    "AllowanceTotalAmount": "Summe der Nachlässe",
    "ChargeTotalAmount": "Summe der Zuschläge",
    "PrepaidAmount": "Bereits gezahlter Betrag",
    "TotalPrepaidAmount": "Bereits gezahlter Betrag",
    "PayableRoundingAmount": "Rundungsbetrag",
    "PayableAmount": "Zahlbetrag",
    "DuePayableAmount": "Zahlbetrag",
    "PaymentMeansCode": "Zahlungsart",
    "PaymentID": "Zahlungsreferenz",
    "InstructionID": "Zahlungsreferenz",
    "PaymentDueDate": "Fälligkeitsdatum",
    "ActualDeliveryDate": "Lieferdatum",
    "IBANID": "IBAN",
    "BICID": "BIC",
    "EndpointID": "Elektronische Adresse",
    "CompanyID": "Unternehmens- oder Steuerkennung",
    "RegistrationName": "Rechtlicher Unternehmensname",
    "StreetName": "Straße",
    "AdditionalStreetName": "Zusätzliche Adresszeile",
    "CityName": "Ort",
    "PostalZone": "Postleitzahl",
    "PostcodeCode": "Postleitzahl",
    "CountrySubentity": "Bundesland oder Region",
    "IdentificationCode": "Länderkennung",
    "Telephone": "Telefonnummer",
    "ElectronicMail": "E-Mail-Adresse",
    "LineID": "Positionsnummer",
    "Information": "Zahlungsbedingungen",
}


CONTEXT_DESCRIPTIONS: Final[tuple[tuple[tuple[str, ...], str], ...]] = (
    (("Invoice", "ID"), "Rechnungsnummer"),
    (("CreditNote", "ID"), "Gutschriftsnummer"),
    (("ExchangedDocument", "ID"), "Rechnungsnummer"),
    (("InvoiceLine", "ID"), "Positionsnummer"),
    (("CreditNoteLine", "ID"), "Positionsnummer"),
    (("OrderReference", "ID"), "Bestellreferenz"),
    (("ContractDocumentReference", "ID"), "Vertragsreferenz"),
    (("InvoiceDocumentReference", "ID"), "Referenzierte Rechnungsnummer"),
    (
        ("AccountingSupplierParty", "Party", "PartyIdentification", "ID"),
        "Verkäuferkennung",
    ),
    (
        ("AccountingCustomerParty", "Party", "PartyIdentification", "ID"),
        "Käuferkennung",
    ),
    (
        ("PartyLegalEntity", "CompanyID"),
        "Handelsregister- oder Unternehmenskennung",
    ),
    (("Item", "Name"), "Bezeichnung des Artikels oder der Leistung"),
    (("PartyName", "Name"), "Name des Rechnungspartners"),
    (("SellerTradeParty", "Name"), "Name des Verkäufers"),
    (("BuyerTradeParty", "Name"), "Name des Käufers"),
    (("ShipToTradeParty", "Name"), "Name des Lieferempfängers"),
    (
        ("SpecifiedTradeProduct", "Name"),
        "Bezeichnung des Artikels oder der Leistung",
    ),
    (("BuyerOrderReferencedDocument", "IssuerAssignedID"), "Bestellreferenz"),
    (("SellerOrderReferencedDocument", "IssuerAssignedID"), "Auftragsreferenz"),
    (("ContractReferencedDocument", "IssuerAssignedID"), "Vertragsreferenz"),
    (("IssueDateTime", "DateTimeString"), "Rechnungsdatum"),
    (("DueDateDateTime", "DateTimeString"), "Fälligkeitsdatum"),
    (
        ("BillingSpecifiedPeriod", "StartDateTime", "DateTimeString"),
        "Beginn des Abrechnungszeitraums",
    ),
    (
        ("BillingSpecifiedPeriod", "EndDateTime", "DateTimeString"),
        "Ende des Abrechnungszeitraums",
    ),
)


def prepare_xml_document(xml: str) -> PreparedXmlDocument:
    """Parse XML without external resources and create an indented representation."""

    declaration_match = XML_DECLARATION_RE.match(xml)
    declaration = declaration_match.group(1) if declaration_match else None
    parse_text = xml[declaration_match.end() :] if declaration_match else xml.lstrip("\ufeff")
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        remove_comments=False,
        remove_blank_text=True,
    )
    root = etree.fromstring(parse_text, parser=parser)
    formatted = etree.tostring(
        root.getroottree(),
        encoding="unicode",
        pretty_print=True,
    ).strip()
    if declaration and not formatted.lstrip().startswith("<?xml"):
        formatted = f"{declaration}\n{formatted}"
    return PreparedXmlDocument(root=root, formatted_source=formatted)


def format_xml_source(xml: str) -> str:
    """Return pretty-printed XML while leaving the supplied string untouched."""

    return prepare_xml_document(xml).formatted_source


def describe_xml_path(path: tuple[str, ...]) -> str | None:
    for suffix, description in CONTEXT_DESCRIPTIONS:
        if len(path) >= len(suffix) and path[-len(suffix) :] == suffix:
            return description
    if not path:
        return None
    local_name = path[-1]
    return SECTION_DESCRIPTIONS.get(local_name) or FIELD_DESCRIPTIONS.get(local_name)


def xml_node_info(node: etree._Element, parent_path: tuple[str, ...] = ()) -> XmlNodeInfo:
    if isinstance(node, etree._Comment):
        return XmlNodeInfo(
            kind="comment",
            name="<!-- Kommentar -->",
            local_name="#comment",
            path=(*parent_path, "#comment"),
            description="XML-Kommentar",
            attributes=(),
            text=_clean_text(node.text),
        )
    if isinstance(node, etree._ProcessingInstruction):
        target = getattr(node, "target", "") or "Anweisung"
        return XmlNodeInfo(
            kind="processing-instruction",
            name=f"<?{target}?>",
            local_name="#processing-instruction",
            path=(*parent_path, "#processing-instruction"),
            description="Verarbeitungsanweisung",
            attributes=(),
            text=_clean_text(node.text),
        )
    if isinstance(node, etree._Entity):
        entity_name = getattr(node, "name", "") or "entity"
        return XmlNodeInfo(
            kind="entity",
            name=f"&{entity_name};",
            local_name="#entity",
            path=(*parent_path, "#entity"),
            description="Nicht aufgelöste XML-Entität",
            attributes=(),
            text=None,
        )

    qname = etree.QName(node)
    local_name = qname.localname
    path = (*parent_path, local_name)
    name = f"{node.prefix}:{local_name}" if node.prefix else local_name
    attributes = tuple(
        XmlAttribute(_qualified_attribute_name(node, raw_name), value)
        for raw_name, value in node.attrib.items()
    )
    return XmlNodeInfo(
        kind="element",
        name=name,
        local_name=local_name,
        path=path,
        description=describe_xml_path(path),
        attributes=attributes,
        text=_clean_text(node.text),
    )


def xml_child_nodes(node: etree._Element) -> list[etree._Element]:
    """Return direct XML children; descendants are deliberately not traversed."""

    return list(node)


def _qualified_attribute_name(node: etree._Element, raw_name: str) -> str:
    qname = etree.QName(raw_name)
    if not qname.namespace:
        return qname.localname
    if qname.namespace == XML_NAMESPACE:
        return f"xml:{qname.localname}"
    for prefix, namespace in node.nsmap.items():
        if prefix and namespace == qname.namespace:
            return f"{prefix}:{qname.localname}"
    return f"{{{qname.namespace}}}{qname.localname}"


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
