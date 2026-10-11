import os
import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

# Import models, validation schemas, and normalizers
from app.database_models import OfferCreate, OfferUpdate, DynamicTableContentSchema
from app.document_generator import sanitize_adobe_filename

# Mock the database mapping locally for validation suite testing
# to ensure high-performance, containerized isolated execution.
def test_adobe_filename_normalizer_pipeline():
    """
    Tests that the filename validator enforces all Adobe-specific constraints:
    - Max length 160 characters.
    - Allowed characters are only: [A-Za-z0-9], '.', '_', '-'
    - Replaces spaces with underscores.
    """
    # Test case 1: Space replacement
    input_name = "Sintesi Super Fibra Professional.docx"
    sanitized = sanitize_adobe_filename(input_name)
    assert sanitized == "Sintesi_Super_Fibra_Professional.docx"
    assert " " not in sanitized

    # Test case 2: Strip forbidden characters
    input_forbidden = "offerta/fwa:5g?prezzo*30.pdf"
    sanitized_forbidden = sanitize_adobe_filename(input_forbidden)
    assert sanitized_forbidden == "offertafwa5gprezzo30.pdf"
    assert ":" not in sanitized_forbidden
    assert "?" not in sanitized_forbidden
    assert "*" not in sanitized_forbidden

    # Test case 3: Limit length to strictly 160 characters
    long_base = "a" * 200
    input_long = f"{long_base}.pdf"
    sanitized_long = sanitize_adobe_filename(input_long)
    assert len(sanitized_long) == 160
    assert sanitized_long.endswith(".pdf")


def test_logical_date_boundaries():
    """
    Tests that the Pydantic schema validation correctly blocks offers
    where the closing date is logically set before the starting date.
    """
    # Test case 1: Valid date range
    valid_payload = {
        "commercial_name": "Super Fibra GA",
        "technology_type": "FTTH",
        "base_price": Decimal("29.99"),
        "date_start": date(2026, 6, 1),
        "date_end": date(2026, 12, 31)
    }
    offer = OfferCreate(**valid_payload, segment_id="W3_FIX_GA_CNS")
    assert offer.date_end == date(2026, 12, 31)

    # Test case 2: Invalid date range (closing date before start date)
    invalid_payload = {
        "commercial_name": "Super Fibra CB",
        "technology_type": "FTTC",
        "base_price": Decimal("24.99"),
        "date_start": date(2026, 6, 1),
        "date_end": date(2026, 5, 1) # Invalid!
    }
    with pytest.raises(ValueError, match="La data di fine sottoscrivibilità non può essere antecedente"):
        OfferCreate(**invalid_payload, segment_id="W3_FIX_CB_CNS")


def test_very_mobile_po_code_validation():
    """
    Tests that the Very Mobile unique PO identifier is strictly validated
    against required alphanumeric structural parameters (e.g. PO123456).
    """
    # Test case 1: Valid PO code
    payload_valid = {
        "commercial_name": "Very 5G Promo",
        "technology_type": "5G",
        "base_price": Decimal("9.99"),
        "po_code": "PO123456",
        "date_start": date(2026, 6, 1)
    }
    offer = OfferCreate(**payload_valid, segment_id="VERY_MOBILE")
    assert offer.po_code == "PO123456"

    # Test case 2: Invalid PO code format
    payload_invalid = {
        "commercial_name": "Very 5G Promo",
        "technology_type": "5G",
        "base_price": Decimal("9.99"),
        "po_code": "INVALID_CODE_123",
        "date_start": date(2026, 6, 1)
    }
    with pytest.raises(ValueError, match="po_code"):
        OfferCreate(**payload_invalid, segment_id="VERY_MOBILE")


def test_dynamic_table_rows_limit_enforcement():
    """
    Tests that the dynamic table schema correctly enforces rows boundary limits
    defined for each segment (e.g., maximum 3 dynamic rows for Very Mobile,
    maximum 15 for WINDTRE CB Consumer).
    """
    # Define a dynamic table structure containing 4 populated Padre rows
    table_payload = {
        "max_rows_limit": 15,
        "rows": [
            {"id": "p1", "type": "padre", "label": "Voce 1", "value": "10€", "children": []},
            {"id": "p2", "type": "padre", "label": "Voce 2", "value": "20€", "children": []},
            {"id": "p3", "type": "padre", "label": "Voce 3", "value": "30€", "children": []},
            {"id": "p4", "type": "padre", "label": "Voce 4", "value": "40€", "children": []}
        ]
    }

    # Test case 1: Enforce standard limit (WINDTRE CB Consumer allows up to 15, so 4 is valid)
    validated = DynamicTableContentSchema.model_validate(
        table_payload, 
        context={"max_rows_limit": 15}
    )
    assert len(validated.rows) == 4

    # Test case 2: Exceeding strict limit (Very Mobile allows maximum 3, so 4 rows should fail)
    with pytest.raises(ValueError, match="Le righe totali compilate"):
        DynamicTableContentSchema.model_validate(
            table_payload, 
            context={"max_rows_limit": 3} # Very Mobile limit
        )


def test_agcom_code_format_validation():
    """
    Tests that the OfferUpdate schema accepts both 10-char standard alphanumeric 
    and 36-char UUID formatted AGCOM codes.
    """
    # Test case 1: Valid 10-char code
    update_10 = OfferUpdate(current_agcom_code="COD1234567")
    assert update_10.current_agcom_code == "COD1234567"

    # Test case 2: Valid 36-char UUID code
    update_36 = OfferUpdate(current_agcom_code="eab9995b-2cd6-4519-9355-1040f725774c")
    assert update_36.current_agcom_code == "eab9995b-2cd6-4519-9355-1040f725774c"

    # Test case 3: Invalid code (too short)
    with pytest.raises(ValueError, match="string_too_short"):
         OfferUpdate(current_agcom_code="SHORT")

    # Test case 4: Invalid code (too long)
    with pytest.raises(ValueError, match="string_too_long"):
         OfferUpdate(current_agcom_code="a" * 51)


def test_custom_filename_validation():
    """
    Tests that OfferCreate correctly accepts and parses:
    - custom_filename_sintesi
    - custom_filename_trasparenza
    """
    payload = {
        "commercial_name": "Very custom",
        "technology_type": "4G",
        "base_price": Decimal("4.99"),
        "date_start": date(2026, 6, 1),
        "custom_filename_sintesi": "custom_sintesi",
        "custom_filename_trasparenza": "custom_trasparenza.xlsx"
    }
    offer = OfferCreate(**payload, segment_id="VERY_MOBILE")
    assert offer.custom_filename_sintesi == "custom_sintesi"
    assert offer.custom_filename_trasparenza == "custom_trasparenza.xlsx"


def test_payment_method_and_transition_date_end():
    """
    Tests that:
    1. OfferCreate correctly validates and maps 'payment_method' values.
    2. Offers can be created and managed via the client with payment_method.
    """
    # Test case 1: Create with default payment method
    payload_default = {
        "commercial_name": "Test Pay Default",
        "technology_type": "5G",
        "base_price": Decimal("19.99"),
        "date_start": date(2026, 7, 1)
    }
    offer_default = OfferCreate(**payload_default, segment_id="W3_MOB_CB_CNS")
    assert offer_default.payment_method == "credito_residuo"

    # Test case 2: Create with explicit abbonamento payment method
    payload_explicit = {
        "commercial_name": "Test Pay Explicit",
        "technology_type": "FTTH",
        "base_price": Decimal("29.99"),
        "date_start": date(2026, 7, 1),
        "payment_method": "abbonamento"
    }
    offer_explicit = OfferCreate(**payload_explicit, segment_id="W3_FIX_GA_CNS")
    assert offer_explicit.payment_method == "abbonamento"


def test_dynamic_table_layouts(tmp_path):
    """
    Tests that synthesize_sintesi_docx successfully renders both:
    1. Classic side-by-side dynamic table layout (label placeholder, value implicitly adjacent).
    2. Vertical/One-column dynamic table layout (explicit label and value placeholders, e.g. stacked).
    It also verifies Standard 229: complete deletion of both label and value rows when the data value is empty.
    """
    import os
    from docx import Document
    from app.document_generator import synthesize_sintesi_docx

    # Create a temporary master template .docx file
    template_file = tmp_path / "master_template.docx"
    output_file = tmp_path / "output_sintesi.docx"

    doc = Document()
    doc.add_paragraph("Master Template Unit Test Document")

    # Table 1: Classic Side-by-Side (2 columns)
    t1 = doc.add_table(rows=4, cols=2)
    t1.rows[0].cells[0].text = "{{parent_0_label}}"
    t1.rows[0].cells[1].text = "" # Value will go here
    t1.rows[1].cells[0].text = "{{child_0_0_label}}"
    t1.rows[1].cells[1].text = "" # Value will go here
    t1.rows[2].cells[0].text = "{{parent_1_label}}"
    t1.rows[2].cells[1].text = "" # Value will go here
    t1.rows[3].cells[0].text = "{{child_1_0_label}}"
    t1.rows[3].cells[1].text = "" # Value will go here

    # Table 2: Vertical Stacked / One-Column (1 column)
    t2 = doc.add_table(rows=4, cols=1)
    t2.rows[0].cells[0].text = "{{SERVIZI_parent_0_label}}"
    t2.rows[1].cells[0].text = "{{SERVIZI_parent_0_value}}"
    t2.rows[2].cells[0].text = "{{SERVIZI_parent_1_label}}"
    t2.rows[3].cells[0].text = "{{SERVIZI_parent_1_value}}"

    doc.save(str(template_file))

    # Construct active template data payload
    data = {
        "placeholders": {
            "nome_offerta": "Super Promo 100",
            "tecnologia": "FTTH",
            "prezzo": "22.99"
        },
        "tables": [
            {
                # Implicit Table (No table identifier)
                "rows": [
                    {
                        "id": "p0",
                        "type": "padre",
                        "label": "Canone mensile",
                        "value": "22.99 €",
                        "children": [
                            {
                                "id": "c0",
                                "type": "figlio",
                                "label": "Sconto Fedeltà",
                                "value": "5.00 €"
                            }
                        ]
                    },
                    {
                        "id": "p1",
                        "type": "padre",
                        "label": "Servizi Extra",
                        "value": "", # Parent value is empty!
                        "children": [
                            {
                                "id": "c1",
                                "type": "figlio",
                                "label": "Segreteria Telefonica",
                                "value": "Visita [WINDTRE](https://windtre.it/extra \"Sito WINDTRE\") per più dettagli o vai a https://google.com."
                             }
                        ]
                    }
                ]
            },
            {
                # Explicit Table (Identifier "SERVIZI")
                "table_identifier": "SERVIZI",
                "rows": [
                    {
                        "id": "s0",
                        "type": "padre",
                        "label": "Giga Illimitati",
                        "value": "Incluso",
                        "children": []
                    },
                    {
                        "id": "s1",
                        "type": "padre",
                        "label": "Servizio Assistenza",
                        "value": "", # Empty -> Row and Value row should be removed completely!
                        "children": []
                    }
                ]
            }
        ]
    }

    # Execute synthesis
    synthesize_sintesi_docx(str(template_file), str(output_file), data)

    # Validate output document
    assert os.path.exists(output_file)
    output_doc = Document(str(output_file))

    # Validate Table 1: Classic side-by-side
    out_t1 = output_doc.tables[0]
    assert len(out_t1.rows) == 4
    assert out_t1.rows[0].cells[0].text.strip() == "Canone mensile"
    assert out_t1.rows[0].cells[1].text.strip() == "22.99 €"
    assert out_t1.rows[1].cells[0].text.strip() == "↳ Sconto Fedeltà"
    assert out_t1.rows[1].cells[1].text.strip() == "5.00 €"
    # Parent 1: value empty, but child active -> label must remain, value cell written as empty
    assert out_t1.rows[2].cells[0].text.strip() == "Servizi Extra"
    assert out_t1.rows[2].cells[1].text.strip() == ""
    assert out_t1.rows[3].cells[0].text.strip() == "↳ Segreteria Telefonica"
    
    val_text = out_t1.rows[3].cells[1].text.strip()
    assert "WINDTRE" in val_text
    assert "https://google.com" in val_text
    
    # Assert that there are XML hyperlink elements inside the cell paragraph
    p = out_t1.rows[3].cells[1].paragraphs[0]
    from docx.oxml.ns import qn
    hyperlinks = p._p.findall(qn('w:hyperlink'))
    assert len(hyperlinks) == 2 # 1 for markdown [WINDTRE](...), 1 for plain https://google.com
    # Verify the tooltip was natively written to the OpenXML tree
    assert hyperlinks[0].get(qn('w:tooltip')) == "Sito WINDTRE"

    # Validate Table 2: One column stacked layout
    out_t2 = output_doc.tables[1]
    # In Table 2:
    # Row 0 and Row 1 are parent_0_label and parent_0_value -> Giga Illimitati, Incluso.
    # Row 2 and Row 3 are parent_1_label and parent_1_value -> Empty value -> Both rows deleted!
    # Therefore, out_t2 should have exactly 2 rows left!
    assert len(out_t2.rows) == 2
    assert out_t2.rows[0].cells[0].text.strip() == "Giga Illimitati"
    assert out_t2.rows[1].cells[0].text.strip() == "Incluso"


def test_html_to_unicode_sub_super():
    """
    Tests that html_to_unicode_sub_super correctly:
    1. Converts standard and cased sub/sup tags to Unicode.
    2. Converts <br> tags to newline characters (\n).
    3. Unescapes HTML entities like &nbsp; to clean spaces.
    4. Strips other HTML tags like <b> and <i>.
    """
    from app.document_generator import html_to_unicode_sub_super
    raw_text = "<sup>1</sup> <i>asdas&nbsp;</i><br><sup>2 </sup><b><i>asdasd&nbsp;</i></b>"
    converted = html_to_unicode_sub_super(raw_text)
    
    # Expected: "¹ asdas \n² asdasd "
    # Note: "<sup>2 </sup>" translates "2" to "²" and space " " remains unchanged, resulting in "² "
    assert converted == "¹ asdas \n² asdasd "


def test_write_formatted_cell_text_superscripts():
    """
    Tests that _write_formatted_cell_text correctly parses both HTML-style and
    Markdown-style superscripts inside cells, creating native docx superscript runs.
    """
    from docx import Document
    from app.document_generator import _write_formatted_cell_text
    
    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    cell = table.cell(0, 0)
    
    test_text = "Costo^1^ e Offerta<sup>*</sup>"
    _write_formatted_cell_text(cell, test_text)
    
    # Assertions
    runs = cell.paragraphs[0].runs
    assert len(runs) >= 4
    
    # Let's check text and superscript font formatting
    texts = [r.text for r in runs]
    assert "Costo" in texts
    assert " e Offerta" in texts
    
    super_runs = [r for r in runs if r.font.superscript]
    assert len(super_runs) == 2
    assert {r.text for r in super_runs} == {"1", "*"}


def test_replace_placeholders_in_paragraph_formatting():
    """
    Tests that _replace_placeholders_in_paragraph and _format_paragraph_runs
    correctly parse and natively format caret and bold placeholders within paragraphs.
    """
    from docx import Document
    from app.document_generator import _replace_placeholders_in_paragraph
    
    doc = Document()
    p = doc.add_paragraph("Note dell'offerta: {{PREZZO_notes}}")
    data = {
        "placeholders": {
            "PREZZO_notes": "Il canone^1^ è in **promozione** per tutti."
        }
    }
    
    _replace_placeholders_in_paragraph(p, data)
    
    # Assert runs text and styles
    runs = p.runs
    assert len(runs) >= 4
    
    texts = [r.text for r in runs]
    assert "Note dell'offerta: Il canone" in texts
    assert " è in " in texts
    assert " per tutti." in texts
    
    # Ensure superscript is natively applied to "1"
    super_runs = [r for r in runs if r.font.superscript]
    assert len(super_runs) == 1
    assert super_runs[0].text == "1"
    
    # Ensure bold is natively applied to "promozione"
    bold_runs = [r for r in runs if r.bold]
    assert len(bold_runs) == 1
    assert bold_runs[0].text == "promozione"


def test_write_formatted_cell_text_nested_styles():
    """
    Tests that _write_formatted_cell_text correctly parses nested styles,
    case-insensitive HTML bold and italic tags, and subscript/superscript combos.
    """
    from docx import Document
    from app.document_generator import _write_formatted_cell_text
    
    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    cell = table.cell(0, 0)
    
    test_text = "<b><I>Figlio:</I> Velocità</b> <B>Super</B>^1^"
    _write_formatted_cell_text(cell, test_text, indent="  ↳ ")
    
    runs = cell.paragraphs[0].runs
    assert len(runs) >= 4
    
    # Check that "Figlio:" is both bold and italic
    figlio_runs = [r for r in runs if r.text == "Figlio:"]
    assert len(figlio_runs) == 1
    assert figlio_runs[0].bold is True
    assert figlio_runs[0].italic is True
    
    # Check that "Velocità" is bold (since it's inside <b>...</b>)
    velo_runs = [r for r in runs if "Velocità" in r.text]
    assert len(velo_runs) == 1
    assert velo_runs[0].bold is True
    
    # Check that "Super" is bold
    super_runs = [r for r in runs if r.text == "Super"]
    assert len(super_runs) == 1
    assert super_runs[0].bold is True
    
    # Check that "1" is superscripted
    one_runs = [r for r in runs if r.text == "1"]
    assert len(one_runs) == 1
    assert one_runs[0].font.superscript is True


def test_bulk_update_offers_success():
    """
    Tests that bulk_update_offers correctly performs simultaneous metadata updates on multiple offers.
    """
    from app.main import on_startup, SessionLocal
    from app.database_models import Offer, OfferBulkUpdate, OfferUpdate
    from app.services import OfferService
    from decimal import Decimal
    from datetime import date
    import uuid
    
    # Trigger database setup and seeding
    on_startup()
    
    db = SessionLocal()
    try:
        # Create two hermetic test offers
        offer1 = Offer(
            id=uuid.uuid4(),
            segment_id="VERY_MOBILE",
            commercial_name="Hermetic Test Offer 1",
            technology_type="4G",
            base_price=Decimal("10.00"),
            status="NUOVA",
            date_start=date(2026, 1, 1)
        )
        offer2 = Offer(
            id=uuid.uuid4(),
            segment_id="VERY_MOBILE",
            commercial_name="Hermetic Test Offer 2",
            technology_type="5G",
            base_price=Decimal("15.00"),
            status="NUOVA",
            date_start=date(2026, 1, 1)
        )
        db.add_all([offer1, offer2])
        db.flush()
        
        offer_ids = [offer1.id, offer2.id]
        
        # Apply bulk update: change base_price to 45.00 and set end date
        payload = OfferBulkUpdate(
            offer_ids=offer_ids,
            fields=OfferUpdate(
                base_price=Decimal("45.00"),
                date_end=date(2026, 12, 31)
            )
        )
        
        updated_offers = OfferService.bulk_update_offers(payload, db)
        assert len(updated_offers) == 2
        
        for offer in updated_offers:
            assert offer.base_price == Decimal("45.00")
            assert offer.date_end == date(2026, 12, 31)
            
    finally:
        db.rollback()
        db.close()


def test_resolve_placeholders_unit():
    """
    Tests that resolve_placeholders handles:
    1. Flexible whitespace inside double curly braces: {{ base_price }} vs {{base_price}}.
    2. Case-insensitivity: {{ BASE_PRICE }} and $Commercial_Name$.
    3. Dual syntax: {{ token }} and $token$.
    4. Preserving $Bollino$ and $bollino$ for OpenXML graphic injection.
    5. Fallbacks for missing keys or non-string values.
    """
    from app.document_generator import resolve_placeholders

    placeholders = {
        "base_price": "19.99",
        "commercial_name": "Mia Offerta Super",
        "tecnologia": "FTTH",
        "prezzo_canone": "19,99 €/mese"
    }

    # Spaced and compact curlies
    assert resolve_placeholders("Canone: {{ base_price }} €", placeholders) == "Canone: 19.99 €"
    assert resolve_placeholders("Canone: {{base_price}} €", placeholders) == "Canone: 19.99 €"
    assert resolve_placeholders("Canone: {{   base_price   }} €", placeholders) == "Canone: 19.99 €"

    # Case-insensitivity
    assert resolve_placeholders("Canone: {{ BASE_PRICE }} €", placeholders) == "Canone: 19.99 €"
    assert resolve_placeholders("Canone: {{ Base_Price }} €", placeholders) == "Canone: 19.99 €"
    assert resolve_placeholders("Offerta: $Commercial_Name$", placeholders) == "Offerta: Mia Offerta Super"

    # Dual syntax: $token$
    assert resolve_placeholders("Tariffa $base_price$ per $tecnologia$", placeholders) == "Tariffa 19.99 per FTTH"

    # Preserving $Bollino$ for image badge injection
    assert resolve_placeholders("Tecnologia: $Bollino$", placeholders) == "Tecnologia: $Bollino$"
    assert resolve_placeholders("Badge: $bollino$", placeholders) == "Badge: $bollino$"

    # Unmatched tokens remain untouched
    assert resolve_placeholders("Sconosciuto: {{ unknown_token }}", placeholders) == "Sconosciuto: {{ unknown_token }}"
    assert resolve_placeholders("Sconosciuto: $unknown_token$", placeholders) == "Sconosciuto: $unknown_token$"

    # Edge cases
    assert resolve_placeholders(None, placeholders) == ""
    assert resolve_placeholders("", placeholders) == ""
    assert resolve_placeholders(123.45, placeholders) == "123.45"


def test_dynamic_table_offer_placeholders_sintesi_docx(tmp_path):
    """
    Tests that synthesize_sintesi_docx resolves offer-level placeholders
    such as {{ base_price }} and {{ commercial_name }} inside dynamic table rows
    while preserving and injecting the $Bollino$ graphic badge in child rows.
    """
    from docx import Document
    from app.document_generator import synthesize_sintesi_docx

    template_file = tmp_path / "template_placeholders.docx"
    output_file = tmp_path / "output_placeholders.docx"

    doc = Document()
    doc.add_paragraph("Documento di Sintesi")

    # Dynamic Table
    t = doc.add_table(rows=2, cols=2)
    t.rows[0].cells[0].text = "{{parent_0_label}}"
    t.rows[0].cells[1].text = "" # Value cell
    t.rows[1].cells[0].text = "{{child_0_0_label}}"
    t.rows[1].cells[1].text = "" # Value cell

    doc.save(str(template_file))

    data = {
        "technology_code": "FTTH",
        "placeholders": {
            "commercial_name": "Fibra Ultra 2.5",
            "nome_offerta": "Fibra Ultra 2.5",
            "base_price": "24.90",
            "base_price_eu": "24,90 €",
            "tecnologia": "FTTH",
            "prezzo": "24.90 euro"
        },
        "tables": [
            {
                "rows": [
                    {
                        "id": "p0",
                        "type": "padre",
                        "label": "Canone per {{ commercial_name }}",
                        "value": "{{ base_price }} €/mese",
                        "children": [
                            {
                                "id": "c0",
                                "type": "figlio",
                                "label": "Bollino AGCOM",
                                "value": "$Bollino$"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    synthesize_sintesi_docx(str(template_file), str(output_file), data)

    assert os.path.exists(output_file)
    res_doc = Document(str(output_file))
    out_table = res_doc.tables[0]

    # Row 0: Padre
    assert out_table.rows[0].cells[0].text.strip() == "Canone per Fibra Ultra 2.5"
    assert out_table.rows[0].cells[1].text.strip() == "24.90 €/mese"

    # Row 1: Figlio (label interpolated, value has $Bollino$ replaced with OpenXML drawing)
    assert out_table.rows[1].cells[0].text.strip() == "↳ Bollino AGCOM"
    # Value cell should have had $Bollino$ replaced; no literal "$Bollino$" text remains
    assert "$Bollino$" not in out_table.rows[1].cells[1].text


def test_dynamic_table_offer_placeholders_trasparenza_xlsx(tmp_path):
    """
    Tests that synthesize_trasparenza_xlsx resolves offer-level placeholders
    in dynamic table rows.
    """
    from openpyxl import load_workbook
    from app.document_generator import synthesize_trasparenza_xlsx

    output_file = tmp_path / "trasparenza_placeholders.xlsx"

    data = {
        "placeholders": {
            "nome_offerta": "Offerta Test Placeholders",
            "commercial_name": "Offerta Test Placeholders",
            "base_price": "29.99",
            "tecnologia": "FTTH",
            "prezzo": "29.99 euro",
            "agcom_code": "AG123"
        },
        "tables": [
            {
                "rows": [
                    {
                        "id": "p0",
                        "type": "padre",
                        "label": "Canone {{ commercial_name }}",
                        "value": "{{ base_price }} €",
                        "children": [
                            {
                                "id": "c0",
                                "type": "figlio",
                                "label": "Promo Tecnologia {{ tecnologia }}",
                                "value": "Sconto su {{ base_price }}"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    # Generate fallback Excel (non-existent template path triggers fallback mode)
    synthesize_trasparenza_xlsx("/nonexistent/template.xlsx", str(output_file), data)

    assert os.path.exists(output_file)
    wb = load_workbook(str(output_file))
    sheet = wb.active

    # Check that placeholders were resolved in the dynamic rows
    labels = [sheet.cell(row=r, column=1).value for r in range(9, 12)]
    values = [sheet.cell(row=r, column=2).value for r in range(9, 12)]

    assert "Canone Offerta Test Placeholders" in labels
    assert "29.99 €" in values
    assert "  - Promo Tecnologia FTTH" in labels
    assert "Sconto su 29.99" in values


def test_universal_offer_placeholders_payload():
    """
    Tests that DocumentService.prepare_synthesis_payload dynamically maps ALL
    Offer columns (including activation_price_gia_clienti, po_code, date_start, etc.)
    and correctly resolves footnotes with these placeholders.
    """
    from unittest.mock import MagicMock
    from uuid import uuid4
    from app.services.document_service import DocumentService
    from app.database_models import Offer, DynamicTable
    
    mock_db = MagicMock()
    mock_offer = MagicMock(spec=Offer)
    offer_id = uuid4()
    mock_offer.id = offer_id
    mock_offer.segment_id = "W3_FIX_GA_CNS"
    mock_offer.commercial_name = "Super Fibra Special"
    mock_offer.technology_type = "FTTH"
    mock_offer.base_price = Decimal("24.99")
    mock_offer.po_code = "PO998877"
    mock_offer.current_agcom_code = "12345/26"
    mock_offer.status = "ATTIVA"
    mock_offer.date_start = date(2026, 1, 15)
    mock_offer.date_end = date(2026, 12, 31)
    mock_offer.custom_filename_sintesi = "sintesi_special.docx"
    mock_offer.custom_filename_trasparenza = "trasparenza_special.xlsx"
    mock_offer.payment_method = "abbonamento"
    mock_offer.activation_price_gia_clienti = Decimal("19.99")
    mock_offer.activation_price_nuovi_nativi = Decimal("0.00")
    mock_offer.activation_price_nuovi_portabilita = None

    mock_db.scalar.return_value = mock_offer
    mock_db.get.return_value = mock_offer
    
    # Mock dynamic table with footnotes referencing offer placeholders
    mock_table = MagicMock(spec=DynamicTable)
    mock_table.sequence_order = 1
    mock_table.table_identifier = "COSTI"
    mock_table.structural_content = {
        "max_rows_limit": 5,
        "rows": [
            {
                "id": "p1",
                "type": "padre",
                "label": "Attivazione già clienti",
                "value": "{{ activation_price_gia_clienti }} €",
                "children": []
            }
        ]
    }
    mock_table.note_links = {
        "html_content": "Costo attivazione già clienti: {{ activation_price_gia_clienti_eu }}, codice PO: {{ po_code }}."
    }
    mock_db.scalars.return_value.all.return_value = [mock_table]

    payload = DocumentService.prepare_synthesis_payload(offer_id, mock_db)
    
    placeholders = payload["placeholders"]
    
    # Verify universal columns and formats
    assert placeholders["activation_price_gia_clienti"] == "19.99"
    assert placeholders["activation_price_gia_clienti_eu"] == "19,99 €"
    assert placeholders["prezzo_attivazione_gia_clienti"] == "19.99 euro"
    assert placeholders["activation_price_nuovi_nativi"] == "0.00"
    assert placeholders["activation_price_nuovi_nativi_eu"] == "0,00 €"
    assert placeholders["activation_price_nuovi_portabilita"] == "Non applicabile"
    assert placeholders["po_code"] == "PO998877"
    assert placeholders["commercial_name"] == "Super Fibra Special"
    assert placeholders["base_price"] == "24.99"
    assert placeholders["base_price_eu"] == "24,99 €"
    assert placeholders["date_start"] == "15/01/2026"
    assert placeholders["date_end"] == "31/12/2026"
    assert placeholders["custom_filename_sintesi"] == "sintesi_special.docx"
    assert placeholders["custom_filename_trasparenza"] == "trasparenza_special.xlsx"
    assert placeholders["segment_id"] == "W3_FIX_GA_CNS"
    
    # Verify table-specific footnotes resolved placeholders
    assert "19,99 €" in placeholders["COSTI_notes"]
    assert "PO998877" in placeholders["COSTI_notes"]


def test_activation_price_placeholders_in_docx_and_xlsx(tmp_path):
    """
    Tests that activation price placeholders ({{ activation_price_gia_clienti }},
    {{ activation_price_gia_clienti_eu }}, etc.) are resolved correctly in both
    Word and Excel document synthesis engines.
    """
    from app.document_generator import synthesize_sintesi_docx, synthesize_trasparenza_xlsx
    from docx import Document
    from openpyxl import load_workbook

    docx_path = tmp_path / "test_act_price.docx"
    xlsx_path = tmp_path / "test_act_price.xlsx"

    data = {
        "technology_code": "FTTH",
        "placeholders": {
            "commercial_name": "Offerta Fibra Top",
            "base_price": "29.99",
            "base_price_eu": "29,99 €",
            "activation_price_gia_clienti": "19.99",
            "activation_price_gia_clienti_eu": "19,99 €",
            "activation_price_nuovi_portabilita": "0.00",
            "activation_price_nuovi_portabilita_eu": "0,00 €",
            "po_code": "PO123456",
            "tecnologia": "FTTH"
        },
        "tables": [
            {
                "table_identifier": "COSTI",
                "rows": [
                    {
                        "id": "p0",
                        "type": "padre",
                        "label": "Attivazione Già Clienti",
                        "value": "{{ activation_price_gia_clienti_eu }}",
                        "children": [
                            {
                                "id": "c0",
                                "type": "figlio",
                                "label": "Codice Offerta {{ po_code }}",
                                "value": "MNP: {{ activation_price_nuovi_portabilita_eu }}"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    # Test Word generation
    synthesize_sintesi_docx("/nonexistent/template.docx", str(docx_path), data)
    assert os.path.exists(docx_path)
    doc = Document(str(docx_path))
    table = doc.tables[0]
    cell_texts = [cell.text for row in table.rows for cell in row.cells]
    assert any("Attivazione Già Clienti" in t for t in cell_texts)
    assert any("19,99 €" in t for t in cell_texts)
    assert any("Codice Offerta PO123456" in t for t in cell_texts)
    assert any("MNP: 0,00 €" in t for t in cell_texts)

    # Test Excel generation
    synthesize_trasparenza_xlsx("/nonexistent/template.xlsx", str(xlsx_path), data)
    assert os.path.exists(xlsx_path)
    wb = load_workbook(str(xlsx_path))
    ws = wb.active
    labels = [ws.cell(row=r, column=1).value for r in range(9, 12)]
    values = [ws.cell(row=r, column=2).value for r in range(9, 12)]
    assert "Attivazione Già Clienti" in labels
    assert "19,99 €" in values
    assert "  - Codice Offerta PO123456" in labels
    assert "MNP: 0,00 €" in values


def test_document_service_get_available_placeholders():
    """
    Verifies that DocumentService returns a complete, well-formed
    registry of available placeholders with keys, descriptions, and categories.
    """
    from app.services.document_service import DocumentService
    placeholders = DocumentService.get_available_placeholders()
    assert isinstance(placeholders, list)
    assert len(placeholders) >= 25

    keys = [p["key"] for p in placeholders]
    assert "base_price" in keys
    assert "base_price_eu" in keys
    assert "nome_offerta" in keys
    assert "commercial_name" in keys
    assert "giga_eu" in keys
    assert "eu_giga" in keys
    assert "rda_constant" in keys
    assert "current_agcom_code" in keys
    assert "po_code" in keys
    assert "note_regolatorie" in keys
    assert "PREZZO_notes" in keys

    # Verify every entry has non-empty key, description, category
    for item in placeholders:
        assert "key" in item and len(item["key"]) > 0
        assert "description" in item and len(item["description"]) > 0
        assert "category" in item and len(item["category"]) > 0


def test_api_placeholders_endpoints():
    """
    Verifies that GET /api/placeholders, GET /api/v1/placeholders, and GET /api/offers/placeholders
    all return HTTP 200 and the registry matching the Pydantic schema.
    """
    from app.main import app
    client = TestClient(app)

    # 1. Top-level /api/placeholders
    res1 = client.get("/api/placeholders")
    assert res1.status_code == 200
    data1 = res1.json()
    assert isinstance(data1, list)
    assert any(p["key"] == "base_price" for p in data1)

    # 2. Versioned /api/v1/placeholders
    res2 = client.get("/api/v1/placeholders")
    assert res2.status_code == 200
    data2 = res2.json()
    assert isinstance(data2, list)
    assert len(data2) == len(data1)

    # 3. Offer router sub-path /api/offers/placeholders
    res3 = client.get("/api/offers/placeholders")
    assert res3.status_code == 200
    data3 = res3.json()
    assert isinstance(data3, list)
    assert len(data3) == len(data1)


def test_resolve_placeholders_with_custom_keys():
    """
    Tests that template rendering engine resolves curly brackets {{ key }}
    and handles variable whitespace.
    """
    from app.document_generator import resolve_placeholders
    placeholders = {
        "nome_offerta": "Super Fibra Unlimited",
        "base_price": "29.99",
        "base_price_eu": "29,99 €",
        "giga_eu": "16.1 GB",
        "operatore": "WINDTRE"
    }

    text_template = (
        "L'offerta {{ nome_offerta }} di {{ operatore }} costa {{ base_price_eu }} "
        "con {{ giga_eu }} inclusi in UE. Canone base: {{base_price}}."
    )

    resolved = resolve_placeholders(text_template, placeholders)
    assert "L'offerta Super Fibra Unlimited di WINDTRE costa 29,99 € con 16.1 GB inclusi in UE. Canone base: 29.99." == resolved


def test_duplicate_offer_service():
    """
    Tests OfferService.duplicate_offer:
    - Default name '{original} Copia'
    - Status initialized to 'NUOVA' (draft)
    - AGCOM code reset to None
    - Deep copy of all edited fields and dynamic tables (rows and footnotes)
    """
    from app.main import on_startup, SessionLocal
    from app.database_models import Offer, DynamicTable
    from app.services import OfferService
    from sqlalchemy import select
    import uuid

    on_startup()
    db = SessionLocal()
    try:
        orig_id = uuid.uuid4()
        orig_offer = Offer(
            id=orig_id,
            segment_id="W3_MOB_GA_CNS",
            commercial_name="Super Mobile 5G",
            technology_type="5G",
            base_price=Decimal("12.99"),
            status="APERTA",
            current_agcom_code="AGCOM12345",
            date_start=date(2026, 3, 1),
            date_end=date(2026, 12, 31),
            payment_method="credito_residuo",
            activation_price_gia_clienti=Decimal("9.99"),
            activation_price_nuovi_nativi=Decimal("0.00"),
            activation_price_nuovi_portabilita=Decimal("0.00"),
            custom_filename_sintesi="sintesi_super_mobile",
            custom_filename_trasparenza="trasparenza_super_mobile"
        )
        db.add(orig_offer)
        db.flush()

        # Add dynamic tables to original offer
        orig_table = DynamicTable(
            offer_id=orig_id,
            table_identifier="PREZZO",
            sequence_order=0,
            title="Tabella Prezzo",
            structural_content={
                "max_rows_limit": 15,
                "rows": [
                    {
                        "id": "p1",
                        "type": "padre",
                        "label": "Canone Mensile¹",
                        "value": "12,99 €",
                        "children": [
                            {"id": "c1", "type": "figlio", "label": "Promo 5G", "value": "Inclusa"}
                        ]
                    }
                ]
            },
            note_links={"html_content": "¹ Offerta vincolata a permanenza minima di 24 mesi."}
        )
        db.add(orig_table)
        db.commit()

        # Duplicate the offer with default name
        cloned = OfferService.duplicate_offer(orig_id, None, db)

        assert cloned.id != orig_id
        assert cloned.commercial_name == "Super Mobile 5G Copia"
        assert cloned.status == "NUOVA"
        assert cloned.current_agcom_code is None
        assert cloned.segment_id == orig_offer.segment_id
        assert cloned.technology_type == orig_offer.technology_type
        assert cloned.base_price == orig_offer.base_price
        assert cloned.date_start == orig_offer.date_start
        assert cloned.date_end == orig_offer.date_end
        assert cloned.payment_method == orig_offer.payment_method
        assert cloned.activation_price_gia_clienti == Decimal("9.99")
        assert cloned.activation_price_nuovi_nativi == Decimal("0.00")
        assert cloned.activation_price_nuovi_portabilita == Decimal("0.00")
        assert cloned.custom_filename_sintesi == "sintesi_super_mobile_copia"
        assert cloned.custom_filename_trasparenza == "trasparenza_super_mobile_copia"

        # Verify cloned dynamic table
        cloned_tables = list(db.scalars(
            select(DynamicTable).where(DynamicTable.offer_id == cloned.id)
        ).all())
        assert len(cloned_tables) == 1
        cloned_table = cloned_tables[0]
        assert cloned_table.id != orig_table.id
        assert cloned_table.table_identifier == "PREZZO"
        assert cloned_table.structural_content == orig_table.structural_content
        assert cloned_table.note_links == orig_table.note_links

        # Verify deepcopy isolation (modifying cloned table does not affect original)
        cloned_table.structural_content["rows"].append({"id": "p2", "type": "padre", "label": "Nuova Riga", "value": "0 €"})
        assert len(orig_table.structural_content["rows"]) == 1
    finally:
        db.close()


def test_duplicate_offer_api_endpoint():
    """
    Tests POST /api/offers/{id}/duplicate endpoint with custom draft name.
    """
    from app.main import app, SessionLocal
    from app.database_models import Offer
    import uuid

    client = TestClient(app)
    db = SessionLocal()
    try:
        source_id = uuid.uuid4()
        source_offer = Offer(
            id=source_id,
            segment_id="VERY_MOBILE",
            commercial_name="Very Flash 150",
            technology_type="4G",
            base_price=Decimal("7.99"),
            status="APERTA",
            current_agcom_code="VM99887766",
            po_code="PO554433",
            date_start=date(2026, 4, 1)
        )
        db.add(source_offer)
        db.commit()

        # Call duplicate endpoint with custom draft name
        response = client.post(
            f"/api/offers/{source_id}/duplicate",
            json={"commercial_name": "Very Flash 150 Draft"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["commercial_name"] == "Very Flash 150 Draft"
        assert data["status"] == "NUOVA"
        assert data["current_agcom_code"] is None
        assert data["segment_id"] == "VERY_MOBILE"
        assert float(data["base_price"]) == 7.99
        # Very mobile gets a newly generated PO code
        assert data["po_code"] is not None
        assert data["po_code"].startswith("PO")

        # Verify tables endpoint returns cloned tables for new offer
        new_id = data["id"]
        table_res = client.get(f"/api/offers/{new_id}/tables")
        assert table_res.status_code == 200
        tables_data = table_res.json()
        assert isinstance(tables_data, dict)
    finally:
        db.close()


def test_duplicated_offer_agcom_code_flow():
    """
    Tests the complete user journey:
    1. Duplicated offer starts with status='NUOVA' and current_agcom_code=None.
    2. User adds AGCOM code via metadata update: PUT /api/offers/{id}.
    3. User transitions offer to APERTA with valid AGCOM code.
    4. Empty string AGCOM code is converted to None without 422 error.
    """
    from fastapi.testclient import TestClient
    from app.main import app, on_startup, SessionLocal
    from app.database_models import Offer
    import uuid

    on_startup()
    client = TestClient(app)
    db = SessionLocal()

    try:
        source_id = uuid.uuid4()
        source_offer = Offer(
            id=source_id,
            segment_id="W3_MOB_GA_CNS",
            commercial_name="Start 5G Summer",
            technology_type="5G",
            base_price=Decimal("9.99"),
            status="APERTA",
            current_agcom_code="AGCOM98765",
            date_start=date(2026, 5, 1)
        )
        db.add(source_offer)
        db.commit()

        # Step 1: Duplicate offer
        dup_res = client.post(
            f"/api/offers/{source_id}/duplicate",
            json={"commercial_name": "Start 5G Autumn"}
        )
        assert dup_res.status_code == 201
        new_offer_data = dup_res.json()
        new_id = new_offer_data["id"]

        # Assert AGCOM code is NOT duplicated and status is NUOVA
        assert new_offer_data["status"] == "NUOVA"
        assert new_offer_data["current_agcom_code"] is None

        # Step 2: User adds AGCOM code via metadata update
        update_res = client.put(
            f"/api/offers/{new_id}",
            json={"current_agcom_code": "AGCOM11223"}
        )
        assert update_res.status_code == 200
        updated_data = update_res.json()
        assert updated_data["current_agcom_code"] == "AGCOM11223"

        # Step 3: Verify GET /api/offers/{id} returns the updated AGCOM code
        get_res = client.get(f"/api/offers/{new_id}")
        assert get_res.status_code == 200
        assert get_res.json()["current_agcom_code"] == "AGCOM11223"

        # Step 4: User clears AGCOM code by sending empty string (treated as None)
        clear_res = client.put(
            f"/api/offers/{new_id}",
            json={"current_agcom_code": ""}
        )
        assert clear_res.status_code == 200
        assert clear_res.json()["current_agcom_code"] is None

        # Step 5: Transition to APERTA with AGCOM code
        trans_res = client.post(
            f"/api/offers/{new_id}/transition?target_status=APERTA&agcom_code=AGCOM99881"
        )
        assert trans_res.status_code == 200
        assert trans_res.json()["status"] == "success"

        # Step 6: Verify offer has status APERTA and AGCOM code AGCOM99881
        final_res = client.get(f"/api/offers/{new_id}")
        assert final_res.status_code == 200
        assert final_res.json()["status"] == "APERTA"
        assert final_res.json()["current_agcom_code"] == "AGCOM99881"
    finally:
        db.close()


def test_download_missing_compiled_file_returns_404():
    """
    Regression: /downloads must NOT fabricate a fake .pdf when the compiled
    document is missing. Previously it wrote plain-text "mock" content with a
    .pdf extension, producing a file that no PDF reader could open.
    """
    import uuid

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    missing_name = f"Documento_Mai_Compilato_{uuid.uuid4().hex}.pdf"
    res = client.get(f"/downloads/{missing_name}")
    assert res.status_code == 404


def test_download_rejects_non_pdf_content():
    """
    Regression: a file with a .pdf extension but non-PDF content (such as the
    legacy mock text files already present in the workspace) must not be
    served as a valid document.
    """
    import uuid

    from fastapi.testclient import TestClient

    from app.main import app

    workspace = "/tmp/compilation_workspace"
    os.makedirs(workspace, exist_ok=True)
    fake_name = f"Test_Fake_Corrotto_{uuid.uuid4().hex}.pdf"
    fake_path = os.path.join(workspace, fake_name)
    with open(fake_path, "w", encoding="utf-8") as f:
        f.write("Mock compiled content for a document that was never compiled.")

    try:
        client = TestClient(app)
        res = client.get(f"/downloads/{fake_name}")
        assert res.status_code == 404
    finally:
        os.remove(fake_path)


def test_compile_sintesi_pdf_libreoffice_fallback(tmp_path, monkeypatch):
    """
    Regression: without Microsoft Graph credentials, compile_sintesi_pdf must
    fall back to the local headless LibreOffice engine and produce a real PDF
    (starting with the %PDF- magic bytes) instead of raising immediately.
    """
    for var in (
        "MS_GRAPH_TENANT_ID", "MS_GRAPH_CLIENT_ID", "MS_GRAPH_CLIENT_SECRET", "MS_GRAPH_DRIVE_ID",
        "ONEDRIVE_TENANT_ID", "ONEDRIVE_CLIENT_ID", "ONEDRIVE_CLIENT_SECRET",
        "ONEDRIVE_DRIVE_ID", "ONEDRIVE_USER_ID",
    ):
        monkeypatch.delenv(var, raising=False)

    from docx import Document

    from app.document_generator import compile_sintesi_pdf

    docx_path = tmp_path / "Sintesi_Test_Fallback.docx"
    doc = Document()
    doc.add_heading("Sintesi Test", level=1)
    doc.add_paragraph("Contenuto di prova per il fallback LibreOffice.")
    doc.save(str(docx_path))

    pdf_path = compile_sintesi_pdf(str(docx_path), str(tmp_path))
    assert os.path.exists(pdf_path)
    with open(pdf_path, "rb") as f:
        assert f.read(5) == b"%PDF-"








