"""
Ingestion script for WINDTRE Mobile Trasparenze Tariffarie samples.
Parses the 10 Excel files in 'esempi_trasparenze_mobile/' and populates the database
(Offer records and DynamicTable Padre-Figlio structures) under the segment 'W3_MOB_CB_CNS'.
"""

import os
import sys
import io
import glob
import uuid
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import openpyxl
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database_models import Offer, DynamicTable, Segment


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pre_contratti.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def parse_sample_file(file_path: str) -> Dict[str, Any]:
    """
    Parses a single .XLS (OpenXML/Zip) tariff transparency file and extracts
    structured offer metadata, service values, and regulatory note text.
    """
    fname = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        wb = openpyxl.load_workbook(io.BytesIO(f.read()), data_only=True)
    ws = wb.active

    # Extract commercial name and status
    commercial_name = str(ws.cell(7, 3).value or "").strip()
    status_raw = str(ws.cell(3, 3).value or "").strip()

    # Determine status & AGCOM code
    if status_raw.lower() == "nuova" or not status_raw:
        offer_status = "NUOVA"
        agcom_code = None
    else:
        offer_status = "APERTA"
        agcom_code = status_raw

    # Date start
    d_start_raw = ws.cell(4, 3).value
    if isinstance(d_start_raw, (datetime, date)):
        date_start = d_start_raw.date() if isinstance(d_start_raw, datetime) else d_start_raw
    elif isinstance(d_start_raw, str):
        d_clean = d_start_raw.strip()
        if "/" in d_clean:
            date_start = datetime.strptime(d_clean, "%d/%m/%Y").date()
        else:
            date_start = datetime.fromisoformat(d_clean).date()
    else:
        date_start = date(2024, 6, 19)

    # Date end
    d_end_raw = ws.cell(5, 3).value
    date_end = None
    if d_end_raw and str(d_end_raw).strip() not in ("-", "", "None"):
        try:
            d_clean = str(d_end_raw).strip()
            if "/" in d_clean:
                date_end = datetime.strptime(d_clean, "%d/%m/%Y").date()
            else:
                date_end = datetime.fromisoformat(d_clean).date()
        except Exception:
            date_end = None

    # Base price (Row 28, Column 7)
    base_price_raw = ws.cell(28, 7).value
    if base_price_raw is not None:
        bp_clean = str(base_price_raw).strip().replace(",", ".")
        try:
            base_price = Decimal(bp_clean)
        except Exception:
            base_price = Decimal("0.00")
    else:
        base_price = Decimal("0.00")

    # Activation price for existing customers (Row 19, Column 5)
    att_raw = ws.cell(19, 5).value
    if att_raw is not None and str(att_raw).strip() != "-":
        att_clean = str(att_raw).strip().replace(",", ".")
        try:
            activation_price = Decimal(att_clean)
        except Exception:
            activation_price = None
    else:
        activation_price = None

    # Speeds
    vel_dl = ws.cell(15, 4).value
    vel_ul = ws.cell(16, 4).value

    # Contract terms
    durata_minima = ws.cell(25, 4).value
    costo_recesso = ws.cell(26, 4).value

    # Services
    fonia_mobile_onnet = str(ws.cell(40, 7).value or "").strip()
    sms_onnet = ws.cell(42, 7).value
    internet_volume = ws.cell(44, 7).value

    # Regulatory Notes in Cell A47
    notes_raw = str(ws.cell(47, 1).value or "").strip()

    # Determine technology type
    tech_type = "5G" if (str(vel_dl) == "1600" or "5g" in notes_raw.lower()) else "4G"

    # Identify if Call Your Country (CYC)
    is_cyc = "cyc" in commercial_name.lower() or "call your country" in commercial_name.lower() or "53 paesi" in notes_raw.lower()

    # Extract down-payment / installments from notes if available
    # E.g.: "quota massima di 4,99€ all'attivazione e 24 rate mensili di 1,25€"
    down_payment = None
    m_dp = re.search(r"quota\s+(?:massima\s+di\s+)?(\d+(?:[.,]\d+)?)\s*€\s*all['’]attivazione", notes_raw, re.IGNORECASE)
    if m_dp:
        down_payment = m_dp.group(1).replace(",", ".")

    # Extract foreign minutes if CYC
    foreign_minutes = None
    if is_cyc:
        m_fm = re.search(r"(\d+)\s+minuti\s+dall['’]Italia\s+verso\s+53\s+Paesi", notes_raw, re.IGNORECASE)
        if m_fm:
            foreign_minutes = m_fm.group(1)
        else:
            foreign_minutes = "300"

    return {
        "filename": fname,
        "commercial_name": commercial_name,
        "segment_id": "W3_MOB_CB_CNS",
        "technology_type": tech_type,
        "base_price": base_price,
        "activation_price_gia_clienti": activation_price,
        "activation_price_nuovi_nativi": None,
        "activation_price_nuovi_portabilita": None,
        "status": offer_status,
        "current_agcom_code": agcom_code,
        "date_start": date_start,
        "date_end": date_end,
        "payment_method": "credito_residuo",
        "custom_filename_trasparenza": fname,
        "vel_dl": vel_dl,
        "vel_ul": vel_ul,
        "durata_minima": durata_minima,
        "costo_recesso": costo_recesso,
        "fonia_mobile_onnet": fonia_mobile_onnet,
        "sms_onnet": sms_onnet,
        "internet_volume": internet_volume,
        "notes_raw": notes_raw,
        "is_cyc": is_cyc,
        "down_payment": down_payment,
        "foreign_minutes": foreign_minutes,
    }


def build_dynamic_tables_content(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Constructs the 4 standard AGCOM Padre-Figlio Dynamic Table structures:
    - PREZZO: Base monthly recurring charge + activation breakdown + full regulatory note link
    - COSTI: Early exit fees, SMS extra-allowance, international extra-charge
    - SERVIZI: Voice minutes, SMS quota, Internet GIGA (with $Bollino$ marker), VAS/5G Priority Pass
    - DURATA: Contract permanence minimum, promo duration
    """
    base_price = data["base_price"]
    act_price = data["activation_price_gia_clienti"]
    down_payment = data.get("down_payment")
    is_cyc = data.get("is_cyc", False)
    foreign_minutes = data.get("foreign_minutes")
    sms_val = data.get("sms_onnet")
    net_val = data.get("internet_volume")
    notes_raw = data.get("notes_raw", "")

    # Format HTML note content preserving paragraphs and linebreaks
    # Convert double newlines into paragraph tags, single newlines into <br/>
    note_paragraphs = [p.strip() for p in notes_raw.split("\n\n") if p.strip()]
    note_html = "".join(f"<p>{p.replace('\n', '<br/>')}</p>" for p in note_paragraphs)

    # 1. TABELLA PREZZO
    prezzo_rows = [
        {
            "id": "p_canone_mensile",
            "type": "padre",
            "label": "Canone mensile offerta (Addebito flat)",
            "value": f"{base_price:.2f} euro/mese".replace(".", ","),
            "children": []
        }
    ]
    if act_price:
        act_children = []
        if down_payment:
            act_children.append({
                "id": "c_anticipo_attivazione",
                "type": "figlio",
                "label": "Quota iniziale versata all'attivazione",
                "value": f"{Decimal(down_payment):.2f} euro".replace(".", ",")
            })
            act_children.append({
                "id": "c_rate_attivazione",
                "type": "figlio",
                "label": "24 rate mensili residue",
                "value": "1,25 euro/mese"
            })
        prezzo_rows.append({
            "id": "p_costo_attivazione_gia_clienti",
            "type": "padre",
            "label": "Costo attivazione (Già clienti)",
            "value": f"{act_price:.2f} euro".replace(".", ","),
            "children": act_children
        })

    # 2. TABELLA COSTI
    costi_rows = [
        {
            "id": "p_costo_recesso",
            "type": "padre",
            "label": "Costo recesso",
            "value": "0,0 / 30,00 euro",
            "children": []
        },
        {
            "id": "p_disattivazione_anticipata",
            "type": "padre",
            "label": "Costo disattivazione anticipata linea",
            "value": "10,00 euro",
            "children": []
        },
        {
            "id": "p_extra_sms",
            "type": "padre",
            "label": "Costo singolo SMS extra soglia",
            "value": "0,29 euro/SMS",
            "children": []
        }
    ]
    if is_cyc:
        costi_rows.append({
            "id": "p_extra_estero",
            "type": "padre",
            "label": "Chiamate extra soglia verso Estero (Call Your Country Super)",
            "value": "0,19 euro scatto + tariffe a consumo (max 0,23 euro 1° min UE)",
            "children": []
        })

    # 3. TABELLA SERVIZI
    servizi_rows = [
        {
            "id": "p_minuti_nazionali",
            "type": "padre",
            "label": "Minuti di conversazione nazionali da mobile",
            "value": "Illimitato",
            "children": []
        }
    ]
    if is_cyc and foreign_minutes:
        servizi_rows.append({
            "id": "p_minuti_estero",
            "type": "padre",
            "label": "Minuti dall'Italia verso l'Estero",
            "value": f"{foreign_minutes} minuti verso 53 Paesi",
            "children": []
        })

    # SMS formatting
    if str(sms_val).strip().lower() == "illimitato":
        sms_label_val = "Illimitato"
    elif sms_val and str(sms_val).strip() != "-":
        sms_label_val = f"{sms_val} SMS/mese"
    else:
        sms_label_val = "A consumo (0,29 euro/SMS)"
    servizi_rows.append({
        "id": "p_sms_inclusi",
        "type": "padre",
        "label": "SMS nazionali inclusi",
        "value": sms_label_val,
        "children": []
    })

    # Internet formatting
    if str(net_val).strip().lower() == "illimitato":
        net_label_val = "Giga Illimitati $Bollino$"
    elif net_val and str(net_val).strip() != "-":
        net_label_val = f"{net_val} GB/mese $Bollino$"
    else:
        net_label_val = "Non specificato"
    servizi_rows.append({
        "id": "p_internet_incluso",
        "type": "padre",
        "label": "Traffico Internet nazionale",
        "value": net_label_val,
        "children": []
    })

    # VAS services
    servizi_rows.append({
        "id": "p_servizi_accessori",
        "type": "padre",
        "label": "Servizi accessori inclusi gratuitamente",
        "value": "5G Priority Pass, Ti Ho Cercato, Segreteria Telefonica",
        "children": []
    })

    # 4. TABELLA DURATA
    durata_rows = [
        {
            "id": "p_durata_contratto",
            "type": "padre",
            "label": "Durata minima del contratto",
            "value": "24 mesi",
            "children": []
        },
        {
            "id": "p_durata_promo",
            "type": "padre",
            "label": "Durata promozione",
            "value": "A tempo indeterminato",
            "children": []
        }
    ]

    return {
        "PREZZO": {
            "title": "Tabella Prezzo",
            "sequence_order": 0,
            "structural_content": {
                "max_rows_limit": 15,
                "rows": prezzo_rows
            },
            "note_links": {
                "html_content": note_html
            }
        },
        "COSTI": {
            "title": "Tabella Costi",
            "sequence_order": 1,
            "structural_content": {
                "max_rows_limit": 15,
                "rows": costi_rows
            },
            "note_links": {"links": []}
        },
        "SERVIZI": {
            "title": "Tabella Servizi",
            "sequence_order": 2,
            "structural_content": {
                "max_rows_limit": 15,
                "rows": servizi_rows
            },
            "note_links": {"links": []}
        },
        "DURATA": {
            "title": "Tabella Durata",
            "sequence_order": 3,
            "structural_content": {
                "max_rows_limit": 15,
                "rows": durata_rows
            },
            "note_links": {"links": []}
        }
    }


def ingest_samples(directory: str = "esempi_trasparenze_mobile") -> List[str]:
    """
    Main function to read all samples and populate/update the database.
    """
    files = sorted(glob.glob(os.path.join(directory, "*.XLS")))
    if not files:
        print(f"No .XLS files found in {directory}!")
        return []

    db = SessionLocal()
    ingested_offer_ids = []

    try:
        # Ensure target segment exists
        segment = db.scalar(select(Segment).where(Segment.id == "W3_MOB_CB_CNS"))
        if not segment:
            print("Segment W3_MOB_CB_CNS not found, creating segment...")
            segment = Segment(
                id="W3_MOB_CB_CNS",
                name="WINDTRE Mobile Customer Base Consumer",
                description="WINDTRE Mobile CB Consumer"
            )
            db.add(segment)
            db.commit()

        for fpath in files:
            data = parse_sample_file(fpath)
            comm_name = data["commercial_name"]
            fname = data["filename"]

            print(f"Processing: {fname} -> '{comm_name}' (Status: {data['status']}, Price: {data['base_price']}€)")

            # Check if offer already exists by commercial_name or custom_filename_trasparenza
            existing_offer = db.scalar(
                select(Offer).where(
                    (Offer.commercial_name == comm_name) |
                    (Offer.custom_filename_trasparenza == fname)
                )
            )

            if existing_offer:
                offer_id = existing_offer.id
                print(f"  -> Updating existing offer ID: {offer_id}")
                existing_offer.commercial_name = data["commercial_name"]
                existing_offer.segment_id = data["segment_id"]
                existing_offer.technology_type = data["technology_type"]
                existing_offer.base_price = data["base_price"]
                existing_offer.activation_price_gia_clienti = data["activation_price_gia_clienti"]
                existing_offer.status = data["status"]
                existing_offer.current_agcom_code = data["current_agcom_code"]
                existing_offer.date_start = data["date_start"]
                existing_offer.date_end = data["date_end"]
                existing_offer.payment_method = data["payment_method"]
                existing_offer.custom_filename_trasparenza = data["custom_filename_trasparenza"]
            else:
                offer_id = uuid.uuid4()
                print(f"  -> Creating new offer ID: {offer_id}")
                new_offer = Offer(
                    id=offer_id,
                    segment_id=data["segment_id"],
                    commercial_name=data["commercial_name"],
                    technology_type=data["technology_type"],
                    base_price=data["base_price"],
                    activation_price_gia_clienti=data["activation_price_gia_clienti"],
                    activation_price_nuovi_nativi=None,
                    activation_price_nuovi_portabilita=None,
                    status=data["status"],
                    current_agcom_code=data["current_agcom_code"],
                    date_start=data["date_start"],
                    date_end=data["date_end"],
                    payment_method=data["payment_method"],
                    custom_filename_trasparenza=data["custom_filename_trasparenza"]
                )
                db.add(new_offer)

            db.commit()

            # Build and update the dynamic tables
            tables_data = build_dynamic_tables_content(data)
            for tid, tinfo in tables_data.items():
                existing_table = db.scalar(
                    select(DynamicTable).where(
                        DynamicTable.offer_id == offer_id,
                        DynamicTable.table_identifier == tid
                    )
                )
                if existing_table:
                    existing_table.title = tinfo["title"]
                    existing_table.sequence_order = tinfo["sequence_order"]
                    existing_table.structural_content = tinfo["structural_content"]
                    existing_table.note_links = tinfo["note_links"]
                else:
                    new_table = DynamicTable(
                        id=uuid.uuid4(),
                        offer_id=offer_id,
                        table_identifier=tid,
                        title=tinfo["title"],
                        sequence_order=tinfo["sequence_order"],
                        structural_content=tinfo["structural_content"],
                        note_links=tinfo["note_links"]
                    )
                    db.add(new_table)

            db.commit()
            ingested_offer_ids.append(offer_id)

        print(f"\nSuccessfully ingested/updated {len(ingested_offer_ids)} offers and their dynamic tables!")
        return ingested_offer_ids

    except Exception as e:
        db.rollback()
        print(f"Error during ingestion: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ingest_samples()
