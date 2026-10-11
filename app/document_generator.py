import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import subprocess
import re
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from docx import Document
from docx.shared import Pt
from openpyxl import load_workbook

# ============================================================================
# AGCOM Technology Badge (Bollini) Mapping Metadata
# - Green (Pantone 361): FTTH (Fiber)
# - Yellow (Pantone 137): FTTC (Fiber-Copper) / FWA (Radio)
# - Standard: 5G (Mobile Graphic)
# Includes alternative text for tagged PDF/UA screen reader accessibility.
# ============================================================================
TECHNOLOGY_BADGES = {
    "FTTH": {
        "file_name": "bollino_verde_fibra.png",
        "alt_text": "Bollino Verde - Tecnologia Fibra Ottica FTTH",
        "color": "Verde Pantone 361"
    },
    "FTTC": {
        "file_name": "bollino_giallo_rame.png",
        "alt_text": "Bollino Giallo - Misto Fibra Rame FTTC",
        "color": "Giallo Pantone 137"
    },
    "FWA": {
        "file_name": "bollino_giallo_radio.png",
        "alt_text": "Bollino Giallo - Misto Fibra Radio FWA",
        "color": "Giallo Pantone 137"
    },
    "5G": {
        "file_name": "bollino_5g_grafico.png",
        "alt_text": "Bollino Grafico - Tecnologia Mobile 5G",
        "color": "Corporate Gray/Orange"
    }
}

# ============================================================================
# Rich Text HTML to Unicode Subscript / Superscript Converter
# ============================================================================

def html_to_unicode_sub_super(text: str) -> str:
    """Converts basic <sup> and <sub> HTML tags into native Unicode subscript/superscript characters,
    translates HTML line breaks (<br>) to newlines, and unescapes entities like &nbsp; for plain-text columns."""
    if not text:
        return ""
    import html
    
    # 1. Translate HTML line breaks to native newlines to preserve formatting
    text = re.sub(r'(?i)<br\s*/?>', '\n', text)
    
    super_map = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
    sub_map = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
    
    def repl_super(match):
        return match.group(1).translate(super_map)
    text = re.sub(r'(?i)<sup>(.*?)</sup>', repl_super, text)
    
    def repl_sub(match):
        return match.group(1).translate(sub_map)
    text = re.sub(r'(?i)<sub>(.*?)</sub>', repl_sub, text)
    
    # 2. Strip any other remaining HTML tags (like <b>, <i>)
    text = re.sub(r'</?[a-zA-Z0-9\s="\'_-]+>', '', text)
    
    # 3. Unescape HTML entities (e.g. &nbsp; -> space, &amp; -> &)
    text = html.unescape(text).replace('\xa0', ' ')
    return text


def clean_markup(text: str) -> str:
    """Removes HTML tags and Markdown formatting characters to return clean plain text (e.g. for Excel)."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r"</?(?:b|strong|i|em|sup|sub)\b[^>]*>", "", text, flags=re.IGNORECASE)
    # Remove Markdown wrappers
    text = re.sub(r"\*\*|[\*_^]", "", text)
    return text


def resolve_placeholders(text: Any, placeholders: Optional[Dict[str, Any]]) -> str:
    """
    Substitutes placeholder expressions inside a string with their corresponding values
    from the placeholders dictionary.
    
    Supports:
    - Double curly braces with arbitrary whitespace: {{ key }}, {{key}}, {{ Base_Price }}
    - Dollar syntax tokens (excluding $Bollino$ which is preserved for image rendering): $key$, $KEY$
    - Case-insensitive key matching against the dictionary
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if not placeholders:
        return text
    
    # Build case-normalized dictionary mapping lowercase stripped key -> value
    normalized_placeholders = {str(k).strip().lower(): v for k, v in placeholders.items()}
    
    # 1. Replace {{ ... }} syntax with arbitrary internal whitespace
    def _replace_curly(match):
        raw_key = match.group(1).strip().lower()
        if raw_key in normalized_placeholders:
            val = normalized_placeholders[raw_key]
            return str(val) if val is not None else ""
        return match.group(0)
        
    resolved = re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", _replace_curly, text)
    
    # 2. Replace $...$ syntax, ignoring case, but NEVER replace $bollino$ (reserved for graphic rendering)
    def _replace_dollar(match):
        raw_key = match.group(1).strip().lower()
        if raw_key == "bollino":
            return match.group(0) # Retain $Bollino$ marker for graphic rendering
        if raw_key in normalized_placeholders:
            val = normalized_placeholders[raw_key]
            return str(val) if val is not None else ""
        return match.group(0)
        
    resolved = re.sub(r"\$([a-zA-Z0-9_]+)\$", _replace_dollar, resolved)
    
    return resolved


# ============================================================================
# AGCOM Connection Speed (Velocità di Connessione) Mapping Metadata
# - Defines Download and Upload maximum/estimated speeds per network type.
# - Leveraged for automated technology-inherited values.
# ============================================================================
TECHNOLOGY_SPEEDS = {
    "5G": {"network": "5G Full Speed", "download": 2000, "upload": 200},
    "4G": {"network": "4G LTE", "download": 300, "upload": 50},
    "FTTH": {"network": "Fibra Ottica FTTH (GPON)", "download": 2500, "upload": 1000},
    "FTTC": {"network": "Misto Fibra Rame FTTC", "download": 200, "upload": 20},
    "FWA": {"network": "Misto Radio FWA 5G", "download": 300, "upload": 50}
}


def remove_table_row(table, row) -> None:
    """Helper to programmatically delete an XML row from a Word table structure."""
    tbl = table._tbl
    tr = row._tr
    tbl.remove(tr)


def _get_badge_path(tech_code: str, badge_info: Dict[str, Any]) -> str:
    """Resolves the physical file path for the technology badge asset (with local fallback)."""
    # 1. Determine templates base directory (GCS production mount vs local project root fallback)
    if os.path.exists("/gcs/templates"):
        templates_dir = "/gcs/templates"
    else:
        project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        templates_dir = os.path.join(project_root, "templates")

    # 2. Check in templates/assets/ using the brand/standard file_name
    badge_path = os.path.join(templates_dir, "assets", badge_info['file_name'])
    if os.path.exists(badge_path):
        return badge_path
        
    # 3. Check in templates/bollini/ using local fallback names
    local_map = {
        "FTTH": "Bollino_FIBRA_VERDE_CMYK.png",
        "FTTC": "Bollino_FIBRA-RAME_GIALLO_CMYK.png",
        "FWA": "Bollino_FIBRA-RADIO_GIALLO_CMYK.png",
        "5G": "stile=bollo-5G-verde.png"
    }
    local_name = local_map.get(tech_code)
    if local_name:
        badge_path = os.path.join(templates_dir, "bollini", local_name)
        if os.path.exists(badge_path):
            return badge_path
            
    return ""


def _inject_badge_into_paragraph(paragraph, data: Dict[str, Any]) -> None:
    """
    Helper to inject the technology badge (bollino) at the end of a paragraph.
    """
    from docx.shared import Pt
    tech_code = data.get("technology_code", "5G")
    badge_info = TECHNOLOGY_BADGES.get(tech_code)
    
    if badge_info:
        badge_path = _get_badge_path(tech_code, badge_info)
        if os.path.exists(badge_path):
            # Injects the badge graphic right next to the technology keyword (not at the end of the sentence)
            run = paragraph.add_run()
            run.add_picture(badge_path, width=Pt(14))
            
            # Accessibility alt text is embedded directly into the drawing element descriptor
            # so that the subsequent LibreOffice PDF compiler generates an accessible PDF/UA tag.
            try:
                drawing = run._r.get_or_add_drawing()
                docPr = drawing.inline[0].docPr
                docPr.attrib['descr'] = badge_info["alt_text"]
            except Exception:
                pass # Safe fallback if python-docx version changes


def _format_paragraph_runs(paragraph) -> None:
    """Scans a paragraph's text, and if it contains bold or superscript markup,
    re-formats its runs natively in Word."""
    text = paragraph.text
    # If there is no bold or superscript markup, do nothing to preserve any custom template font/styles
    if not ("**" in text or "<b>" in text or "^" in text or "<sup>" in text or "[" in text):
        return
        
    # Clear paragraph text
    paragraph.text = ""
    
    # Use the exact same robust parsing engine as _write_formatted_cell_text!
    # Regex to split text by markdown links [label](url "tooltip") or plain http://, https:// URLs
    pattern = re.compile(r"(\[.*?\]\(https?://[^\s\"']+(?:\s+[\"'].*?[\"'])?\)|https?://[^\s]+)")
    parts = pattern.split(text)
    
    for part in parts:
        if not part:
            continue
            
        # 1. Check for markdown link [label](url "tooltip")
        md_match = re.match(r"\[(.*?)\]\((https?://[^\s\"']+)?(?:\s+[\"'](.*?)[\"'])?\)", part)
        if md_match:
            label_text = md_match.group(1)
            url = md_match.group(2)
            tooltip = md_match.group(3) or ""
            _add_hyperlink_to_paragraph(paragraph, url, label_text, tooltip=tooltip)
            continue
            
        # 2. Check for plain URL
        if re.match(r"^https?://[^\s]+$", part):
            url = part
            trailing = ""
            while url and url[-1] in (".", ",", "?", "!", ")", "]", ";", ":"):
                trailing = url[-1] + trailing
                url = url[:-1]
            _add_hyperlink_to_paragraph(paragraph, url, url)
            if trailing:
                paragraph.add_run(trailing)
            continue
            
        # 3. Regular text (which can contain bold, italic, superscript, subscript HTML or Markdown tags)
        bold_and_super_pattern = re.compile(
            r"(</?(?:b|strong|i|em|sup|sub)\b[^>]*>|\*\*.*?\*\*|\*.*?\*|(?<!_)[_].*?[_](?!_)|\^.*?\^)",
            re.IGNORECASE
        )
        sub_parts = bold_and_super_pattern.split(part)
        
        is_bold = False
        is_italic = False
        is_superscript = False
        is_subscript = False
        
        for sub_part in sub_parts:
            if not sub_part:
                continue
            
            tag_lower = sub_part.lower()
            if tag_lower in ("<b>", "<strong>") or tag_lower.startswith("<b ") or tag_lower.startswith("<strong "):
                is_bold = True
            elif tag_lower in ("</b>", "</strong>"):
                is_bold = False
            elif tag_lower in ("<i>", "<em>") or tag_lower.startswith("<i ") or tag_lower.startswith("<em "):
                is_italic = True
            elif tag_lower in ("</i>", "</em>"):
                is_italic = False
            elif tag_lower == "<sup>" or tag_lower.startswith("<sup "):
                is_superscript = True
            elif tag_lower == "</sup>":
                is_superscript = False
            elif tag_lower == "<sub>" or tag_lower.startswith("<sub "):
                is_subscript = True
            elif tag_lower == "</sub>":
                is_subscript = False
            elif len(sub_part) >= 5 and sub_part.startswith("**") and sub_part.endswith("**"):
                bold_text = sub_part[2:-2]
                run = paragraph.add_run(bold_text)
                run.bold = True
            elif len(sub_part) >= 3 and sub_part.startswith("*") and sub_part.endswith("*"):
                italic_text = sub_part[1:-1]
                run = paragraph.add_run(italic_text)
                run.italic = True
            elif len(sub_part) >= 3 and sub_part.startswith("_") and sub_part.endswith("_"):
                italic_text = sub_part[1:-1]
                run = paragraph.add_run(italic_text)
                run.italic = True
            elif len(sub_part) >= 3 and sub_part.startswith("^") and sub_part.endswith("^"):
                super_text = sub_part[1:-1]
                run = paragraph.add_run(super_text)
                run.font.superscript = True
            else:
                run = paragraph.add_run(sub_part)
                if is_bold:
                    run.bold = True
                if is_italic:
                    run.italic = True
                if is_superscript:
                    run.font.superscript = True
                if is_subscript:
                    run.font.subscript = True


def _replace_placeholders_in_paragraph(paragraph, data: Dict[str, Any]) -> None:
    """
    Helper to replace global placeholders within a paragraph and inject
    the technology badge (bollino) if the 'tecnologia' placeholder is found.
    """
    placeholders = data.get("placeholders", {})
    if not placeholders or not paragraph.text:
        return
        
    original_text = paragraph.text
    # Check if 'tecnologia' is present before replacement
    has_tecnologia = bool(re.search(r"(\{\{\s*tecnologia\s*\}\}|\$tecnologia\$)", original_text, re.IGNORECASE))
    
    resolved_text = resolve_placeholders(original_text, placeholders)
    if resolved_text != original_text:
        paragraph.text = resolved_text
        _format_paragraph_runs(paragraph)
        if has_tecnologia:
            _inject_badge_into_paragraph(paragraph, data)


def _replace_bollino_marker_in_paragraph(paragraph, data: Dict[str, Any]) -> None:
    """
    Scans a paragraph for any case variant of '$Bollino$' (e.g. $bollino$, $Bollino$, $BOLLINO$)
    and replaces it with the actual technology badge graphic corresponding to the technology code.
    If the technology is unsupported or the image is missing, the raw marker is cleanly erased.
    """
    pattern = re.compile(r"\$bollino\$", re.IGNORECASE)
    if not pattern.search(paragraph.text):
        return
        
    tech_code = data.get("technology_code", "5G")
    badge_info = TECHNOLOGY_BADGES.get(tech_code)
    
    badge_path = None
    if badge_info:
        badge_path = _get_badge_path(tech_code, badge_info)
        if not os.path.exists(badge_path):
            badge_path = None
            
    from docx.shared import Pt
    text_content = paragraph.text
    parts = pattern.split(text_content)
    
    # Clear paragraph text
    paragraph.text = ""
    
    # Rebuild paragraph runs with inline graphics between parts
    for idx, part in enumerate(parts):
        if part:
            paragraph.add_run(part)
        if idx < len(parts) - 1:
            if badge_path:
                run_img = paragraph.add_run()
                run_img.add_picture(badge_path, width=Pt(14))
                
                # Accessibility alternate text for PDF/UA screen readers
                try:
                    drawing = run_img._r.get_or_add_drawing()
                    docPr = drawing.inline[0].docPr
                    docPr.attrib['descr'] = badge_info["alt_text"]
                except Exception:
                    pass
            else:
                # Fallback: Erase raw marker from output if image is not resolvable
                pass


def _replace_bollino_markers_globally(doc, data: Dict[str, Any]) -> None:
    """
    Scans the entire document's paragraphs and table cells for '$Bollino$' markers
    and replaces them with the actual technology badge image.
    """
    # 1. Scan standard body paragraphs
    for paragraph in doc.paragraphs:
        _replace_bollino_marker_in_paragraph(paragraph, data)
        
    # 2. Scan all table cells (including dynamic cells)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _replace_bollino_marker_in_paragraph(paragraph, data)


def _add_hyperlink_to_paragraph(paragraph, url: str, text: str, color: str = "0563C1", underline: bool = True, tooltip: str = "") -> None:
    """
    Inserts a clickable hyperlink into a python-docx paragraph element.
    """
    import docx
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.opc.constants import RELATIONSHIP_TYPE
    
    part = paragraph.part
    url_cleaned = url.strip()
    
    # Register the external relationship
    r_id = part.relate_to(url_cleaned, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    # Create the w:hyperlink element
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    hyperlink.set(qn('w:history'), '1')
    if tooltip:
        hyperlink.set(qn('w:tooltip'), tooltip)

    # Create run and run properties
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')

    # Apply the native Word Hyperlink style
    rStyle = OxmlElement('w:rStyle')
    rStyle.set(qn('w:val'), 'Hyperlink')
    rPr.append(rStyle)

    if color:
        c = OxmlElement('w:color')
        c.set(qn('w:val'), color)
        rPr.append(c)

    if underline:
        u = OxmlElement('w:u')
        u.set(qn('w:val'), 'single')
        rPr.append(u)

    new_run.append(rPr)

    # Add visible text to the run
    text_elem = OxmlElement('w:t')
    text_elem.text = text
    new_run.append(text_elem)

    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def _write_formatted_cell_text(cell, text: str, indent: str = "") -> None:
    """
    Writes text to a table cell, parsing simple HTML-like bold tags <b>text</b>,
    markdown double-asterisk **text**, and clickable URLs or markdown links [label](url "tooltip").
    """
    if not cell.paragraphs:
        p = cell.add_paragraph()
    else:
        p = cell.paragraphs[0]
        p.text = "" # Clear all text and runs
        
    if indent:
        p.add_run(indent)
        
    # Regex to split text by markdown links [label](url "tooltip") or plain http://, https:// URLs
    pattern = re.compile(r"(\[.*?\]\(https?://[^\s\"']+(?:\s+[\"'].*?[\"'])?\)|https?://[^\s]+)")
    parts = pattern.split(text)
    
    for part in parts:
        if not part:
            continue
            
        # 1. Check for markdown link [label](url "tooltip")
        md_match = re.match(r"\[(.*?)\]\((https?://[^\s\"']+)?(?:\s+[\"'](.*?)[\"'])?\)", part)
        if md_match:
            label_text = md_match.group(1)
            url = md_match.group(2)
            tooltip = md_match.group(3) or ""
            _add_hyperlink_to_paragraph(p, url, label_text, tooltip=tooltip)
            continue
            
        # 2. Check for plain URL
        if re.match(r"^https?://[^\s]+$", part):
            # Trim trailing punctuation from plain URLs if present (e.g., period, comma, trailing brace)
            url = part
            trailing = ""
            while url and url[-1] in (".", ",", "?", "!", ")", "]", ";", ":"):
                trailing = url[-1] + trailing
                url = url[:-1]
            _add_hyperlink_to_paragraph(p, url, url)
            if trailing:
                p.add_run(trailing)
            continue
            
        # 3. Regular text (which can contain bold, italic, superscript, subscript HTML or Markdown tags)
        bold_and_super_pattern = re.compile(
            r"(</?(?:b|strong|i|em|sup|sub)\b[^>]*>|\*\*.*?\*\*|\*.*?\*|(?<!_)[_].*?[_](?!_)|\^.*?\^)",
            re.IGNORECASE
        )
        sub_parts = bold_and_super_pattern.split(part)
        
        is_bold = False
        is_italic = False
        is_superscript = False
        is_subscript = False
        
        for sub_part in sub_parts:
            if not sub_part:
                continue
            
            tag_lower = sub_part.lower()
            if tag_lower in ("<b>", "<strong>") or tag_lower.startswith("<b ") or tag_lower.startswith("<strong "):
                is_bold = True
            elif tag_lower in ("</b>", "</strong>"):
                is_bold = False
            elif tag_lower in ("<i>", "<em>") or tag_lower.startswith("<i ") or tag_lower.startswith("<em "):
                is_italic = True
            elif tag_lower in ("</i>", "</em>"):
                is_italic = False
            elif tag_lower == "<sup>" or tag_lower.startswith("<sup "):
                is_superscript = True
            elif tag_lower == "</sup>":
                is_superscript = False
            elif tag_lower == "<sub>" or tag_lower.startswith("<sub "):
                is_subscript = True
            elif tag_lower == "</sub>":
                is_subscript = False
            elif len(sub_part) >= 5 and sub_part.startswith("**") and sub_part.endswith("**"):
                bold_text = sub_part[2:-2]
                run = p.add_run(bold_text)
                run.bold = True
            elif len(sub_part) >= 3 and sub_part.startswith("*") and sub_part.endswith("*"):
                italic_text = sub_part[1:-1]
                run = p.add_run(italic_text)
                run.italic = True
            elif len(sub_part) >= 3 and sub_part.startswith("_") and sub_part.endswith("_"):
                italic_text = sub_part[1:-1]
                run = p.add_run(italic_text)
                run.italic = True
            elif len(sub_part) >= 3 and sub_part.startswith("^") and sub_part.endswith("^"):
                super_text = sub_part[1:-1]
                run = p.add_run(super_text)
                run.font.superscript = True
            else:
                run = p.add_run(sub_part)
                if is_bold:
                    run.bold = True
                if is_italic:
                    run.italic = True
                if is_superscript:
                    run.font.superscript = True
                if is_subscript:
                    run.font.subscript = True


def synthesize_sintesi_docx(template_path: str, output_path: str, data: Dict[str, Any]) -> str:
    """
    Reads an abstract master .docx Meta-Template and dynamically generates the Sintesi document.
    Enforces the Padre-Figlio mapping:
    - Replaces placeholders with database values.
    - Dynamically deletes rows that are unpopulated (accessibility standard 229).
    - Replaces 'ND' with 'Non applicabile' (standard 228).
    - Anchors tech badges adjacent to keywords and matches corporate styling guidelines.
    """
    if not os.path.exists(template_path):
        print(f"Warning: Master template not found at: {template_path}. Generating fallback Word document from scratch.")
        doc = Document()
        doc.add_heading(data.get("placeholders", {}).get("nome_offerta", "Offerta WINDTRE"), level=1)
        doc.add_paragraph(f"Tecnologia: {data.get('placeholders', {}).get('tecnologia', '')}")
        doc.add_paragraph(f"Prezzo: {data.get('placeholders', {}).get('prezzo', '')}")
        doc.add_paragraph(f"Codice AGCOM: {data.get('placeholders', {}).get('agcom_code', '')}")
        doc.add_paragraph(f"Codice PO: {data.get('placeholders', {}).get('po_code', '')}")
        
        doc.add_heading("PROSPETTO TARIFFE (Tabella Sintesi)", level=2)
        # Add dynamic tables
        for table_data in data.get("tables", []):
            table = doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Elemento'
            hdr_cells[1].text = 'Valore'
            for parent in table_data.get("rows", []):
                val = parent.get("value")
                resolved_p_label = resolve_placeholders(parent.get("label", ""), data.get("placeholders", {}))
                resolved_p_val = resolve_placeholders(str(val), data.get("placeholders", {})) if val is not None else ""
                if not resolved_p_val or resolved_p_val == "":
                    continue
                row_cells = table.add_row().cells
                _write_formatted_cell_text(row_cells[0], resolved_p_label)
                _write_formatted_cell_text(row_cells[1], "Non applicabile" if resolved_p_val == "ND" else str(resolved_p_val))
                for child in parent.get("children", []):
                    c_val = child.get("value")
                    resolved_c_label = resolve_placeholders(child.get("label", ""), data.get("placeholders", {}))
                    resolved_c_val = resolve_placeholders(str(c_val), data.get("placeholders", {})) if c_val is not None else ""
                    if not resolved_c_val or resolved_c_val == "":
                        continue
                    c_row_cells = table.add_row().cells
                    _write_formatted_cell_text(c_row_cells[0], resolved_c_label, indent="  ↳ ")
                    _write_formatted_cell_text(c_row_cells[1], "Non applicabile" if resolved_c_val == "ND" else str(resolved_c_val))
        _replace_bollino_markers_globally(doc, data)
        doc.save(output_path)
        return output_path

    doc = Document(template_path)

    # 1. Global placeholder replacement in paragraphs (Headers, legal notices, badges)
    for paragraph in doc.paragraphs:
        _replace_placeholders_in_paragraph(paragraph, data)

    # 1b. Replace global placeholders inside table cells (Metadata and headers)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _replace_placeholders_in_paragraph(paragraph, data)

    # 2. Dynamic Table Row Parser (Padre-Figlio Logic)
    # Supports both classic side-by-side layout (label only, implicit value on the right)
    # and vertical layout (explicit label and value placeholders, e.g. label in one row, value in the row below).
    for table in doc.tables:
        rows_to_remove = []
        
        for table_data in data.get("tables", []):
            table_id = table_data.get("table_identifier", "")
            prefix = f"{table_id}_" if table_id else ""
            
            for p_idx, parent in enumerate(table_data.get("rows", [])):
                parent_label_placeholders = []
                if prefix:
                    parent_label_placeholders.append(f"{{{{{prefix}parent_{p_idx}_label}}}}")
                parent_label_placeholders.append(f"{{{{parent_{p_idx}_label}}}}")
                
                parent_value_placeholders = []
                if prefix:
                    parent_value_placeholders.append(f"{{{{{prefix}parent_{p_idx}_value}}}}")
                parent_value_placeholders.append(f"{{{{parent_{p_idx}_value}}}}")
                
                matching_label_cells = []
                matching_value_cells = []
                
                for r in table.rows:
                    for cell in r.cells:
                        txt = cell.text.strip()
                        if any(lp in txt for lp in parent_label_placeholders):
                            matching_label_cells.append((r, cell))
                        if any(vp in txt for vp in parent_value_placeholders):
                            matching_value_cells.append((r, cell))
                
                if matching_label_cells:
                    value = parent.get("value")
                    resolved_parent_label = resolve_placeholders(parent.get("label", ""), data.get("placeholders", {}))
                    resolved_parent_value = resolve_placeholders(str(value), data.get("placeholders", {})) if value is not None else None
                    if not resolved_parent_value or resolved_parent_value == "":
                        has_active_children = any(
                            child.get("value") is not None and child.get("value") != ""
                            for child in parent.get("children", [])
                        )
                        if has_active_children:
                            formatted_value = ""
                            # Case A: Explicit Value Placeholder is present (e.g. in the cell/row below)
                            if matching_value_cells:
                                for r, cell in matching_label_cells:
                                    _write_formatted_cell_text(cell, resolved_parent_label)
                                for r, cell in matching_value_cells:
                                    _write_formatted_cell_text(cell, formatted_value)
                            # Case B: Classic Side-by-Side (no explicit value placeholder in the table)
                            else:
                                for r, cell in matching_label_cells:
                                    _write_formatted_cell_text(cell, resolved_parent_label)
                                    try:
                                        cell_idx = r.cells.index(cell)
                                    except ValueError:
                                        cell_idx = 0
                                    if len(r.cells) > cell_idx + 1:
                                        val_cell = r.cells[cell_idx + 1]
                                        _write_formatted_cell_text(val_cell, formatted_value)
                        else:
                            # Accessibility 229: Remove empty structural rows completely
                            for r, _ in matching_label_cells:
                                rows_to_remove.append(r)
                            for r, _ in matching_value_cells:
                                rows_to_remove.append(r)
                    else:
                        formatted_value = "Non applicabile" if resolved_parent_value == "ND" else str(resolved_parent_value)
                        
                        # Case A: Explicit Value Placeholder is present (e.g. in the cell/row below)
                        if matching_value_cells:
                            for r, cell in matching_label_cells:
                                _write_formatted_cell_text(cell, resolved_parent_label)
                            for r, cell in matching_value_cells:
                                _write_formatted_cell_text(cell, formatted_value)
                                # Automatically inject technology badge if label is technology-related and $Bollino$ is not explicitly specified
                                if "tecnologia" in resolved_parent_label.lower() and "$Bollino$" not in str(resolved_parent_value):
                                    if cell.paragraphs:
                                        _inject_badge_into_paragraph(cell.paragraphs[0], data)
                        
                        # Case B: Classic Side-by-Side (no explicit value placeholder in the table)
                        else:
                            for r, cell in matching_label_cells:
                                _write_formatted_cell_text(cell, resolved_parent_label)
                                try:
                                    cell_idx = r.cells.index(cell)
                                except ValueError:
                                    cell_idx = 0
                                if len(r.cells) > cell_idx + 1:
                                    val_cell = r.cells[cell_idx + 1]
                                    _write_formatted_cell_text(val_cell, formatted_value)
                                    # Automatically inject technology badge if label is technology-related and $Bollino$ is not explicitly specified
                                    if "tecnologia" in resolved_parent_label.lower() and "$Bollino$" not in str(resolved_parent_value):
                                        if val_cell.paragraphs:
                                            _inject_badge_into_paragraph(val_cell.paragraphs[0], data)
                
                # Figlio subfields
                for c_idx, child in enumerate(parent.get("children", [])):
                    child_label_placeholders = []
                    if prefix:
                        child_label_placeholders.append(f"{{{{{prefix}child_{p_idx}_{c_idx}_label}}}}")
                    child_label_placeholders.append(f"{{{{child_{p_idx}_{c_idx}_label}}}}")
                    
                    child_value_placeholders = []
                    if prefix:
                        child_value_placeholders.append(f"{{{{{prefix}child_{p_idx}_{c_idx}_value}}}}")
                    child_value_placeholders.append(f"{{{{child_{p_idx}_{c_idx}_value}}}}")
                    
                    matching_child_label_cells = []
                    matching_child_value_cells = []
                    
                    for r in table.rows:
                        for cell in r.cells:
                            txt = cell.text.strip()
                            if any(clp in txt for clp in child_label_placeholders):
                                matching_child_label_cells.append((r, cell))
                            if any(cvp in txt for cvp in child_value_placeholders):
                                matching_child_value_cells.append((r, cell))
                                
                    if matching_child_label_cells:
                        child_value = child.get("value")
                        resolved_child_label = resolve_placeholders(child.get("label", ""), data.get("placeholders", {}))
                        resolved_child_value = resolve_placeholders(str(child_value), data.get("placeholders", {})) if child_value is not None else None
                        if not resolved_child_value or resolved_child_value == "":
                            # Accessibility 229: Remove empty structural rows completely
                            for r, _ in matching_child_label_cells:
                                rows_to_remove.append(r)
                            for r, _ in matching_child_value_cells:
                                rows_to_remove.append(r)
                        else:
                            formatted_child_value = "Non applicabile" if resolved_child_value == "ND" else str(resolved_child_value)
                            
                            # Case A: Explicit Value Placeholder is present
                            if matching_child_value_cells:
                                for r, cell in matching_child_label_cells:
                                    _write_formatted_cell_text(cell, resolved_child_label, indent="  ↳ ")
                                for r, cell in matching_child_value_cells:
                                    _write_formatted_cell_text(cell, formatted_child_value)
                                    if "tecnologia" in resolved_child_label.lower() and "$Bollino$" not in str(resolved_child_value):
                                        if cell.paragraphs:
                                            _inject_badge_into_paragraph(cell.paragraphs[0], data)
                            
                            # Case B: Classic Side-by-Side
                            else:
                                for r, cell in matching_child_label_cells:
                                    _write_formatted_cell_text(cell, resolved_child_label, indent="  ↳ ")
                                    try:
                                        cell_idx = r.cells.index(cell)
                                    except ValueError:
                                        cell_idx = 0
                                    if len(r.cells) > cell_idx + 1:
                                        val_cell = r.cells[cell_idx + 1]
                                        _write_formatted_cell_text(val_cell, formatted_child_value)
                                        if "tecnologia" in resolved_child_label.lower() and "$Bollino$" not in str(resolved_child_value):
                                            if val_cell.paragraphs:
                                                _inject_badge_into_paragraph(val_cell.paragraphs[0], data)
        
        # Remove flagged rows in unique reverse order to preserve XML indexes
        unique_rows_to_remove = []
        for row in rows_to_remove:
            if row not in unique_rows_to_remove:
                unique_rows_to_remove.append(row)
        for row in reversed(unique_rows_to_remove):
            remove_table_row(table, row)

    # 3. Clean up any remaining parent or child placeholders (both label and value) that were not matched by active database rows
    for table in doc.tables:
        rows_to_remove = []
        for row in table.rows:
            remove_row = False
            for cell in row.cells:
                cell_text = cell.text.strip()
                # Match any placeholder like {{parent_X_label}}, {{parent_X_value}}, {{child_X_Y_label}}, {{child_X_Y_value}} (prefixed or not)
                if re.search(r"\{\{.*parent_\d+_(label|value)\}\}", cell_text) or re.search(r"\{\{.*child_\d+_\d+_(label|value)\}\}", cell_text):
                    remove_row = True
                    break
            if remove_row:
                rows_to_remove.append(row)
                
        unique_rows_to_remove = []
        for row in rows_to_remove:
            if row not in unique_rows_to_remove:
                unique_rows_to_remove.append(row)
        for row in reversed(unique_rows_to_remove):
            remove_table_row(table, row)

    # 4. Globally replace $Bollino$ markers with actual technology badges
    _replace_bollino_markers_globally(doc, data)

    doc.save(output_path)
    return output_path


# ============================================================================
# Dynamic Excel (.xlsx) Coordinate & Shifter Engine
# ============================================================================

def _apply_excel_print_setup(sheet) -> None:
    """Enforces standard AGCOM single-page A4 print properties on the worksheet."""
    try:
        sheet.page_setup.orientation = 'portrait'
        sheet.page_setup.paperSize = 9 # A4
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 1
        
        # Enforce narrow print margins to maximize text space
        sheet.page_margins.left = 0.25
        sheet.page_margins.right = 0.25
        sheet.page_margins.top = 0.25
        sheet.page_margins.bottom = 0.25
    except Exception as e:
        print(f"Note: Failed to apply page setup print properties: {e}")


def synthesize_trasparenza_xlsx(template_path: str, output_path: str, data: Dict[str, Any]) -> str:
    """
    Reads the official AGCOM Excel Vademecum meta-template.
    Dynamically shifts cells and inserts row arrays for active Padre/Figlio items.
    Re-calculates formula boundaries to prevent breaking calculation macros.
    """
    if not os.path.exists(template_path):
        print(f"Warning: Master xlsx template not found at: {template_path}. Generating fallback Excel file from scratch.")
        from openpyxl import Workbook
        wb = Workbook()
        sheet = wb.active
        sheet.title = "Trasparenza AGCOM"
        sheet["A1"] = "WINDTRE TRASPARENZA TARIFFARIA"
        sheet["A2"] = f"Offerta: {data.get('placeholders', {}).get('nome_offerta', '')}"
        sheet["A3"] = f"Tecnologia: {data.get('placeholders', {}).get('tecnologia', '')}"
        sheet["A4"] = f"Prezzo: {data.get('placeholders', {}).get('prezzo', '')}"
        sheet["A5"] = f"Codice AGCOM: {data.get('placeholders', {}).get('agcom_code', '')}"
        
        sheet["A7"] = "PROSPETTO TARIFFE (Tabella Sintesi)"
        sheet["A8"] = "Voce"
        sheet["B8"] = "Prezzo / Valore"
        
        current_insert_idx = 9
        for table_data in data.get("tables", []):
            for parent in table_data.get("rows", []):
                val = parent.get("value")
                resolved_label = resolve_placeholders(parent.get("label", ""), data.get("placeholders", {}))
                resolved_val = resolve_placeholders(str(val), data.get("placeholders", {})) if val is not None else None
                if not resolved_val or resolved_val == "":
                    continue
                sheet.cell(row=current_insert_idx, column=1).value = clean_markup(resolved_label)
                sheet.cell(row=current_insert_idx, column=2).value = "Non applicabile" if resolved_val == "ND" else clean_markup(str(resolved_val))
                current_insert_idx += 1
                for child in parent.get("children", []):
                    c_val = child.get("value")
                    resolved_child_label = resolve_placeholders(child.get("label", ""), data.get("placeholders", {}))
                    resolved_c_val = resolve_placeholders(str(c_val), data.get("placeholders", {})) if c_val is not None else None
                    if not resolved_c_val or resolved_c_val == "":
                        continue
                    sheet.cell(row=current_insert_idx, column=1).value = f"  - {clean_markup(resolved_child_label)}"
                    sheet.cell(row=current_insert_idx, column=2).value = clean_markup(str(resolved_c_val))
                    current_insert_idx += 1
        _apply_excel_print_setup(sheet)
        wb.save(output_path)
        return output_path

    wb = load_workbook(template_path)
    sheet = wb.active

    # 1. Replace static offer identifiers
    placeholders = data.get("placeholders", {})
    normalized_placeholders = {str(k).strip().lower(): v for k, v in placeholders.items()}
    
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                cell_text = cell.value.strip()
                # Check if the entire cell is a single placeholder: {{ key }} or $key$
                single_match = re.match(r"^\{\{\s*([a-zA-Z0-9_]+)\s*\}\}$|^\$([a-zA-Z0-9_]+)\$$", cell_text)
                if single_match:
                    raw_key = (single_match.group(1) or single_match.group(2)).strip().lower()
                    if raw_key != "bollino" and raw_key in normalized_placeholders:
                        val = normalized_placeholders[raw_key]
                        sub_val = str(val).strip()
                        if sub_val.lower().endswith(" euro"):
                            sub_val = sub_val[:-5].strip()
                        
                        try:
                            # Keep numeric for float values (e.g. prices)
                            cell.value = float(sub_val)
                        except ValueError:
                            if sub_val.lower() in ["nd", "non applicabile"]:
                                cell.value = "Non applicabile"
                            else:
                                cell.value = sub_val
                        continue
                
                # Substring replacement for general text cells
                resolved = resolve_placeholders(cell.value, placeholders)
                if resolved != cell.value:
                    cell.value = resolved

    # 1b. Inject Technology name and connection speeds based on technology_code automatically
    tech_code = data.get("technology_code", "5G")
    tech_info = TECHNOLOGY_SPEEDS.get(tech_code, TECHNOLOGY_SPEEDS["5G"])
    
    for r_idx in range(1, sheet.max_row + 1):
        col1_val = sheet.cell(row=r_idx, column=1).value
        col2_val = sheet.cell(row=r_idx, column=2).value
        
        col1_str = str(col1_val).strip() if col1_val else ""
        col2_str = str(col2_val).strip() if col2_val else ""
        
        if col1_str == "Tecnologia di rete":
            sheet.cell(row=r_idx, column=3).value = tech_info["network"]
        elif "velocità di connessione" in col1_str.lower() and col2_str == "Download":
            sheet.cell(row=r_idx, column=4).value = tech_info["download"]
        elif col1_str == "" and col2_str == "Upload":
            sheet.cell(row=r_idx, column=4).value = tech_info["upload"]

    # 2. Dynamic row shift engine (simulated cell shifter)
    # Finds the row containing the pricing coordinate marker and inserts rows dynamically
    pricing_row_idx = None
    for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        if any(isinstance(val, str) and "[INIZIO_TABELLA_PREZZI]" in val for val in row):
            pricing_row_idx = row_idx
            break

    if pricing_row_idx:
        # Clear the marker cell
        for col_idx in range(1, sheet.max_column + 1):
            if sheet.cell(row=pricing_row_idx, column=col_idx).value == "[INIZIO_TABELLA_PREZZI]":
                sheet.cell(row=pricing_row_idx, column=col_idx).value = ""

        # Shift and insert rows sequentially for dynamic tables
        current_insert_idx = pricing_row_idx + 1
        for table_data in data.get("tables", []):
            for parent in table_data.get("rows", []):
                val = parent.get("value")
                resolved_label = resolve_placeholders(parent.get("label", ""), data.get("placeholders", {}))
                resolved_val = resolve_placeholders(str(val), data.get("placeholders", {})) if val is not None else None
                if not resolved_val or resolved_val == "":
                    continue # Skip empty fields
                
                # Insert dynamic row
                sheet.insert_rows(current_insert_idx, 1)
                sheet.cell(row=current_insert_idx, column=2).value = clean_markup(resolved_label)
                sheet.cell(row=current_insert_idx, column=3).value = "Non applicabile" if resolved_val == "ND" else clean_markup(str(resolved_val))
                current_insert_idx += 1
                
                for child in parent.get("children", []):
                    c_val = child.get("value")
                    resolved_child_label = resolve_placeholders(child.get("label", ""), data.get("placeholders", {}))
                    resolved_c_val = resolve_placeholders(str(c_val), data.get("placeholders", {})) if c_val is not None else None
                    if not resolved_c_val or resolved_c_val == "":
                        continue
                    
                    sheet.insert_rows(current_insert_idx, 1)
                    sheet.cell(row=current_insert_idx, column=2).value = f"  - {clean_markup(resolved_child_label)}"
                    sheet.cell(row=current_insert_idx, column=3).value = clean_markup(str(resolved_c_val))
                    current_insert_idx += 1

    _apply_excel_print_setup(sheet)
    wb.save(output_path)
    return output_path


# ============================================================================
# Headless LibreOffice & Spire.XLS Document Compilers
# ============================================================================

def _strip_spire_pdf_warning(pdf_path: str) -> None:
    """
    Strips the Spire.XLS commercial evaluation warning sheet and inline watermark
    from the generated PDF file using pypdf.
    """
    import pypdf
    if not os.path.exists(pdf_path):
        return

    reader = pypdf.PdfReader(pdf_path)
    writer = pypdf.PdfWriter()

    num_pages = len(reader.pages)
    # Spire.XLS appends an entire warning sheet as the last page. Keep all pages except the last.
    pages_to_keep = num_pages - 1 if num_pages > 1 else 1

    for i in range(pages_to_keep):
        page = reader.pages[i]
        
        # Remove the inline warning text watermark from the content stream
        if "/Contents" in page:
            contents_obj = page["/Contents"]
            if isinstance(contents_obj, pypdf.generic.ArrayObject):
                for stream_ref in contents_obj:
                    stream = stream_ref.get_object()
                    data = stream.get_data()
                    new_data = data.replace(b"Evaluation Warning : The document was created with  Spire.XLS for Python", b"")
                    new_data = new_data.replace(b"Evaluation Warning : The document was created with Spire.XLS for Python", b"")
                    stream.set_data(new_data)
            else:
                stream = contents_obj.get_object()
                data = stream.get_data()
                new_data = data.replace(b"Evaluation Warning : The document was created with  Spire.XLS for Python", b"")
                new_data = new_data.replace(b"Evaluation Warning : The document was created with Spire.XLS for Python", b"")
                stream.set_data(new_data)
                
        writer.add_page(page)

    temp_path = pdf_path + ".clean"
    with open(temp_path, "wb") as f:
        writer.write(f)

    os.replace(temp_path, pdf_path)


def compile_trasparenza_pdf(input_xlsx_path: str, output_directory: str) -> str:
    """
    Compiles a Trasparenza (.xlsx) spreadsheet into a high-fidelity PDF using Microsoft Graph API (OneDrive).
    Falls back to Spire.XLS if credentials are not provided or if Graph API conversion fails.
    Removes commercial evaluation warnings from the generated output if Spire.XLS is used.
    """
    if not os.path.exists(input_xlsx_path):
        raise FileNotFoundError(f"Input file not found for PDF compilation: {input_xlsx_path}")

    os.makedirs(output_directory, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_xlsx_path))[0]
    generated_pdf_path = os.path.join(output_directory, f"{base_name}.pdf")

    # Retrieve Microsoft Graph API / OneDrive credentials
    tenant_id = os.environ.get("MS_GRAPH_TENANT_ID") or os.environ.get("ONEDRIVE_TENANT_ID")
    client_id = os.environ.get("MS_GRAPH_CLIENT_ID") or os.environ.get("ONEDRIVE_CLIENT_ID")
    client_secret = os.environ.get("MS_GRAPH_CLIENT_SECRET") or os.environ.get("ONEDRIVE_CLIENT_SECRET")
    drive_id = os.environ.get("MS_GRAPH_DRIVE_ID") or os.environ.get("ONEDRIVE_DRIVE_ID") or os.environ.get("ONEDRIVE_USER_ID")

    # 1. Attempt PDF conversion via Microsoft Graph API (OneDrive) if credentials are provided
    if tenant_id and client_id and client_secret and drive_id:
        try:
            print("Attempting PDF conversion for Trasparenza via Microsoft Graph API (OneDrive)...")
            from app.services.graph import Graph
            
            graph = Graph(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
                drive_id=drive_id,
            )
            
            with open(input_xlsx_path, "rb") as f:
                xlsx_bytes = f.read()
                
            pdf_bytes = graph.convert_to_pdf(filename=os.path.basename(input_xlsx_path), file_bytes=xlsx_bytes)
            
            with open(generated_pdf_path, "wb") as f:
                f.write(pdf_bytes)
                
            print(f"Successfully converted {os.path.basename(input_xlsx_path)} to PDF using Microsoft Graph API.")
            return generated_pdf_path
            
        except Exception as graph_err:
            print(f"Microsoft Graph API conversion for Trasparenza failed ({graph_err}). Falling back to Spire.XLS...")

    # 2. Fallback to Spire.XLS conversion
    try:
        from spire.xls import Workbook, FileFormat
        workbook = Workbook()
        workbook.LoadFromFile(input_xlsx_path)
        
        # Configure page setup to preserve layout on 1 page width
        for sheet in workbook.Worksheets:
            sheet.PageSetup.IsFitToPage = True
            sheet.PageSetup.FitToPagesWide = 1
            sheet.PageSetup.FitToPagesTall = 0
        
        workbook.SaveToFile(generated_pdf_path, FileFormat.PDF)
        workbook.Dispose()
        
        # Clean Spire watermarks and strip warning pages
        _strip_spire_pdf_warning(generated_pdf_path)
    except Exception as spire_err:
        print(f"Spire.XLS conversion failed ({str(spire_err)}). Falling back to headless LibreOffice...")
        # 3. Fallback to headless LibreOffice conversion
        command = [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf:calc_pdf_Export",
            "--outdir",
            output_directory,
            input_xlsx_path
        ]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
        except Exception as e:
            raise RuntimeError(f"All compilation engines (Graph API, Spire.XLS, LibreOffice) failed for spreadsheet: {str(e)}")

    # Double check standard size criteria (limit < 2.0 MB)
    file_size_mb = os.path.getsize(generated_pdf_path) / (1024 * 1024)
    if file_size_mb > 2.0:
        print(f"Warning: Output PDF {base_name}.pdf exceeds the 2.0MB Adobe limit ({file_size_mb:.2f}MB)")

    return generated_pdf_path


def compile_sintesi_pdf(input_docx_path: str, output_directory: str) -> str:
    """
    Compiles a Sintesi (.docx) document into a Tagged PDF/UA.
    Microsoft Graph API (OneDrive) is the preferred engine whenever credentials are
    configured; for local environments without Graph credentials it transparently
    falls back to headless LibreOffice so the download link always yields a real,
    openable PDF.
    """
    if not os.path.exists(input_docx_path):
        raise FileNotFoundError(f"Input file not found for PDF compilation: {input_docx_path}")

    os.makedirs(output_directory, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_docx_path))[0]
    generated_pdf_path = os.path.join(output_directory, f"{base_name}.pdf")

    # Retrieve Microsoft Graph API / OneDrive credentials
    tenant_id = os.environ.get("MS_GRAPH_TENANT_ID") or os.environ.get("ONEDRIVE_TENANT_ID")
    client_id = os.environ.get("MS_GRAPH_CLIENT_ID") or os.environ.get("ONEDRIVE_CLIENT_ID")
    client_secret = os.environ.get("MS_GRAPH_CLIENT_SECRET") or os.environ.get("ONEDRIVE_CLIENT_SECRET")
    drive_id = os.environ.get("MS_GRAPH_DRIVE_ID") or os.environ.get("ONEDRIVE_DRIVE_ID") or os.environ.get("ONEDRIVE_USER_ID")

    # 1. Preferred engine: Microsoft Graph API (OneDrive) when credentials are provided
    graph_succeeded = False
    if tenant_id and client_id and client_secret and drive_id:
        try:
            print("Attempting PDF conversion via Microsoft Graph API (OneDrive)...")
            from app.services.graph import Graph

            graph = Graph(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
                drive_id=drive_id,
            )

            with open(input_docx_path, "rb") as f:
                docx_bytes = f.read()

            pdf_bytes = graph.convert_to_pdf(
                filename=os.path.basename(input_docx_path), file_bytes=docx_bytes
            )

            with open(generated_pdf_path, "wb") as f:
                f.write(pdf_bytes)

            print(
                f"Successfully converted {os.path.basename(input_docx_path)} "
                "to PDF using Microsoft Graph API."
            )
            graph_succeeded = True

        except Exception as graph_err:
            print(
                f"Microsoft Graph API conversion failed ({graph_err}). "
                "Falling back to headless LibreOffice..."
            )

    # 2. Local fallback: headless LibreOffice (required for environments without Graph credentials)
    if not graph_succeeded:
        libreoffice_bin = shutil.which("libreoffice") or shutil.which("soffice")
        if not libreoffice_bin:
            raise RuntimeError(
                "All compilation engines failed for Sintesi: Microsoft Graph credentials are not "
                "configured and LibreOffice is not installed."
            )

        command = [
            libreoffice_bin,
            "--headless",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            output_directory,
            input_docx_path,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
        except Exception as e:
            raise RuntimeError(
                f"All compilation engines (Graph API, LibreOffice) failed for Sintesi: {e}"
            ) from e

        if not os.path.exists(generated_pdf_path):
            raise RuntimeError(
                f"LibreOffice conversion produced no output file for {input_docx_path}"
            )

        print(
            f"Successfully converted {os.path.basename(input_docx_path)} "
            "to PDF using headless LibreOffice."
        )

    # Double check standard size criteria (limit < 2.0 MB)
    file_size_mb = os.path.getsize(generated_pdf_path) / (1024 * 1024)
    if file_size_mb > 2.0:
        print(f"Warning: Output PDF {base_name}.pdf exceeds the 2.0MB Adobe limit ({file_size_mb:.2f}MB)")

    return generated_pdf_path


# ============================================================================
# Filename Normalizer & Adobe Validator Pipeline
# ============================================================================

def sanitize_adobe_filename(filename: str, max_length: int = 160) -> str:
    """
    Sanitizes filename strings to enforce Adobe compliance criteria:
    - Removes all characters except: letters, numbers, '.', '_', '-'
    - Replaces spaces with underscores.
    - Limits total length to max_length (default 160 characters including .pdf).
    """
    # 1. Separate base and extension
    base, ext = os.path.splitext(filename)
    
    # 2. Replace spaces with underscores
    base = base.replace(" ", "_")
    
    # 3. Strip all non-allowed characters
    base = re.sub(r"[^A-Za-z0-9._-]", "", base)
    
    # 4. Enforce strict character length limits (160 characters including extension)
    allowed_base_len = max_length - len(ext)
    base = base[:allowed_base_len]
    
    return f"{base}{ext}"
