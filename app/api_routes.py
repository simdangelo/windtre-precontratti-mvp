from uuid import UUID
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker

# Local database and schema definitions
from .database_models import (
    Offer, OfferCreate, OfferUpdate, OfferResponse, DynamicTableContentSchema, DynamicTable, OfferBulkUpdate, PlaceholderItem, OfferDuplicateRequest
)
from app.services import OfferService, DocumentService

router = APIRouter(prefix="/offers", tags=["Offers"])


# ============================================================================
# Local persistent SQLite Database Configuration (Zero-setup for local Demo)
# ============================================================================
DATABASE_URL = "sqlite:///./pre_contratti.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """Yields a local thread-safe session connection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# 1. Endpoint: List & Detail Offers
# ============================================================================

@router.get("/", response_model=List[OfferResponse])
def get_all_offers(db: Session = Depends(get_db_session)):
    """
    Returns a list of all offers recorded in the database, ordered by creation date.
    """
    return list(db.scalars(select(Offer).order_by(Offer.created_at.desc())).all())


@router.get("/placeholders", response_model=List[PlaceholderItem], tags=["Placeholders"])
def get_available_placeholders():
    """
    Returns the registry of available placeholders for template injection and authoring autocomplete.
    """
    return DocumentService.get_available_placeholders()


@router.get("/{id}", response_model=OfferResponse)
def get_offer_by_id(id: UUID, db: Session = Depends(get_db_session)):
    """
    Returns single offer metadata by UUID.
    """
    offer = db.scalar(select(Offer).where(Offer.id == id))
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer record not found.")
    return offer


@router.get("/{id}/tables")
def get_offer_tables_by_id(id: UUID, db: Session = Depends(get_db_session)):
    """
    Returns the compiled structural content JSON layouts of all dynamic tables for this offer.
    """
    tables = db.scalars(
        select(DynamicTable)
        .where(DynamicTable.offer_id == id)
        .order_by(DynamicTable.sequence_order)
    ).all()
    # Return mapping table_identifier -> structural_content JSON + note_links
    return {
        t.table_identifier: {
            "max_rows_limit": t.structural_content.get("max_rows_limit", 15),
            "rows": t.structural_content.get("rows", []),
            "note_links": t.note_links
        }
        for t in tables
    }


# ============================================================================
# 2. Endpoint: Create Offer (Initial status: 'NUOVA')
# ============================================================================

@router.post("/", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_new_offer(payload: OfferCreate, db: Session = Depends(get_db_session)):
    """
    Creates a new offer record in Google Cloud Spanner (PostgreSQL dialect).
    Delegates to OfferService to bootstrap layout tables and save data.
    """
    return OfferService.create_offer(payload, db)


# ============================================================================
# 2b. Endpoint: Update Offer Metadata
# ============================================================================

@router.put("/{id}", response_model=OfferResponse, status_code=status.HTTP_200_OK)
def update_offer_metadata(id: UUID, payload: OfferUpdate, db: Session = Depends(get_db_session)):
    """
    Updates the base metadata fields of an offer (such as commercial name, technology type, price, and PO code).
    Delegates database updates to OfferService.
    """
    return OfferService.update_offer_metadata(id, payload, db)


# ============================================================================
# 3. Endpoint: Update Dynamic Table Fields (Padre-Figlio validation)
# ============================================================================

@router.put("/{id}/tables/{table_identifier}", status_code=status.HTTP_200_OK)
def update_dynamic_table_layout(
    id: UUID, 
    table_identifier: str, 
    payload: DynamicTableContentSchema, 
    db: Session = Depends(get_db_session)
):
    """
    Updates the structural Padre-Figlio JSON layout inside Google Cloud Spanner.
    Delegates to OfferService to execute boundary validation by segment limit.
    """
    return OfferService.update_dynamic_table(id, table_identifier, payload, db)


# ============================================================================
# 4. Endpoint: Transition Offer Lifecycle (NUOVA -> APERTA -> CHIUSA)
# ============================================================================

@router.post("/{id}/transition", status_code=status.HTTP_200_OK)
def transition_offer_state(
    id: UUID, 
    target_status: str, 
    agcom_code: Optional[str] = None, 
    date_end: Optional[date] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db_session)
):
    """
    Transitions the offer state. Generates a new pair of compiled documents (PDF + Word/Excel)
    using DocumentService without overwriting historical records.
    """
    return OfferService.transition_offer(id, target_status, agcom_code, date_end, background_tasks, db)


# ============================================================================
# 4b. Endpoint: Duplicate Offer
# ============================================================================

@router.post("/{id}/duplicate", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def duplicate_offer(
    id: UUID,
    payload: Optional[OfferDuplicateRequest] = None,
    db: Session = Depends(get_db_session)
):
    """
    Duplicates an existing offer along with all its edited fields, metadata,
    and dynamic tables (structural Padre-Figlio content and footnote links).
    Initializes the duplicated offer in 'NUOVA' (draft) status with name suffix 'Copia'.
    """
    return OfferService.duplicate_offer(id, payload, db)


# ============================================================================
# 5. Endpoint: Manual Document Compilation (Trigger Generation Task)
# ============================================================================

@router.post("/{id}/compile", status_code=status.HTTP_200_OK)
def compile_offer_documents(
    id: UUID, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
):
    """
    Manually triggers direct asynchronous document compilation for the offer in its current state.
    """
    offer = db.scalar(select(Offer).where(Offer.id == id))
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer record not found.")

    background_tasks.add_task(
        DocumentService.execute_asynchronous_document_compilation, offer.id, db
    )
    return {
        "status": "success", 
        "message": "Direct document compilation enqueued."
    }


# ============================================================================
# 5b. Endpoint: Bulk Update Offers
# ============================================================================

@router.post("/bulk-update", response_model=List[OfferResponse], status_code=status.HTTP_200_OK)
def bulk_update_offers(payload: OfferBulkUpdate, db: Session = Depends(get_db_session)):
    """
    Performs bulk metadata updates on a specified list of offers.
    """
    return OfferService.bulk_update_offers(payload, db)


# ============================================================================
# 6. Endpoint: Export Adobe Mapping (Required CSV Sheet)
# ============================================================================

@router.get(path="/{id}/mapping", response_class=StreamingResponse)
def export_adobe_mapping_sheet(id: UUID, db: Session = Depends(get_db_session)):
    """
    Generates and downloads the mapping sheet CSV file matching Adobe's internal formatting.
    Delegates CSV generation and streaming to DocumentService.
    """
    offer = db.scalar(select(Offer).where(Offer.id == id))
    if not offer:
        raise HTTPException(status_code=404, detail="Offer record not found.")

    return DocumentService.generate_adobe_mapping_sheet(offer)

