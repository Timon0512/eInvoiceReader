import asyncio
from types import SimpleNamespace

import flet as ft

from xrechnung_app.app import InvoiceWindowApp
from xrechnung_app.state import AppState
from xrechnung_app.xml_view import (
    describe_xml_path,
    prepare_xml_document,
    xml_child_nodes,
    xml_node_info,
)


UBL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cbc:ID schemeID="invoice">RE-100</cbc:ID>
<cac:AccountingSupplierParty>
  <cac:Party><cac:PartyIdentification><cbc:ID>SELLER-1</cbc:ID></cac:PartyIdentification></cac:Party>
</cac:AccountingSupplierParty>
<cac:InvoiceLine><cbc:ID>7</cbc:ID><cac:Item><cbc:Name>Beratung</cbc:Name></cac:Item></cac:InvoiceLine>
<!-- Prüfhinweis -->
</Invoice>"""


CII_XML = """<rsm:CrossIndustryInvoice
 xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
 xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
<rsm:ExchangedDocument><ram:ID>RE-200</ram:ID></rsm:ExchangedDocument>
<rsm:SupplyChainTradeTransaction>
  <ram:IncludedSupplyChainTradeLineItem>
    <ram:AssociatedDocumentLineDocument><ram:LineID>3</ram:LineID></ram:AssociatedDocumentLineDocument>
  </ram:IncludedSupplyChainTradeLineItem>
</rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""


def test_ubl_tree_keeps_prefixes_attributes_values_and_comments() -> None:
    prepared = prepare_xml_document(UBL_XML)
    root = xml_node_info(prepared.root)
    children = xml_child_nodes(prepared.root)
    invoice_id = xml_node_info(children[0], root.path)
    comment = xml_node_info(children[-1], root.path)

    assert root.name == "Invoice"
    assert root.description == "Rechnung"
    assert invoice_id.name == "cbc:ID"
    assert invoice_id.description == "Rechnungsnummer"
    assert invoice_id.text == "RE-100"
    assert [(attribute.name, attribute.value) for attribute in invoice_id.attributes] == [
        ("schemeID", "invoice")
    ]
    assert comment.kind == "comment"
    assert comment.text == "Prüfhinweis"


def test_cii_tree_keeps_original_names_and_describes_context() -> None:
    prepared = prepare_xml_document(CII_XML)
    root = prepared.root
    exchanged_document = xml_child_nodes(root)[0]
    invoice_id = xml_child_nodes(exchanged_document)[0]

    root_info = xml_node_info(root)
    document_info = xml_node_info(exchanged_document, root_info.path)
    id_info = xml_node_info(invoice_id, document_info.path)

    assert root_info.name == "rsm:CrossIndustryInvoice"
    assert root_info.description == "Rechnung"
    assert document_info.description == "Rechnungsdokument"
    assert id_info.name == "ram:ID"
    assert id_info.description == "Rechnungsnummer"


def test_contextual_id_descriptions_are_distinct() -> None:
    assert describe_xml_path(("Invoice", "ID")) == "Rechnungsnummer"
    assert describe_xml_path(("Invoice", "InvoiceLine", "ID")) == "Positionsnummer"
    assert describe_xml_path(("Invoice", "OrderReference", "ID")) == "Bestellreferenz"
    assert (
        describe_xml_path(
            (
                "Invoice",
                "AccountingSupplierParty",
                "Party",
                "PartyIdentification",
                "ID",
            )
        )
        == "Verkäuferkennung"
    )
    assert describe_xml_path(("Unknown", "TechnicalTag")) is None


def test_pretty_source_is_indented_without_changing_original() -> None:
    original = '<?xml version="1.0"?><root><section><value>1</value></section></root>'
    before = original[:]
    prepared = prepare_xml_document(original)

    assert original == before
    assert prepared.formatted_source.startswith('<?xml version="1.0"?>\n<root>')
    assert "\n  <section>\n    <value>1</value>\n  </section>" in prepared.formatted_source


def test_external_entities_are_not_resolved() -> None:
    xml = (
        '<!DOCTYPE root [<!ENTITY external SYSTEM "file:///does-not-exist.txt">]>'
        "<root>&external;</root>"
    )

    prepared = prepare_xml_document(xml)
    entity = xml_child_nodes(prepared.root)[0]

    assert xml_node_info(entity, ("root",)).kind == "entity"
    assert "&external;" in prepared.formatted_source


def test_long_unknown_repeated_and_empty_elements_remain_visible() -> None:
    long_value = "x" * 5000
    prepared = prepare_xml_document(
        f"<root><TechnicalTag>{long_value}</TechnicalTag>"
        "<TechnicalTag>zweiter Wert</TechnicalTag><Empty/></root>"
    )
    children = xml_child_nodes(prepared.root)
    first = xml_node_info(children[0], ("root",))
    second = xml_node_info(children[1], ("root",))
    empty = xml_node_info(children[2], ("root",))

    assert len(children) == 3
    assert first.description is None
    assert first.text == long_value
    assert second.text == "zweiter Wert"
    assert empty.text is None


def test_xml_tree_children_are_built_lazily() -> None:
    prepared = prepare_xml_document("<root><section><value>1</value></section><leaf/></root>")
    app = InvoiceWindowApp.__new__(InvoiceWindowApp)

    root_control = app._xml_node_control(prepared.root, (), expanded=True)

    assert isinstance(root_control, ft.ExpansionTile)
    assert len(root_control.controls) == 2
    section_control = root_control.controls[0]
    assert isinstance(section_control, ft.ExpansionTile)
    assert section_control.controls == []

    section_control.update = lambda: None
    section_control.on_change(SimpleNamespace(data=True, control=section_control))

    assert len(section_control.controls) == 1


def test_comment_title_does_not_add_element_brackets() -> None:
    prepared = prepare_xml_document("<root><!-- Hinweis --></root>")
    comment = xml_child_nodes(prepared.root)[0]
    app = InvoiceWindowApp.__new__(InvoiceWindowApp)

    control = app._xml_node_control(comment, ("root",))
    title = control.content.controls[0].controls[0]

    assert title.value == "<!-- Kommentar -->"


def test_xml_tab_defaults_to_tree_and_copies_unchanged_source() -> None:
    clipboard_values: list[str] = []

    class Clipboard:
        async def set(self, value: str) -> None:
            clipboard_values.append(value)

    original = "<root><value>1</value></root>"
    app = InvoiceWindowApp.__new__(InvoiceWindowApp)
    app.state = AppState(original_xml=original)
    app.page = SimpleNamespace(
        clipboard=Clipboard(),
        show_dialog=lambda _dialog: None,
    )

    tab = app._xml_tab()
    selector = next(
        control for control in tab.content.controls if isinstance(control, ft.SegmentedButton)
    )
    copy_button = tab.content.controls[0].controls[1]

    assert selector.selected == ["tree"]
    asyncio.run(copy_button.on_click())
    assert clipboard_values == [original]
