from decimal import Decimal

from xrechnung_reader import read_invoice


UBL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID>
 <cbc:ID>R-100</cbc:ID><cbc:IssueDate>2026-07-16</cbc:IssueDate>
 <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode><cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
 <cac:AccountingSupplierParty><cac:Party><cac:PartyLegalEntity><cbc:RegistrationName>Seller GmbH</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingSupplierParty>
 <cac:AccountingCustomerParty><cac:Party><cac:PartyLegalEntity><cbc:RegistrationName>Buyer GmbH</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingCustomerParty>
 <cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode="H87">2</cbc:InvoicedQuantity><cbc:LineExtensionAmount currencyID="EUR">20.00</cbc:LineExtensionAmount><cac:Item><cbc:Name>Poster</cbc:Name><cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19</cbc:Percent></cac:ClassifiedTaxCategory></cac:Item><cac:Price><cbc:PriceAmount currencyID="EUR">10.00</cbc:PriceAmount></cac:Price></cac:InvoiceLine>
 <cac:LegalMonetaryTotal><cbc:LineExtensionAmount currencyID="EUR">20</cbc:LineExtensionAmount><cbc:TaxExclusiveAmount currencyID="EUR">20</cbc:TaxExclusiveAmount><cbc:TaxInclusiveAmount currencyID="EUR">23.80</cbc:TaxInclusiveAmount><cbc:PayableAmount currencyID="EUR">23.80</cbc:PayableAmount></cac:LegalMonetaryTotal>
</Invoice>"""

CII = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
 <rsm:ExchangedDocumentContext><ram:GuidelineSpecifiedDocumentContextParameter><ram:ID>urn:cen.eu:en16931:2017</ram:ID></ram:GuidelineSpecifiedDocumentContextParameter></rsm:ExchangedDocumentContext>
 <rsm:ExchangedDocument><ram:ID>R-200</ram:ID><ram:TypeCode>380</ram:TypeCode><ram:IssueDateTime><udt:DateTimeString format="102">20260716</udt:DateTimeString></ram:IssueDateTime></rsm:ExchangedDocument>
 <rsm:SupplyChainTradeTransaction>
  <ram:IncludedSupplyChainTradeLineItem><ram:AssociatedDocumentLineDocument><ram:LineID>1</ram:LineID></ram:AssociatedDocumentLineDocument><ram:SpecifiedTradeProduct><ram:Name>Poster</ram:Name></ram:SpecifiedTradeProduct><ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>10.00</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement><ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="H87">2</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery><ram:SpecifiedLineTradeSettlement><ram:ApplicableTradeTax><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>19</ram:RateApplicablePercent></ram:ApplicableTradeTax><ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>20.00</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation></ram:SpecifiedLineTradeSettlement></ram:IncludedSupplyChainTradeLineItem>
  <ram:ApplicableHeaderTradeAgreement><ram:SellerTradeParty><ram:Name>Seller GmbH</ram:Name></ram:SellerTradeParty><ram:BuyerTradeParty><ram:Name>Buyer GmbH</ram:Name></ram:BuyerTradeParty></ram:ApplicableHeaderTradeAgreement>
  <ram:ApplicableHeaderTradeDelivery/>
  <ram:ApplicableHeaderTradeSettlement><ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode><ram:SpecifiedTradeSettlementHeaderMonetarySummation><ram:LineTotalAmount>20</ram:LineTotalAmount><ram:TaxBasisTotalAmount>20</ram:TaxBasisTotalAmount><ram:GrandTotalAmount>23.80</ram:GrandTotalAmount><ram:DuePayableAmount>23.80</ram:DuePayableAmount></ram:SpecifiedTradeSettlementHeaderMonetarySummation></ram:ApplicableHeaderTradeSettlement>
 </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""


def test_reads_ubl(tmp_path):
    path = tmp_path / "invoice.xml"
    path.write_text(UBL, encoding="utf-8")
    invoice = read_invoice(path)
    assert invoice.syntax == "UBL"
    assert invoice.invoice_number == "R-100"
    assert invoice.lines[0].quantity == Decimal("2")
    assert invoice.totals.payable_amount == Decimal("23.80")


def test_reads_cii(tmp_path):
    path = tmp_path / "invoice.xml"
    path.write_text(CII, encoding="utf-8")
    invoice = read_invoice(path)
    assert invoice.syntax == "CII"
    assert invoice.invoice_number == "R-200"
    assert invoice.issue_date == "2026-07-16"
    assert invoice.lines[0].unit_price == Decimal("10.00")
