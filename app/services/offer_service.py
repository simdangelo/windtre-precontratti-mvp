import copy
import random
from uuid import UUID
from datetime import date
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status, BackgroundTasks

# Import models & schemas
from app.database_models import (
    Offer, Segment, DynamicTable, OfferCreate, OfferUpdate, DynamicTableContentSchema, OfferBulkUpdate, OfferDuplicateRequest
)
from app.services.document_service import DocumentService


class OfferService:
    """
    Handles all business logic regarding offers management:
    - Creating and bootstrapping baseline dynamic tables.
    - Validating segment limits during dynamic table layout updates.
    - Implementing the state machine and enqueuing document synthesis tasks.
    """

    # Enforce row boundary limits based on AGCOM segment specifications
    LIMIT_MAPPING: Dict[str, int] = {
        "W3_MOB_GA_CNS": 12,
        "W3_MOB_CB_CNS": 15,
        "W3_MOB_GA_MB": 11,
        "W3_FIX_GA_CNS": 14,
        "W3_FIX_CB_CNS": 14,
        "VERY_MOBILE": 15,
    }

    @classmethod
    def create_offer(cls, payload: OfferCreate, db: Session) -> Offer:
        """
        Creates a new offer, boots up the default layout structures, and saves to Spanner.
        """
        # 1. Verify target segment exists
        segment = db.scalar(select(Segment).where(Segment.id == payload.segment_id))
        if not segment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Selected market segment does not exist."
            )

        db_offer = Offer(
            segment_id=payload.segment_id,
            commercial_name=payload.commercial_name,
            technology_type=payload.technology_type,
            base_price=payload.base_price,
            po_code=payload.po_code,
            current_agcom_code=payload.current_agcom_code,
            status="NUOVA",
            date_start=payload.date_start,
            date_end=payload.date_end,
            custom_filename_sintesi=payload.custom_filename_sintesi,
            custom_filename_trasparenza=payload.custom_filename_trasparenza,
            payment_method=payload.payment_method,
            activation_price_gia_clienti=payload.activation_price_gia_clienti,
            activation_price_nuovi_nativi=payload.activation_price_nuovi_nativi,
            activation_price_nuovi_portabilita=payload.activation_price_nuovi_portabilita
        )
        db.add(db_offer)
        db.flush() # Secure the generated Offer UUID

        # 3. Bootstrap baseline dynamic tables (e.g. PREZZO, COSTI, SERVIZI, DURATA) for editing
        default_identifiers = ["PREZZO", "COSTI", "SERVIZI", "DURATA"]
        for idx, identifier in enumerate(default_identifiers):
            db_table = DynamicTable(
                offer_id=db_offer.id,
                table_identifier=identifier,
                sequence_order=idx,
                title=f"Tabella {identifier.title()}",
                structural_content={"max_rows_limit": 15, "rows": []}, # Initial empty Padre-Figlio tree
                note_links={"links": []}
            )
            db.add(db_table)

        db.commit()
        db.refresh(db_offer)
        return db_offer

    @classmethod
    def update_offer_metadata(
        cls, id: UUID, payload: OfferUpdate, db: Session
    ) -> Offer:
        """
        Updates the baseline metadata attributes of an offer in the database.
        """
        offer = db.scalar(select(Offer).where(Offer.id == id))
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Offer record not found."
            )

        if payload.commercial_name is not None:
            offer.commercial_name = payload.commercial_name
        if payload.technology_type is not None:
            offer.technology_type = payload.technology_type
        if payload.base_price is not None:
            offer.base_price = payload.base_price
        if payload.po_code is not None:
            offer.po_code = payload.po_code if payload.po_code != "N/A" else None
        if "current_agcom_code" in payload.model_fields_set:
            offer.current_agcom_code = payload.current_agcom_code
        if payload.status is not None:
            offer.status = payload.status
        if payload.date_start is not None:
            offer.date_start = payload.date_start
        if payload.date_end is not None:
            offer.date_end = payload.date_end
        if payload.custom_filename_sintesi is not None:
            offer.custom_filename_sintesi = payload.custom_filename_sintesi
        if payload.custom_filename_trasparenza is not None:
            offer.custom_filename_trasparenza = payload.custom_filename_trasparenza
        if payload.payment_method is not None:
            offer.payment_method = payload.payment_method
        if payload.activation_price_gia_clienti is not None:
            offer.activation_price_gia_clienti = payload.activation_price_gia_clienti
        if payload.activation_price_nuovi_nativi is not None:
            offer.activation_price_nuovi_nativi = payload.activation_price_nuovi_nativi
        if payload.activation_price_nuovi_portabilita is not None:
            offer.activation_price_nuovi_portabilita = payload.activation_price_nuovi_portabilita

        db.commit()
        db.refresh(offer)
        return offer

    @classmethod
    def update_dynamic_table(
        cls, id: UUID, table_identifier: str, payload: DynamicTableContentSchema, db: Session
    ) -> Dict[str, str]:
        """
        Loads the offer, retrieves segment row limits, re-validates the payload context,
        and commits the validated Padre-Figlio content to Spanner.
        """
        # 1. Load the offer and dynamic table records
        offer = db.scalar(select(Offer).where(Offer.id == id))
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Offer record not found."
            )

        table = db.scalar(
            select(DynamicTable)
            .where(DynamicTable.offer_id == id, DynamicTable.table_identifier == table_identifier)
        )
        if not table:
            # Dynamically bootstrap the new table structure if it is not found in the database
            next_seq = len(offer.dynamic_tables)
            table = DynamicTable(
                offer_id=id,
                table_identifier=table_identifier,
                sequence_order=next_seq,
                title=f"Tabella {table_identifier.title()}",
                structural_content={"max_rows_limit": 15, "rows": []},
                note_links={"links": []}
            )
            db.add(table)

        # 2. Enforce limits based on requirements document
        allowed_limit = cls.LIMIT_MAPPING.get(offer.segment_id, 15) # Default limit fallback

        # Re-validate with context parameters injected
        try:
            validated_content = DynamicTableContentSchema.model_validate(
                payload.model_dump(), 
                context={"max_rows_limit": allowed_limit}
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                detail=f"Validation failed: {str(e)}"
            )

        # 3. Commit JSON to Cloud Spanner JSON column
        # Exclude note_links from table layout content to keep them structurally decoupled
        table.structural_content = validated_content.model_dump(exclude={"note_links"})
        if validated_content.note_links is not None:
            table.note_links = validated_content.note_links
        db.commit()
        
        return {"status": "success", "message": f"Table '{table_identifier}' layout saved."}

    @classmethod
    def transition_offer(
        cls, id: UUID, target_status: str, agcom_code: Optional[str], date_end: Optional[date], background_tasks: BackgroundTasks, db: Session
    ) -> Dict[str, str]:
        """
        Executes transition validations, updates Spanner metadata, and enqueues async rendering.
        """
        offer = db.scalar(select(Offer).where(Offer.id == id))
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Offer record not found."
            )

        if target_status == "APERTA":
            if not agcom_code or len(agcom_code) not in (10, 36):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Transition to APERTA requires a valid 10-char or 36-char UUID AGCOM code."
                )
            offer.current_agcom_code = agcom_code
            offer.status = "APERTA"
        elif target_status == "CHIUSA":
            offer.status = "CHIUSA"
            offer.date_end = date_end or date.today()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid target transition status."
            )

        db.commit()

        # Enqueue compilation task onto GCP Cloud Tasks / Background execution
        if background_tasks:
            background_tasks.add_task(
                DocumentService.execute_asynchronous_document_compilation, offer.id, db
            )

        return {
            "status": "success", 
            "message": f"Offer transitioned to {target_status}. Document generation enqueued."
        }

    @classmethod
    def bulk_update_offers(
        cls, payload: OfferBulkUpdate, db: Session
    ) -> list[Offer]:
        """
        Performs bulk metadata updates on a targeted list of offers.
        """
        if not payload.offer_ids:
            return []

        # 1. Fetch targeted offers
        stmt = select(Offer).where(Offer.id.in_(payload.offer_ids))
        offers = list(db.scalars(stmt).all())

        # 2. Check if any requested offer ID was not found
        found_ids = {o.id for o in offers}
        missing_ids = [str(oid) for oid in payload.offer_ids if oid not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offers not found: {', '.join(missing_ids)}"
            )

        # 3. Check for fields to update
        fields_to_update = payload.fields.model_dump(exclude_unset=True)
        if not fields_to_update:
            return offers

        # 4. Perform updates
        for offer in offers:
            for field, val in fields_to_update.items():
                if field == "po_code":
                    setattr(offer, field, val if val != "N/A" else None)
                else:
                    setattr(offer, field, val)

        db.commit()

        # 5. Refresh updated offers
        for offer in offers:
            db.refresh(offer)

        return offers

    @classmethod
    def duplicate_offer(
        cls, id: UUID, payload: Optional[OfferDuplicateRequest] = None, db: Session = None
    ) -> Offer:
        """
        Duplicates an existing offer record along with:
        - All edited metadata and parameters (commercial name defaulted to '{nome} Copia' or custom draft name).
        - Initial status set to 'NUOVA' (draft) with AGCOM code cleared.
        - Deep copy of all associated DynamicTable records (Padre-Figlio structural content and note_links).
        """
        original = db.scalar(select(Offer).where(Offer.id == id))
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source offer record not found."
            )

        # 1. Determine new commercial name
        if payload and payload.commercial_name and payload.commercial_name.strip():
            new_name = payload.commercial_name.strip()
        else:
            new_name = f"{original.commercial_name} Copia"

        target_status = payload.target_status if payload and payload.target_status else "NUOVA"

        # 2. Very Mobile unique PO Code generation
        if original.segment_id == "VERY_MOBILE":
            new_po = f"PO{random.randint(100000, 999999)}"
        else:
            new_po = original.po_code

        # 3. Filenames handling
        new_sintesi_filename = None
        if original.custom_filename_sintesi:
            new_sintesi_filename = f"{original.custom_filename_sintesi}_copia"

        new_trasparenza_filename = None
        if original.custom_filename_trasparenza:
            new_trasparenza_filename = f"{original.custom_filename_trasparenza}_copia"

        # 4. Instantiate new Offer record
        new_offer = Offer(
            segment_id=original.segment_id,
            commercial_name=new_name,
            technology_type=original.technology_type,
            base_price=original.base_price,
            po_code=new_po,
            current_agcom_code=None,
            status=target_status,
            date_start=original.date_start,
            date_end=original.date_end,
            custom_filename_sintesi=new_sintesi_filename,
            custom_filename_trasparenza=new_trasparenza_filename,
            payment_method=original.payment_method,
            activation_price_gia_clienti=original.activation_price_gia_clienti,
            activation_price_nuovi_nativi=original.activation_price_nuovi_nativi,
            activation_price_nuovi_portabilita=original.activation_price_nuovi_portabilita,
        )
        db.add(new_offer)
        db.flush() # Allocates UUID for new_offer.id

        # 5. Deep-copy all dynamic tables belonging to source offer
        source_tables = list(db.scalars(
            select(DynamicTable)
            .where(DynamicTable.offer_id == original.id)
            .order_by(DynamicTable.sequence_order)
        ).all())

        if source_tables:
            for t in source_tables:
                cloned_table = DynamicTable(
                    offer_id=new_offer.id,
                    table_identifier=t.table_identifier,
                    sequence_order=t.sequence_order,
                    title=t.title,
                    structural_content=copy.deepcopy(t.structural_content),
                    note_links=copy.deepcopy(t.note_links) if t.note_links else {"links": []}
                )
                db.add(cloned_table)
        else:
            # Fallback bootstrap baseline tables
            default_identifiers = ["PREZZO", "COSTI", "SERVIZI", "DURATA"]
            for idx, identifier in enumerate(default_identifiers):
                db_table = DynamicTable(
                    offer_id=new_offer.id,
                    table_identifier=identifier,
                    sequence_order=idx,
                    title=f"Tabella {identifier.title()}",
                    structural_content={"max_rows_limit": 15, "rows": []},
                    note_links={"links": []}
                )
                db.add(db_table)

        db.commit()
        db.refresh(new_offer)
        return new_offer

