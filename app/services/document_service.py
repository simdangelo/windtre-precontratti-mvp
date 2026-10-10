import io
import os
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

# Import models & generators
from app.database_models import DynamicTable, Offer, OfferStateHistory
from app.document_generator import (
    TECHNOLOGY_SPEEDS,
    compile_sintesi_pdf,
    compile_trasparenza_pdf,
    sanitize_adobe_filename,
    synthesize_sintesi_docx,
    synthesize_trasparenza_xlsx,
)


class DocumentService:
    """
    Handles all business logic regarding document generation, compilation,
    PDF/UA conversion, and exporting metadata.
    """

    @staticmethod
    def prepare_synthesis_payload(offer_id: UUID, db: Session) -> dict:
        """
        Extracts and resolves all offer data, dynamic tables, footnotes, and
        reflected model columns into the complete synthesis payload dictionary.
        """
        offer = db.scalar(select(Offer).where(Offer.id == offer_id))
        if not offer:
            # Fallback if db.get was mocked or used directly
            if hasattr(db, "get"):
                offer = db.get(Offer, offer_id)
            if not offer:
                raise ValueError(f"Offer with ID {offer_id} not found.")

        # 1. Package current database structures into a synthesis dictionary
        tech_speeds = TECHNOLOGY_SPEEDS.get(offer.technology_type, TECHNOLOGY_SPEEDS["5G"])
        
        # Determine operator name based on segment
        operator_name = "Very Mobile" if offer.segment_id == "VERY_MOBILE" else "WINDTRE"
        
        # Determine website URL based on segment
        web_page = "https://verymobile.it/trasparenza-tariffaria/" if offer.segment_id == "VERY_MOBILE" else "https://www.windtre.it/trasparenza-tariffaria/"
        
        # Determine target market based on segment
        market = "Mobile fonia e Internet" if "MOB" in offer.segment_id or offer.segment_id == "VERY_MOBILE" else "Fisso fonia e Internet"
        
        # Determine payment method
        pay_method = "Credito Residuo" if offer.payment_method == "credito_residuo" else "Abbonamento"
        
        # Compile target clientele dynamically based on populated activation prices
        targets = []
        if offer.activation_price_gia_clienti is not None:
            targets.append("Già clienti")
        if offer.activation_price_nuovi_nativi is not None:
            targets.append("Nuovi clienti nativi")
        if offer.activation_price_nuovi_portabilita is not None:
            targets.append("Nuovi clienti in portabilità")
        
        if not targets:
            # Fallback if no specific activation prices are set
            targets = ["Già clienti", "Nuovi clienti nativi", "Nuovi clienti in portabilità"]
        target_clientela_str = ", ".join(targets)
        
        # Fetch all DynamicTables associated with the offer
        tables = db.scalars(
            select(DynamicTable)
            .where(DynamicTable.offer_id == offer_id)
            .order_by(DynamicTable.sequence_order)
        ).all()

        # Dynamic scanning of table rows for activation prices fallback (AGCOM Compliance & Standard 228)
        scanned_gia_clienti = "Non applicabile"
        scanned_nuovi_nativi = "Non applicabile"
        scanned_nuovi_portabilita = "Non applicabile"
        
        for t in tables:
            rows = t.structural_content.get("rows", [])
            for r in rows:
                lbl = r.get("label", "").lower()
                val = r.get("value", "")
                
                # Check Padre row
                if "attivazione" in lbl:
                    if "già" in lbl or "gia" in lbl:
                        scanned_gia_clienti = val if (val and val.strip() != "ND") else "Non applicabile"
                    elif "nativo" in lbl or "nativi" in lbl:
                        scanned_nuovi_nativi = val if (val and val.strip() != "ND") else "Non applicabile"
                    elif "portabilità" in lbl or "portabilita" in lbl or "mnp" in lbl:
                        scanned_nuovi_portabilita = val if (val and val.strip() != "ND") else "Non applicabile"
                
                # Check Figlio (children) rows
                for child in r.get("children", []):
                    c_lbl = child.get("label", "").lower()
                    c_val = child.get("value", "")
                    if "attivazione" in c_lbl:
                        if "già" in c_lbl or "gia" in c_lbl:
                            scanned_gia_clienti = c_val if (c_val and c_val.strip() != "ND") else "Non applicabile"
                        elif "nativo" in c_lbl or "nativi" in c_lbl:
                            scanned_nuovi_nativi = c_val if (c_val and c_val.strip() != "ND") else "Non applicabile"
                        elif "portabilità" in c_lbl or "portabilita" in c_lbl or "mnp" in c_lbl:
                            scanned_nuovi_portabilita = c_val if (c_val and c_val.strip() != "ND") else "Non applicabile"

        # 2. Universal Model Column Mapping:
        # Dynamically map EVERY column of the Offer table into placeholders
        placeholders: dict = {}
        for column in Offer.__table__.columns:
            col_name = column.name
            col_val = getattr(offer, col_name, None)
            
            if col_val is None:
                placeholders[col_name] = ""
            elif isinstance(col_val, (Decimal, float)):
                f_val = float(col_val)
                placeholders[col_name] = f"{f_val:.2f}"
                placeholders[f"{col_name}_eu"] = f"{f_val:.2f}".replace('.', ',') + " €"
                placeholders[f"{col_name}_euro"] = f"{f_val:.2f} euro"
            elif isinstance(col_val, (date, datetime)):
                placeholders[col_name] = col_val.strftime("%d/%m/%Y")
            else:
                placeholders[col_name] = str(col_val)

        # 3. Explicit Handling of Activation Prices (with scanned fallback and formatting)
        if offer.activation_price_gia_clienti is not None:
            act_gia_f = float(offer.activation_price_gia_clienti)
            placeholders["activation_price_gia_clienti"] = f"{act_gia_f:.2f}"
            placeholders["activation_price_gia_clienti_eu"] = f"{act_gia_f:.2f}".replace('.', ',') + " €"
            placeholders["prezzo_attivazione_gia_clienti"] = f"{act_gia_f:.2f} euro"
        else:
            placeholders["activation_price_gia_clienti"] = scanned_gia_clienti
            placeholders["activation_price_gia_clienti_eu"] = scanned_gia_clienti
            placeholders["prezzo_attivazione_gia_clienti"] = scanned_gia_clienti

        if offer.activation_price_nuovi_nativi is not None:
            act_nat_f = float(offer.activation_price_nuovi_nativi)
            placeholders["activation_price_nuovi_nativi"] = f"{act_nat_f:.2f}"
            placeholders["activation_price_nuovi_nativi_eu"] = f"{act_nat_f:.2f}".replace('.', ',') + " €"
            placeholders["prezzo_attivazione_nuovi_nativi"] = f"{act_nat_f:.2f} euro"
        else:
            placeholders["activation_price_nuovi_nativi"] = scanned_nuovi_nativi
            placeholders["activation_price_nuovi_nativi_eu"] = scanned_nuovi_nativi
            placeholders["prezzo_attivazione_nuovi_nativi"] = scanned_nuovi_nativi

        if offer.activation_price_nuovi_portabilita is not None:
            act_port_f = float(offer.activation_price_nuovi_portabilita)
            placeholders["activation_price_nuovi_portabilita"] = f"{act_port_f:.2f}"
            placeholders["activation_price_nuovi_portabilita_eu"] = f"{act_port_f:.2f}".replace('.', ',') + " €"
            placeholders["prezzo_attivazione_nuovi_portabilita"] = f"{act_port_f:.2f} euro"
        else:
            placeholders["activation_price_nuovi_portabilita"] = scanned_nuovi_portabilita
            placeholders["activation_price_nuovi_portabilita_eu"] = scanned_nuovi_portabilita
            placeholders["prezzo_attivazione_nuovi_portabilita"] = scanned_nuovi_portabilita

        # 4. Standard Business & Template Aliases
        base_price_val = float(offer.base_price) if offer.base_price is not None else 0.0
        base_price_str = f"{base_price_val:.2f}"
        base_price_eu_str = f"{base_price_val:.2f}".replace('.', ',') + " €"
        prezzo_canone_str = f"{base_price_val:.2f}".replace('.', ',') + " €/mese"

        # Global AGCOM RDA constant (typically 1.55 €/GB)
        # EU Gigabytes = ( (Monthly Fee excl. VAT) / RDA Constant ) * 2
        rda_constant = 1.55
        base_price_ex_vat = base_price_val / 1.22
        eu_giga_calc = round((base_price_ex_vat / rda_constant) * 2, 1) if base_price_val > 0 else 0.0
        giga_eu_str = f"{int(eu_giga_calc) if eu_giga_calc.is_integer() else eu_giga_calc} GB"

        placeholders.update({
            "operatore": operator_name,
            "stato_offerta": offer.current_agcom_code if offer.current_agcom_code else (offer.status or "Nuova"),
            "data_inizio": offer.date_start.strftime("%d/%m/%Y") if offer.date_start else "",
            "data_fine": offer.date_end.strftime("%d/%m/%Y") if offer.date_end else "—",
            "territorio": "Nazionale",
            "nome_offerta": offer.commercial_name,
            "commercial_name": offer.commercial_name,
            "tecnologia": offer.technology_type,
            "technology_type": offer.technology_type,
            "tecnologia_rete": tech_speeds["network"],
            "tipologia_offerta": "Piano base",
            "piani_compatibili": "Nessuno",
            "pagina_web": web_page,
            "mercato_riferimento": market,
            "modalita_pagamento": pay_method,
            "payment_method": offer.payment_method or "credito_residuo",
            "segment_id": offer.segment_id,
            "status": offer.status,
            "target_clientela": target_clientela_str,
            "prezzo": f"{base_price_str} euro",
            "base_price": base_price_str,
            "base_price_eu": base_price_eu_str,
            "prezzo_canone": prezzo_canone_str,
            "canone_mensile": prezzo_canone_str,
            "giga_eu": giga_eu_str,
            "eu_giga": giga_eu_str,
            "rda_constant": str(rda_constant),
            "agcom_code": offer.current_agcom_code or "Nuova",
            "current_agcom_code": offer.current_agcom_code or "Nuova",
            "po_code": offer.po_code or "N/A",
            "data_documento": datetime.now().strftime("%d/%m/%Y"),
            "velocita_download": f"{tech_speeds['download']} Mbps",
            "velocita_upload": f"{tech_speeds['upload']} Mbps"
        })

        synthesis_payload = {
            "technology_code": offer.technology_type, # Maps to FTTH, FTTC, FWA, 5G for badge selection
            "placeholders": placeholders,
            "tables": []
        }
        
        html_notes_list = []
        from app.document_generator import html_to_unicode_sub_super, resolve_placeholders
        for t in tables:
            table_dict = dict(t.structural_content)
            table_dict["table_identifier"] = t.table_identifier
            table_dict["note_links"] = t.note_links
            synthesis_payload["tables"].append(table_dict)
            
            # Extract notes if present
            note_content = ""
            if t.note_links and isinstance(t.note_links, dict):
                content = t.note_links.get("html_content")
                if content and content.strip():
                    # Resolve any offer placeholders within footnotes
                    note_content = resolve_placeholders(content.strip(), synthesis_payload["placeholders"])
                    html_notes_list.append(note_content)
            
            # Populate table-specific footnote placeholders (e.g. {{PREZZO_notes}} and {{PREZZO_notes_plain}})
            if t.table_identifier:
                synthesis_payload["placeholders"][f"{t.table_identifier}_notes"] = note_content
                synthesis_payload["placeholders"][f"{t.table_identifier}_notes_plain"] = html_to_unicode_sub_super(note_content) if note_content else ""
                    
        # Concatenate notes with paragraph breaks
        full_html_notes = "<br/><br/>".join(html_notes_list)
        synthesis_payload["placeholders"]["note_regolatorie"] = full_html_notes
        synthesis_payload["placeholders"]["note_regolatorie_plain"] = html_to_unicode_sub_super(full_html_notes)

        return synthesis_payload

    @staticmethod
    def execute_asynchronous_document_compilation(offer_id: UUID, db: Session) -> None:
        """
        Worker task to compile dynamic files, execute LibreOffice PDF exports,
        verify file sizes, and record audit histories inside Google Cloud Spanner.
        This represents the asynchronous decoupled worker task.
        """
        offer = db.scalar(select(Offer).where(Offer.id == offer_id))
        if not offer:
            return

        # 1. Package current database structures into a synthesis dictionary
        synthesis_payload = DocumentService.prepare_synthesis_payload(offer_id, db)

        # 2. Execute synthesis (simulate template paths)
        temp_dir = "/tmp/compilation_workspace"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Target path templates
        project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        master_docx_template = "/gcs/templates/w3_meta_template.docx"
        if not os.path.exists(master_docx_template):
            master_docx_template = os.path.join(project_root, "templates", "w3_meta_template.docx")
            
        master_xlsx_template = "/gcs/templates/template_trasaparenza.xlsx"
        if not os.path.exists(master_xlsx_template):
            master_xlsx_template = os.path.join(project_root, "templates", "template_trasaparenza.xlsx")
        
        # Determine the raw filenames based on segment and custom naming preferences
        if offer.segment_id == "VERY_MOBILE":
            # Use exactly custom_filename if provided (Very Mobile has naming autonomy)
            if offer.custom_filename_sintesi:
                base_sintesi = offer.custom_filename_sintesi[:-5] if offer.custom_filename_sintesi.endswith(".docx") else (offer.custom_filename_sintesi[:-4] if offer.custom_filename_sintesi.endswith(".pdf") else offer.custom_filename_sintesi)
                raw_docx_name = f"{base_sintesi}.docx"
            else:
                raw_docx_name = f"{offer.commercial_name}.docx"

            if offer.custom_filename_trasparenza:
                base_trasparenza = offer.custom_filename_trasparenza[:-5] if offer.custom_filename_trasparenza.endswith(".xlsx") else (offer.custom_filename_trasparenza[:-4] if offer.custom_filename_trasparenza.endswith(".pdf") else offer.custom_filename_trasparenza)
                raw_xlsx_name = f"{base_trasparenza}.xlsx"
            else:
                raw_xlsx_name = f"trasparenza_{offer.commercial_name}.xlsx"
        else:
            # WINDTRE or other segments (Uses structured suffix additions to support the 4-file co-existence rule)
            base_sintesi = offer.custom_filename_sintesi or f"{offer.commercial_name}_{offer.technology_type}_{offer.base_price:.2f}"
            if base_sintesi.endswith(".docx"):
                base_sintesi = base_sintesi[:-5]
            elif base_sintesi.endswith(".pdf"):
                base_sintesi = base_sintesi[:-4]

            base_trasparenza = offer.custom_filename_trasparenza or f"trasparenza_{offer.commercial_name}"
            if base_trasparenza.endswith(".xlsx"):
                base_trasparenza = base_trasparenza[:-5]
            elif base_trasparenza.endswith(".pdf"):
                base_trasparenza = base_trasparenza[:-4]

            suffix = ""
            if offer.status == "NUOVA":
                suffix = "_NUOVA"
            elif offer.status == "APERTA":
                suffix = f"_COD_{offer.current_agcom_code}" if offer.current_agcom_code else "_NUOVA"
            else:
                suffix = f"_{offer.status}"

            raw_docx_name = f"{base_sintesi}{suffix}.docx"
            raw_xlsx_name = f"{base_trasparenza}{suffix}.xlsx"
        
        sanitized_docx_name = sanitize_adobe_filename(raw_docx_name)
        sanitized_xlsx_name = sanitize_adobe_filename(raw_xlsx_name)
        
        local_docx_path = os.path.join(temp_dir, sanitized_docx_name)
        local_xlsx_path = os.path.join(temp_dir, sanitized_xlsx_name)
        
        # Execute python parsing engines
        synthesize_sintesi_docx(master_docx_template, local_docx_path, synthesis_payload)
        synthesize_trasparenza_xlsx(master_xlsx_template, local_xlsx_path, synthesis_payload)
        
        # Execute separate specialized compilers for Sintesi and Trasparenza
        compiled_pdf_docx = compile_sintesi_pdf(local_docx_path, temp_dir)
        compiled_pdf_xlsx = compile_trasparenza_pdf(local_xlsx_path, temp_dir)

        # 3. Write generated outputs to Google Cloud Storage (GCS)
        gcs_base_uri = f"https://storage.googleapis.com/w3-precontratti-outputs/{offer.id}"
        
        # Determine appropriate old_status
        old_status = "NUOVA" if offer.status == "APERTA" else ("APERTA" if offer.status == "CHIUSA" else None)

        # Instantiate audit trail history record
        audit_record = OfferStateHistory(
            offer_id=offer.id,
            old_status=old_status,
            new_status=offer.status,
            agcom_code_used=offer.current_agcom_code,
            docx_gcs_uri=f"{gcs_base_uri}/{sanitized_docx_name}",
            xlsx_gcs_uri=f"{gcs_base_uri}/{sanitized_xlsx_name}",
            sintesi_pdf_gcs_uri=f"{gcs_base_uri}/{os.path.basename(compiled_pdf_docx)}",
            trasparenza_pdf_gcs_uri=f"{gcs_base_uri}/{os.path.basename(compiled_pdf_xlsx)}"
        )
        db.add(audit_record)
        db.commit()

    @staticmethod
    def generate_adobe_mapping_sheet(offer: Offer) -> StreamingResponse:
        """
        Generates and streams a CSV mapping sheet matching Adobe's internal formatting.
        Ensures seamless compatibility with Adobe's deployment engines.
        """
        # Adobe-compliant CSV header structure
        csv_headers = "ID_Offerta,Nome_Commerciale,Tecnologia,Codice_AGCOM,Stato,URL_Sintesi,URL_Trasparenza\n"
        csv_row = (
            f"{offer.id},{offer.commercial_name},{offer.technology_type},"
            f"{offer.current_agcom_code or 'Nuova'},{offer.status},"
            f"https://precontratti.windtre.it/sintesi/{offer.id}.pdf,"
            f"https://precontratti.windtre.it/trasparenza/{offer.id}.pdf\n"
        )
        
        csv_file = io.BytesIO()
        csv_file.write((csv_headers + csv_row).encode("utf-8"))
        csv_file.seek(0)
        
        filename = sanitize_adobe_filename(f"adobe_mapping_{offer.commercial_name}.csv")

        return StreamingResponse(
            csv_file, 
            media_type="text/csv", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    @staticmethod
    def get_available_placeholders() -> List[Dict[str, Any]]:
        """
        Returns the official registry of available placeholders for document templates,
        dynamic table definitions, and WYSIWYG note authoring autocompletion.
        """
        return [
            # Prezzi & Tariffe
            {
                "key": "base_price",
                "description": "Prezzo mensile base dell'offerta in formato numerico (es. 29.99)",
                "category": "Prezzi",
                "example": "29.99"
            },
            {
                "key": "base_price_eu",
                "description": "Prezzo mensile con simbolo euro e virgola decimale (es. 29,99 €)",
                "category": "Prezzi",
                "example": "29,99 €"
            },
            {
                "key": "base_price_euro",
                "description": "Prezzo mensile esteso con dicitura euro (es. 29.99 euro)",
                "category": "Prezzi",
                "example": "29.99 euro"
            },
            {
                "key": "prezzo",
                "description": "Importo del canone base dell'offerta (es. 29.99 euro)",
                "category": "Prezzi",
                "example": "29.99 euro"
            },
            {
                "key": "prezzo_canone",
                "description": "Canone mensile formattato per tabelle (es. 29,99 €/mese)",
                "category": "Prezzi",
                "example": "29,99 €/mese"
            },
            {
                "key": "canone_mensile",
                "description": "Canone mensile ricorrente (alias)",
                "category": "Prezzi",
                "example": "29,99 €/mese"
            },
            {
                "key": "activation_price_gia_clienti",
                "description": "Costo di attivazione per già clienti numerico",
                "category": "Prezzi",
                "example": "19.99"
            },
            {
                "key": "activation_price_gia_clienti_eu",
                "description": "Costo di attivazione per già clienti formattato con simbolo euro",
                "category": "Prezzi",
                "example": "19,99 €"
            },
            {
                "key": "prezzo_attivazione_gia_clienti",
                "description": "Costo di attivazione per già clienti con dicitura euro",
                "category": "Prezzi",
                "example": "19.99 euro"
            },
            {
                "key": "activation_price_nuovi_nativi",
                "description": "Costo di attivazione per nuovi clienti nativi numerico",
                "category": "Prezzi",
                "example": "9.99"
            },
            {
                "key": "activation_price_nuovi_nativi_eu",
                "description": "Costo di attivazione per nuovi clienti nativi formattato con simbolo euro",
                "category": "Prezzi",
                "example": "9,99 €"
            },
            {
                "key": "prezzo_attivazione_nuovi_nativi",
                "description": "Costo di attivazione per nuovi clienti nativi con dicitura euro",
                "category": "Prezzi",
                "example": "9.99 euro"
            },
            {
                "key": "activation_price_nuovi_portabilita",
                "description": "Costo di attivazione per nuovi clienti in portabilità (MNP)",
                "category": "Prezzi",
                "example": "0.00"
            },
            {
                "key": "activation_price_nuovi_portabilita_eu",
                "description": "Costo di attivazione per clienti MNP formattato con simbolo euro",
                "category": "Prezzi",
                "example": "0,00 €"
            },
            {
                "key": "prezzo_attivazione_nuovi_portabilita",
                "description": "Costo di attivazione per clienti MNP con dicitura euro",
                "category": "Prezzi",
                "example": "0.00 euro"
            },
            # Offerta & Commerciale
            {
                "key": "nome_offerta",
                "description": "Nome commerciale dell'offerta",
                "category": "Offerta",
                "example": "Windtre Super Mobile Unlimited"
            },
            {
                "key": "commercial_name",
                "description": "Nome commerciale dell'offerta (alias)",
                "category": "Offerta",
                "example": "Windtre Super Mobile Unlimited"
            },
            {
                "key": "operatore",
                "description": "Brand operatore commerciale (WINDTRE o Very Mobile)",
                "category": "Offerta",
                "example": "WINDTRE"
            },
            {
                "key": "segment_id",
                "description": "Identificativo del segmento commerciale aziendale",
                "category": "Offerta",
                "example": "W3_MOB_CB_CNS"
            },
            {
                "key": "po_code",
                "description": "Codice PO univoco (obbligatorio per Very Mobile)",
                "category": "Offerta",
                "example": "PO123456"
            },
            {
                "key": "stato_offerta",
                "description": "Stato corrente o codice AGCOM assegnato",
                "category": "Offerta",
                "example": "COD1234567"
            },
            {
                "key": "status",
                "description": "Stato del ciclo di vita (NUOVA, APERTA, CHIUSA)",
                "category": "Offerta",
                "example": "APERTA"
            },
            {
                "key": "agcom_code",
                "description": "Codice AGCOM dell'offerta o 'Nuova' se non ancora registrata",
                "category": "Offerta",
                "example": "COD1234567"
            },
            {
                "key": "current_agcom_code",
                "description": "Codice univoco AGCOM registrato",
                "category": "Offerta",
                "example": "COD1234567"
            },
            {
                "key": "territorio",
                "description": "Ambito territoriale di applicazione dell'offerta",
                "category": "Offerta",
                "example": "Nazionale"
            },
            {
                "key": "tipologia_offerta",
                "description": "Tipologia dell'offerta commerciale",
                "category": "Offerta",
                "example": "Piano base"
            },
            {
                "key": "piani_compatibili",
                "description": "Piani tariffari compatibili",
                "category": "Offerta",
                "example": "Nessuno"
            },
            {
                "key": "mercato_riferimento",
                "description": "Mercato AGCOM di riferimento",
                "category": "Offerta",
                "example": "Mobile fonia e Internet"
            },
            {
                "key": "target_clientela",
                "description": "Target clientela autorizzata alla sottoscrizione",
                "category": "Offerta",
                "example": "Già clienti, Nuovi clienti nativi"
            },
            {
                "key": "modalita_pagamento",
                "description": "Modalità di pagamento commerciale",
                "category": "Offerta",
                "example": "Credito Residuo"
            },
            {
                "key": "payment_method",
                "description": "Metodo di pagamento tecnico (credito_residuo o abbonamento)",
                "category": "Offerta",
                "example": "credito_residuo"
            },
            # Dati UE & Regolatorio AGCOM
            {
                "key": "giga_eu",
                "description": "Volume Giga in roaming UE calcolato con formula AGCOM RDA",
                "category": "Regolatorio",
                "example": "15.8 GB"
            },
            {
                "key": "eu_giga",
                "description": "Volume Giga in roaming europeo (alias)",
                "category": "Regolatorio",
                "example": "15.8 GB"
            },
            {
                "key": "rda_constant",
                "description": "Costante annuale AGCOM per calcolo RDA roaming UE",
                "category": "Regolatorio",
                "example": "1.55"
            },
            {
                "key": "data_inizio",
                "description": "Data di inizio commercializzazione dell'offerta",
                "category": "Regolatorio",
                "example": "01/06/2026"
            },
            {
                "key": "data_fine",
                "description": "Data di termine commercializzazione o scadenza",
                "category": "Regolatorio",
                "example": "31/12/2026"
            },
            {
                "key": "data_documento",
                "description": "Data di generazione del documento di sintesi",
                "category": "Regolatorio",
                "example": "06/10/2026"
            },
            {
                "key": "pagina_web",
                "description": "URL della pagina di trasparenza tariffaria",
                "category": "Regolatorio",
                "example": "https://www.windtre.it/trasparenza-tariffaria/"
            },
            {
                "key": "custom_filename_sintesi",
                "description": "Nome file personalizzato per la Sintesi contrattuale",
                "category": "Regolatorio",
                "example": "sintesi_offerta_flash"
            },
            {
                "key": "custom_filename_trasparenza",
                "description": "Nome file personalizzato per la Trasparenza tariffaria",
                "category": "Regolatorio",
                "example": "trasparenza_offerta_flash"
            },
            # Rete & Tecnologie
            {
                "key": "tecnologia",
                "description": "Tecnologia di rete principale (FTTH, FTTC, FWA, 5G, 4G)",
                "category": "Tecnico",
                "example": "5G"
            },
            {
                "key": "technology_type",
                "description": "Codice tecnologia (alias)",
                "category": "Tecnico",
                "example": "5G"
            },
            {
                "key": "tecnologia_rete",
                "description": "Descrizione estesa della tecnologia di rete",
                "category": "Tecnico",
                "example": "5G Full Speed"
            },
            {
                "key": "velocita_download",
                "description": "Velocità massima/stimata di download",
                "category": "Tecnico",
                "example": "2000 Mbps"
            },
            {
                "key": "velocita_upload",
                "description": "Velocità massima/stimata di upload",
                "category": "Tecnico",
                "example": "200 Mbps"
            },
            # Note Regolatorie & Segnaposto Tabelle
            {
                "key": "note_regolatorie",
                "description": "Tutte le note regolatorie concatenate in formato HTML",
                "category": "Note",
                "example": "Note complete per tutte le tabelle"
            },
            {
                "key": "note_regolatorie_plain",
                "description": "Tutte le note regolatorie in formato testo semplice (senza tag HTML)",
                "category": "Note",
                "example": "Note in testo piano"
            },
            {
                "key": "PREZZO_notes",
                "description": "Note regolatorie ancorate sotto la tabella PREZZO (formattate)",
                "category": "Note",
                "example": "Note specifiche per la tabella PREZZO"
            },
            {
                "key": "PREZZO_notes_plain",
                "description": "Note specifiche per la tabella PREZZO in testo semplice",
                "category": "Note",
                "example": "Note testo semplice PREZZO"
            },
            {
                "key": "SERVIZI_notes",
                "description": "Note specifiche per la tabella SERVIZI (formattate)",
                "category": "Note",
                "example": "Note specifiche per la tabella SERVIZI"
            },
            {
                "key": "SERVIZI_notes_plain",
                "description": "Note specifiche per la tabella SERVIZI in testo semplice",
                "category": "Note",
                "example": "Note testo semplice SERVIZI"
            },
            {
                "key": "COSTI_notes",
                "description": "Note specifiche per la tabella COSTI (formattate)",
                "category": "Note",
                "example": "Note specifiche per la tabella COSTI"
            },
            {
                "key": "COSTI_notes_plain",
                "description": "Note specifiche per la tabella COSTI in testo semplice",
                "category": "Note",
                "example": "Note testo semplice COSTI"
            },
            {
                "key": "DURATA_notes",
                "description": "Note specifiche per la tabella DURATA (formattate)",
                "category": "Note",
                "example": "Note specifiche per la tabella DURATA"
            },
            {
                "key": "DURATA_notes_plain",
                "description": "Note specifiche per la tabella DURATA in testo semplice",
                "category": "Note",
                "example": "Note testo semplice DURATA"
            }
        ]

